# coding:utf-8

import sys

from flask import Flask, render_template, request
from server.order import *
from server.log4cas import LOGGER
from server.excel import save_order_data_to_excel

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
@app.route('/home')
def home():
    return render_template('main/order.html')


# 下载商户订单详细信息，入参：指定日期，默认昨天
@app.route('/order', methods=['POST'])
def download_order():
    order_download_date = request.form['orderDownloadDate']
    session_id = request.form['sessionId']

    # for test:
    # session_id = "0000si4l8ahug9VnJ9nlgD3seLD:-1"
    # order_download_date = '2018-02-03'
    context = dict()
    merchant_summary = None
    order_detail_datas = None
    try:
        error, merchant_summary, order_detail_datas = query_order_detail(session_id, order_download_date)
        context = {
            'error': error,
            'session_id': session_id,
            'download_date': order_download_date,
            'merchant_summary': merchant_summary,
            'order_details': order_detail_datas
        }

    except Exception as ex:
        LOGGER.exception("查询商户订单信息异常，Exception:%s", ex)

    try:
        save_order_data_to_excel(merchant_summary, order_detail_datas)
    except Exception as ex:
        LOGGER.exception("保存excel失败， Exception:%s", ex)

    return render_template('main/order.html', **context)


@app.route('/help')
def help():
    return render_template('main/help.html')


@app.route('/test')
def test():
    # 测试生成excel
    return "test"


if __name__ == '__main__':
    app.run()
