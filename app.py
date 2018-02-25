# coding:utf-8

import sys
from urllib import quote

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_apscheduler import APScheduler
from werkzeug import exceptions

from server.batch_order import refresh_merchant_config, get_merchant, download_order_by_logon_id, download_all_orders
from server.browser import *
from server.excel import save_order_data_to_excel, merge_excel_helper, get_excel_path
from server.order import *
from server.utils import get_merchant_login_cfg

reload(sys)
sys.setdefaultencoding('utf-8')


class Config(object):
    JOBS = [
        {
            'id': 'checkSessionValidation',
            'func': 'server.batch_order:refresh_merchant_config',
            'args': (),
            'trigger': 'interval',
            'seconds': 5 * 60
        }
    ]


app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)
app.secret_key = 'top_1_play_cards'
app.config.from_object(Config)


@app.route('/order')
def home():
    return render_template('main/order.html')


# 下载商户订单详细信息，入参：指定日期，默认昨天
@app.route('/order', methods=['POST'])
def order():
    order_download_date = request.form['orderDownloadDate']
    session_id = request.form['sessionId']
    action_type = request.form['actionType']

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
@app.route('/batch_order')
def batch_order():
    return render_template('main/batch_order.html')


@app.route('/batch_order/manual_login', methods=['POST'])
def manual_login():
    logon_id = request.form.get('logonId')
    res = {'status': False, 'error': ''}

    if not is_local_run_mode():
        # 不是本地模式跳过
        res['error'] = "服务器运行模式不支持登录，请在本地运行"
        return jsonify(res)
    try:
        merchant = get_merchant(logon_id)
        print(merchant)
        if merchant:
            res['status'] = login(merchant)
        else:
            res['error'] = logon_id + "对应的商户数据未查询到, 请刷新页面重新加载商户配置数据"
    except Exception as ex:
        res['error'] = ex.message
    return jsonify(res)


@app.route('/batch_order/close_all_drivers')
def close_all_drivers():
    count = 0
    try:
        if is_local_run_mode():
            count = close_all()
    except Exception as ex:
        LOGGER.error("关闭页面异常", ex)
    return jsonify(count)


@app.route('/batch_order/batch_login')
def batch_login():
    if not is_local_run_mode():
        # 不是本地模式跳过
        return build_res("[服务器运行模式不支持登录，请在本地运行]")
    merchant_names = batch_fresh_login()
    return build_res(merchant_names)


@app.route('/batch_order/merge', methods=['POST'])
def merge_orders():
    order_download_date = request.form['orderDownloadDate']
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
def get_merchant_info():
    res = refresh_merchant_config()
    return jsonify(res)


@app.route('/batch_order/download_order', methods=['POST'])
def download_order():
    logon_id = request.form.get('logonId')
    order_download_date = request.form['orderDownloadDate']
    res = download_order_by_logon_id(logon_id, order_download_date, True)
    return jsonify(res)


@app.route('/batch_order/download_all', methods=['POST'])
def download_all():
    order_download_date = request.form['orderDownloadDate']
    res = download_all_orders(order_download_date)
    return jsonify(res)


@app.route('/batch_order/export/<date>')
def export_file(date):
    """
    中文名称IE乱码问题：
    https://stackoverflow.com/questions/21818855/flask-handling-unicode-text-with-werkzeug
    https://github.com/pallets/flask/issues/1286

    :param date:
    :return:
    """
    # order_download_date = request.form['orderDownloadDate']
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


@app.route('/help')
def help():
    return render_template('main/help.html')


@app.route('/test')
def test():
    # 测试生成excel
    return "test"


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

    # 启动定时
    scheduler = APScheduler()
    scheduler.init_app(app)
    try:
        scheduler.start()
        LOGGER.info("定时刷新session任务启动，5min运行一次")
    except (KeyboardInterrupt, SystemExit):
        pass

    app.run(port=8888)
