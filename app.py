# coding:utf-8

import sys

from flask import Flask, render_template, request, jsonify, flash

from server.batch_order import refresh_merchant_config, get_merchant
from server.browser import *
from server.excel import save_order_data_to_excel, merge_excel_helper
from server.order import *

reload(sys)
sys.setdefaultencoding('utf-8')

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)
app.secret_key = 'top_1_play_cards'

# 商户登录成功后的缓存，包括session
merchants = dict()


@app.route('/')
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

        except Exception as ex:
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


@app.route('/batch_order')
def batch_order():
    return render_template('main/batch_order.html')


@app.route('/batch_order/manual_login', methods=['POST'])
def manual_login():
    logon_id = request.form.get('logonId')
    res = {'status': False, 'error': ''}
    try:
        merchant = get_merchant(logon_id)
        if merchant:
            res['status'] = login(merchant)
        else:
            res['error'] = logon_id + "对应的商户数据未查询到, 请刷新页面重新加载商户配置数据"
    except Exception as ex:
        res['error'] = ex.message
    return jsonify(res)


@app.route('/batch_order/close_all_drivers')
def close_all_drivers():
    try:
        close_all()
    except Exception as ex:
        LOGGER.error("关闭页面异常", ex)
    return 'ok'


@app.route('/merchant_info')
def get_merchant_info():
    res = refresh_merchant_config()
    return jsonify(res)


@app.route('/help')
def help():
    return render_template('main/help.html')


@app.route('/test')
def test():
    # 测试生成excel
    return "test"


if __name__ == '__main__':
    app.run(port=8888)
