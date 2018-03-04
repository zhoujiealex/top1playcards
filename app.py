# coding:utf-8
"""
Flask应用

Author: karl(i@karlzhou.com)
"""

import platform
import sys
from urllib import quote

from flask import Flask, render_template, request, jsonify, send_from_directory, abort, Response, redirect, flash, \
    url_for
from flask_apscheduler import APScheduler
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from werkzeug import exceptions

from server.batch_order import refresh_merchant_config, get_merchant, download_order_by_logon_id, download_all_orders
from server.browser import *
import server.browser as browser
from server.excel import save_order_data_to_excel, merge_excel_helper, get_excel_path
from server.order import *
from server.utils import get_merchant_login_cfg

reload(sys)
sys.setdefaultencoding('utf-8')

RUN_TIME = int(get_merchant_login_cfg('refresh_time'))


class Config(object):
    JOBS = [
        {
            'id': 'checkSessionValidation',
            'func': 'server.batch_order:refresh_merchant_config',
            'args': (),
            'trigger': 'interval',
            'seconds': RUN_TIME
        }
    ]


app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)
app.secret_key = get_merchant_login_cfg('secret_key')
app.config.from_object(Config)
scheduler = APScheduler()
scheduler.init_app(app)

# if 'Windows' == platform.system():
if 'Windows' == platform.system():
    # windows下用这个启动定时，linux用uwsgi部署，用mule模块启动
    try:
        scheduler.start()
        LOGGER.info(u"定时刷新session任务启动，%ss运行一次", RUN_TIME)
    except (KeyboardInterrupt, SystemExit):
        pass

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.session_protection = "strong"
login_manager.login_message = u"请输入用户名密码登录"
login_manager.login_message_category = "info"


# silly user model
class User(UserMixin):
    """
    https://github.com/shekhargulati/flask-login-example/blob/master/flask-login-example.py
    """

    def __init__(self, id):
        self.id = id
        name = None
        password = None
        if id == 1:
            name = 'admin'
            password = get_merchant_login_cfg('password')
        elif id == 0:
            name = 'root'
            password = get_merchant_login_cfg('password') + 'root'

        self.name = name
        self.password = password

    def __repr__(self):
        return "%d/%s/%s" % (self.id, self.name, self.password)


supported_users = {'admin': User(1), 'root': User(0)}


# callback to reload the user object
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', 0)
        user = supported_users.get(username)
        if not user:
            return abort(401)
        else:
            if password == user.password:
                # 记住1天3小时，这样可以隔天登录一次
                if remember:
                    login_user(user, remember=True,
                               duration=datetime.timedelta(days=1, hours=3, minutes=30, seconds=10))
                else:
                    login_user(user)
                return redirect(request.args.get("next") or url_for('batch_order'))
            else:
                return abort(401)
    else:
        return render_template('main/login.html')


# somewhere to logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('用户已登出', 'warning')
    return redirect('/')


@app.route('/order')
@login_required
def home():
    return render_template('main/order.html')


# 下载商户订单详细信息，入参：指定日期，默认昨天
@app.route('/order', methods=['POST'])
@login_required
def order():
    order_download_date = request.form.get('orderDownloadDate')
    session_id = request.form.get('sessionId')
    action_type = request.form.get('actionType')

    context = {'session_id': session_id, 'download_date': order_download_date, 'action_type': action_type}
    if action_type == 'download':
        # for test:
        # session_id = "0000si4l8ahug9VnJ9nlgD3seLD:-1"
        # order_download_date = '2018-02-03'

        merchant_summary = None
        order_detail_datas = None
        try:
            error, merchant_summary, order_detail_datas = query_order_detail(session_id, order_download_date)
            context['error'] = error
            context['merchant_summary'] = merchant_summary
            context['order_details'] = order_detail_datas

        except NoDataException as ex:
            context['error'] = ex.message
        except Exception as ex:
            context['error'] = ex.message
            LOGGER.exception("查询商户订单信息异常，Exception:%s", ex)

        try:
            save_order_data_to_excel(order_download_date, merchant_summary, order_detail_datas)
        except Exception as ex:
            LOGGER.exception("保存excel失败， Exception:%s", ex)
    elif action_type == 'merge':
        merge_res = merge_excel_helper(order_download_date)
        context['merge_res'] = merge_res
        context['error'] = merge_res.get('error', None)

    return render_template('main/order.html', **context)


@app.route('/')
@app.route('/index')
@app.route('/batch_order')
@login_required
def batch_order():
    return render_template('main/batch_order.html')


