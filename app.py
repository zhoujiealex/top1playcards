# coding:utf-8

import datetime
import logging
import logging.handlers

from flask import Flask, render_template, flash, request
from server.order import *
from server.log4cas import LOGGER

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
    session_id = "0000R65hdcaOyn89LEZAg5I_vGh:-1"
    # order_download_date = '2018-02-03'

    error, merchant_summary, order_detail_datas = download_order_detail(session_id, order_download_date)

    context = {
        'error': error,
        'session_id': session_id,
        'download_date': order_download_date,
        'merchant_summary': merchant_summary,
        'order_details': order_detail_datas
        # 'order_details': {}
    }

    return render_template('main/order.html', **context)


@app.route('/help')
def help():
    return render_template('main/help.html')


def log_on(session_id, orderDownloadDate):
    return "1"


if __name__ == '__main__':
    app.run()
