# coding:utf-8

"""
ICBC订单查询

Author: karl(i@karlzhou.com)
"""

import json

import requests
from bs4 import BeautifulSoup

from model import *

# https://biz.elife.icbc.com.cn/businessHomeLogin/receiveCommon.action
ICBC_HOST = "https://biz.elife.icbc.com.cn/"


# TODO: 暂不考虑多门店情况，先处理一个登陆账号只有一个门店的场景

def query_order_detail(session_id, order_download_date):
    LOGGER.info(u"准备下载商户订单数据，session_id:[%s], date:[%s]", session_id, order_download_date)

    error = None
    # 商户指定日期的汇总数据
    merchant_summary = dict()

    session_id = format_session_id(session_id)
    session = get_session(session_id)

    # 1.检查是否有效session
    error = check_session_validation(session)
    if error:
        return error, None, None

    # 2.获取商户id
    error, shop_id = get_merchant_shop_id(session)
    if error:
        return error, None, None
    LOGGER.info(u"session_id:[%s]对应的门店id:[%s]", session_id, shop_id)
    if error:
        return error, None, None

    # 校验日期
    if not order_download_date or not order_download_date.strip():
        error = u"输入日期为空"
        return error, None, None

    order_date = order_download_date.strip()
    # 4.查看商户指定日期summary
    error, merchant_trade_summary = get_merchant_order_summary(session, shop_id, order_date)
    LOGGER.info(u"查看商户指定日期交易汇总,error:[%s],data:(%s)", error, merchant_trade_summary)

    if error:
        return error, None, None

    # 5.获取详细交易订单
    error, order_detail_datas = get_order_trade_list(session, shop_id, order_date)
    LOGGER.info(u"获取详细交易订单，error:[%s], 总个数:[%s]", error, len(order_detail_datas))

    if not order_detail_datas:
        error = order_download_date + "无详细数据，忽略"

    # 转换dict为对象，后续处理方便
    trade_details = list()
    for order_detail in order_detail_datas:
        trade_details.append(convert_raw_detail_order_to_model(order_detail))
    return error, merchant_trade_summary, trade_details


def get_session(session_id):
    """
    返回一个request的session
    :param session_id:
    :return:
    """
    headers = {
        'Host': 'biz.elife.icbc.com.cn',
        'Referer': 'https://biz.elife.icbc.com.cn/store_login/loginStart.action',
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; Tablet PC 2.0)'
    }
    s = requests.Session()
    s.headers.update(headers)
    s.cookies.update({'JSESSIONID': session_id})
    return s


def check_session_valid(session_id):
    """
    检查session是否有效
    :param session_id:
    :return:
    """
    if not session_id:
        return False, "session为空"
    session_id = format_session_id(session_id)
    session = get_session(session_id)
    error = check_session_validation(session)
    if error:
        return False, error
    else:
        return True, None


# 检查session_id是否合法
def check_session_validation(session):
    """
    检查是否有效的session，根据是否能获取到操作员流水，来判断
    :param session:
    :return:
    """
    error = None

    res = session.post(build_icbc_url("storeUserInfo/pageStreamList.action"))

    LOGGER.info("session=%s" % res.text)

    if not res.ok or res.status_code != 200:
        error = "检查session是否有效请求发送失败,status_code=%s, reason=%s" % (res.status_code, res.reason)
        LOGGER.error(error)
        return error

    # 判断是否存在字符串："由于您长时间未做任何操作，请重新登录！"
    if u'由于您长时间未做任何操作，请重新登录' in res.text:
        return u"session过期or输入错误，请重新输入"

    return None


def get_merchant_shop_id(session):
    """
    访问链接https://biz.elife.icbc.com.cn/trade/findTradeDetail.action
    读取元素 <input id="merserialno" type="hidden" value="16050005980">
    :param session:
    :return:
    """
    error = None
    res = session.get(build_icbc_url("trade/findTradeDetail.action"))
    if not res.ok or res.status_code != 200:
        LOGGER.error(u"获取商户门店id失败" + res.reason)
        return error, None

    soup = BeautifulSoup(res.text, 'html.parser')
    try:
        shop_id = soup.find('input', {'id': 'merserialno'}).get('value')
        return error, shop_id
    except Exception:
        return "shop_id获取非法,请检查html网页格式", None