@app.route('/batch_order/manual_login', methods=['POST'])
@login_required
def manual_login():
    logon_id = request.form.get('logonId')
    res = {'status': False, 'error': ''}

    if not is_local_run_mode():
        # 不是本地模式跳过
        res['error'] = "服务器运行模式不支持登录，请在本地运行"
        return jsonify(res)
    try:
        merchant = get_merchant(logon_id)
        if merchant:
            res['status'] = browser.login(merchant)
        else:
            res['error'] = logon_id + "对应的商户数据未查询到, 请刷新页面重新加载商户配置数据"
    except Exception as ex:
        res['error'] = ex.message
    return jsonify(res)


@app.route('/batch_order/close_all_drivers')
@login_required
def close_all_drivers():
    count = 0
    try:
        if is_local_run_mode():
            count = close_all()
    except Exception as ex:
        LOGGER.error("关闭页面异常", ex)
    return jsonify(count)


@app.route('/batch_order/batch_login')
@login_required
def batch_login():
    if not is_local_run_mode():
        # 不是本地模式跳过
        return build_res("[服务器运行模式不支持登录，请在本地运行]")
    merchant_names = batch_fresh_login()
    return build_res(merchant_names)


@app.route('/batch_order/merge', methods=['POST'])
@login_required
def merge_orders():
    order_download_date = request.form.get('orderDownloadDate')
    error = None
    merge_res = dict()
    try:
        merge_res = merge_excel_helper(order_download_date)
    except Exception as ex:
        error = ex.message
    error = merge_res.get('error')

    # 之前数据格式是dict，转换为list
    detail = merge_res.get('detail')
    datas = list()
    if detail:
        for key in detail:
            datas.append({'storeName': key, 'totalCount': detail[key]})

    res = {'src': merge_res.get('src'), 'dst': merge_res.get('dst'), 'datas': datas,
           'totalCount': merge_res.get('total_count')}
    return build_res(res, error)


@app.route('/merchant_info')
@login_required
def get_merchant_info():
    res = refresh_merchant_config()
    return jsonify(res)


@app.route('/batch_order/download_order', methods=['POST'])
@login_required
def download_order():
    logon_id = request.form.get('logonId')
    order_download_date = request.form.get('orderDownloadDate')
    res = download_order_by_logon_id(logon_id, order_download_date, True)
    return jsonify(res)


@app.route('/batch_order/download_all', methods=['POST'])
@login_required
def download_all():
    order_download_date = request.form.get('orderDownloadDate')
    res = download_all_orders(order_download_date)
    return jsonify(res)


@app.route('/batch_order/export/<date>')
@login_required
def export_file(date):
    """
    中文名称IE乱码问题：
    https://stackoverflow.com/questions/21818855/flask-handling-unicode-text-with-werkzeug
    https://github.com/pallets/flask/issues/1286

    :param date:
    :return:
    """
    src, dst, dst_file_name, excel_saved_path = get_excel_path(date)
    filename = quote(dst_file_name.encode('utf-8'))
    try:
        res = send_from_directory(excel_saved_path, dst_file_name, as_attachment=True, attachment_filename=filename)
        res.headers['Content-Disposition'] += "; filename*=utf-8''{}".format(filename)
        return res
        # return send_from_directory(excel_saved_path, dst_file_name, as_attachment=True)
    except exceptions.NotFound as ex:
        return "%s的文件不存在，请检查日期" % date
    except Exception as ex:
        LOGGER.exception("导出文件异常%s", ex)
        return "导出失败: %s" % ex.message


@app.route('/batch_order/savecfg')
@login_required
def save_cfg():
    """
    保存当前页面的配置文件到本地配置文件中
    :return:
    """
    try:
        cfg = utils.get_merchant_cfg_file()
        datas = list()
        for key in MERCHANTS_DATA:
            datas.append(MERCHANTS_DATA.get(key).to_dict())
        if len(datas) == 0:
            return "无数据，忽略"
        with open(cfg, 'w') as json_file:
            json.dump(datas, json_file, ensure_ascii=False, indent=2)
            return "保存成功！"
    except Exception as ex:
        return build_res(error=ex.message)


@app.route('/help')
@login_required
def help():
    return render_template('main/help.html')


@app.route('/test')
@login_required
def test():
    # 测试生成excel
    return "test"


# handle login failed
@app.errorhandler(401)
def page_not_found(e):
    return Response('<p>登录失败,返回重新登录，不好意思，界面较丑，没时间搞，就这样吧</p>')


# @app.after_request
def set_response_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def is_local_run_mode():
    try:
        return 'LOCAL' in get_merchant_login_cfg('run_mode')
    except Exception:
        return False


def build_res(data=None, error=None):
    res = {'status': True}
    if error:
        res['status'] = False
    res['data'] = data
    res['error'] = error
    return jsonify(res)


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8888)
    except Exception as ex:
        LOGGER.exception("服务器启动失败，异常%s", ex)