def get_operator_id(session):
    """
    登陆账号是操作员id,获取操作员id后，去掉末尾三位得到商户id
        -- 不正确，会出现和不一样的场景，如宾客来的登录id和门店id是不一样

    :param session: `requests`
    :return:
    """
    error = None
    # 操作员流水页面
    res = session.post(build_icbc_url("storeUserInfo/pageStreamList.action"))
    if not res.ok or res.status_code != 200:
        LOGGER.error(u"获取操作员流水失败" + res.reason)
        return error, None

    error, json_data = get_json(res, "解析操作员登陆流水失败")
    if error:
        return error, None

    op_id = None
    try:
        op_id = json_data.get('data')[0].get('OPNAME')
    except Exception as ex:
        error = u"json数据格式有变化，未获取到有效的操作员id"
        LOGGER.error(error + ",Exception:", ex)

    return error, op_id


def get_merchant_order_summary(session, shop_id, date, sel_type='p'):
    """
    https://biz.elife.icbc.com.cn/trade/findStoreTrade.action
    shopIds:[16050004354]
    orderDate:2018-02-04
    selType:p
    :param shop_id:
    :param date:
    :param sel_type: 默认'p' 销售
    :return:
    """
    error = None
    find_store_trade_url = build_icbc_url(
        "trade/findStoreTrade.action" + "?orderDate=" + date + "&selType=" + sel_type + "&shopIds=[" + shop_id + "]")
    res = session.post(url=find_store_trade_url)

    tip = u"查询商户交易统计数据"
    if not res.ok or res.status_code != 200:
        error = tip + u"请求失败" + res.reason
        LOGGER.error(error)
        return error, None

    error, json_data = get_json(res, tip)
    if error:
        return error, None

    error = json_data.get('errorMsg')
    if error:
        return tip + error, None

    # 正常只有个店，无分店，也只有一页
    total = json_data['total']
    if total > 1:
        return tip + u",门店个数不等于1,total=" + str(total), None
    elif total == 0:
        LOGGER.info(u"%s %s 无数据，请重新选择日期", tip, date)
        raise NoDataException(u"%s %s 无数据，请重新选择日期" % (tip, date))

    trade_json_data = json_data.get('list')[0]
    # 组装trade summary对象
    trade_summary_data = TradeSummary()
    trade_summary_data.order_date = trade_json_data.get('order_date')
    trade_summary_data.shop_id = trade_json_data.get('shop_id')
    trade_summary_data.store_name = trade_json_data.get('store_name')
    trade_summary_data.total_amount = trade_json_data.get('total_amount')
    trade_summary_data.total_dis_amt = trade_json_data.get('total_dis_amt')
    trade_summary_data.total_ecoupon_amt = trade_json_data.get('total_ecoupon_amt')
    trade_summary_data.total_money = trade_json_data.get('total_money')
    trade_summary_data.total_point_amt = trade_json_data.get('total_point_amt')

    return error, trade_summary_data


def get_order_trade_list(session, shop_id, date, sel_type='p'):
    """
    https://biz.elife.icbc.com.cn/trade/findTradeOrderList.action
    :param session:
    :param shop_id:
    :param date:
    :param query_type:
    :param current_page: 当前页数
    :return:
    """

    error = None
    # 获取第一页
    next_page = 1
    has_next_page = True
    trade_list_datas = list()
    while has_next_page:
        find_store_trade_url = get_trade_order_list_url(shop_id, date, next_page, sel_type)
        res = session.post(url=find_store_trade_url)
        tip = u"查询商户交易详细数据,第" + str(next_page) + u"页"
        if not res.ok or res.status_code != 200:
            error = tip + u"请求失败" + res.reason
            LOGGER.error(error)
            return error, None

        error, json_data = get_json(res, tip)
        if error:
            return error, None

        error = json_data.get('errorMsg')
        if error:
            return tip + error, None

        has_next_page = json_data.get('hasNextPage')
        next_page = json_data.get('nextPage')

        tmp_list = json_data.get('list')
        trade_list_datas += tmp_list

    trade_list_datas.sort(key=lambda k: (k.get('orderTime', 0)), reverse=True)

    return error, trade_list_datas


def get_trade_order_list_url(shop_id, order_date, current_page, sel_type):
    return build_icbc_url(
        "trade/findTradeOrderList.action" +
        "?currentPage=" + str(current_page) +
        "&orderDate=" + order_date +
        "&selType=" + sel_type +
        "&shopId=" + shop_id)


# 利用session登录

def format_session_id(session_id):
    return session_id.strip()


def format_order_date(order_date):
    # TODO: 检查下载日期，转换为ms
    now = datetime.datetime.now()
    return now


def build_icbc_url(url):
    return ICBC_HOST + url


def get_json(res, message):
    json_data = dict
    try:
        json_data = json.loads(res.text)
    except Exception, ex:
        error = message + u"非法json"
        LOGGER.error(error + ",Exception:", ex)
        return error, None
    return None, json_data


def convert_raw_detail_order_to_model(order_detail):
    """
    把原始json中的dict数据转换为model

    Sample：
    {
      "admibrno": "84",
      "cardNo": "622910******3477",
      "carriageAmt": 0,
      "custid": "EP2015081818476620",
      "customer": "黄子涛",
      "disamt": 0,
      "ecouponAmt": 0,
      "feeAmt": 0,
      "firstPayAmt": 0,
      "goodsId": "d01605170218958861",
      "installmentTimes": 1,
      "isInstallmentFlag": 0,
      "merAcct": "6222081605001343682",
      "merUrl": "https://elife.icbc.com.cn/OFSTCUST/order/appReturn.action",
      "mercname": "枣庄市薛城区尚得利家用电器经营部",
      "mername": "枣庄市薛城区尚得利家用电器经营部",
      "mertId": "16050004354",
      "mobilephone": "13560934349",
      "orderAmt": 418800,
      "orderChannel": "314",
      "orderCurr": "001",
      "orderDate": 1517800419000,
      "orderId": "160557220163201802058958861",
      "orderLang": "zh_CN",
      "orderStatus": "2",
      "orderTime": 1517800403000,
      "payWay": "1",
      "pbocmcc": "5722",
      "pointAmt": 0,
      "saccname": "杨尚卫",
      "serialno": "HEZ000005758378072",
      "shopId": "160557220163",
      "storename": "薛城区尚得利家用电器经营部",
      "totalAmount": 418800,
      "tranType": "0",
      "tranWay": "e生活扫描商户二维码",
      "transerialnum": "0302016054859100001632908986",
      "verifyjoinFlag": "0",
      "ylmerno": "454057220161",
      "zone": "1605"
    }
    :param order_detail:
    :return: `TradeDetail`
    """

    if not order_detail:
        LOGGER.warning("转换输入参数非法，为空")
        return None

    trade_deatil_model = TradeDetail()
    # FIXME: 有两个mername和mercname
    trade_deatil_model.store_name = order_detail.get('storename')
    trade_deatil_model.order_date = order_detail.get('orderDate')
    # FIXME: time和excel里下载的交易日期对不上，感觉是icbc的bug，先不管了，保持和excel一致
    # trade_deatil_model.order_time = order_detail.get('orderTime')
    trade_deatil_model.order_time = order_detail.get('orderDate')
    trade_deatil_model.order_time_full = order_detail.get('orderDate')
    trade_deatil_model.order_id = order_detail.get("orderId")
    trade_deatil_model.card_no = order_detail.get('cardNo')
    trade_deatil_model.order_amt = order_detail.get('orderAmt')
    trade_deatil_model.dis_amt = order_detail.get('disamt')
    # FIXME: totalAmount 和 feeAmt 含义不确定，且excel上未显示feeAmt值
    trade_deatil_model.total_amount = order_detail.get('totalAmount')
    trade_deatil_model.point_amt = order_detail.get('pointAmt')
    trade_deatil_model.ecoupon_amt = order_detail.get('ecouponAmt')
    trade_deatil_model.tran_type = order_detail.get('tranType')
    trade_deatil_model.tran_way = order_detail.get('tranWay')
    return trade_deatil_model
