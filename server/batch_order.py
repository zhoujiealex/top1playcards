# coding:utf-8

"""
ICBC批量订单下载

Author: karl(i@karlzhou.com)
"""
from gevent import monkey

from log4cas import LOGGER
from model import MerchantInfo, TradeDetail, TradeSummary
from model import NoDataException
from utils import read_merchant_cfg

monkey.patch_all()
from gevent.pool import Pool
from order import check_session_valid, query_order_detail
from excel import save_order_data_to_excel

# 商户缓存数据，以登录账户为key
MERCHANTS_DATA = dict()
MERCHANTS_DATA_REFRESH_POOL = Pool(20)


def refresh_merchant_config():
    """
    刷新商户状态和配置等
    :return:
    """
    cfgs = get_merchant_config()
    check_status(cfgs)
    res = list()
    for d in cfgs:
        res.append(d.to_dict())
    return res


def get_merchant_config():
    merchant_cfg_datas = read_merchant_cfg()
    res = list()
    for merchant in merchant_cfg_datas:
        logon_id = merchant.get('logonId')
        merchant_info = MerchantInfo()
        merchant_info.alias = merchant.get("alias")
        merchant_info.logon_id = logon_id
        merchant_info.mcc = merchant.get("mcc")
        merchant_info.shop_id = merchant.get("shopId")
        merchant_info.store_name = merchant.get("storeName")
        merchant_info.session_id = merchant.get("sessionId")

        merchant_data = MERCHANTS_DATA.get(logon_id)
        data = None
        if not merchant_data:
            # 若缓存为空
            MERCHANTS_DATA[logon_id] = merchant_info
            data = merchant_info
        else:
            # 若缓存中已存在，则更新
            merchant_data.alias = merchant_info.alias
            merchant_data.logon_id = merchant_info.logon_id
            merchant_data.mcc = merchant_info.mcc
            if not merchant_data.session_id:
                # TODO: 后续再考虑增加导入session覆盖的功能
                # 缓存里为空才更新
                merchant_data.session_id = merchant_info.session_id
            merchant_data.store_name = merchant_info.store_name
            merchant_data.shop_id = merchant_info.shop_id
            data = merchant_data
        res.append(data)
    return res


def get_merchant(logon_id):
    """
    获取缓存的商户信息
    :param logon_id:
    :return:
    """
    return MERCHANTS_DATA.get(logon_id)


def check_status(cfgs):
    """
    检查session有效性
    :param cfgs: list of `MerchantInfo`
    :return:
    """
    # gevent并发检查session有效性
    merchants = list()
    for cfg in cfgs:
        if isinstance(cfg, MerchantInfo):
            merchants.append(cfg)
    MERCHANTS_DATA_REFRESH_POOL.map(check_status_merchant, merchants)


def check_status_merchant(merchant_info):
    if not isinstance(merchant_info, MerchantInfo):
        return False
    res, error = check_session_valid(merchant_info.session_id)
    if res:
        LOGGER.debug(u"商户(%s)的session有效性=%s", merchant_info.alias, res)
    merchant_info.status = res
    return res


def download_order_by_logon_id(logon_id, order_download_date, need_save=False):
    error, summary, orders = _download_order_by_logon_id_helper(logon_id, order_download_date)

    res = _format_merchant_data(error, summary, orders)

    if need_save and res.get('status'):
        try:
            file_path = save_order_data_to_excel(order_download_date, summary, orders)
            res['tip'] = "数据保存成功，文件路径：%s" % file_path
        except Exception as ex:
            res['error'] += "; %s" % ex.message
    return res


def _download_order_by_logon_id_helper(logon_id, order_download_date):
    """
    根据登陆账号下载数据
    :param logon_id:
    :param order_download_date:
    :return: error, `TradeSummary`, `TradeDetail`
    """
    error = None
    if not logon_id:
        error = "登陆账号为空，请检查"
        return error, None, None
    merchant = get_merchant(logon_id)
    if not merchant:
        error = "根据%s未查找到合适的商户数据，请检查" % logon_id
        return error, None, None

    # 检查session有效性
    session_validation = check_status_merchant(merchant)
    if not session_validation:
        error = "商户%s的session无效，请检查后or重新登录" % logon_id
        return error, None, None

    # 开始下载数据
    try:
        return query_order_detail(merchant.session_id, order_download_date)
    except NoDataException:
        # 商户无数据
        return "商户[%s]%s无数据，请重新选择日期下载" % (merchant.alias, order_download_date), None, None
    except Exception as ex:
        LOGGER.exception("下载商户订单数据异常")
        error = "下载商户订单数据发生异常:%s" % ex.message
        return error, None, None


def _format_merchant_data(error, summary, orders, tip=None):
    """
    格式商户数据
    :param error:
    :param summary:
    :param orders:
    :param path: 文件保存路径
    :return: `dict`
    """
    res = {'status': False, 'summary': [], 'orders': [], 'error': None, 'tip': tip}
    try:
        summary_data = dict()
        orders_data = list()
        if error:
            res['status'] = False
            res['error'] = error
        else:
            res['status'] = True
            if isinstance(summary, TradeSummary):
                summary_data = summary.to_dict()
            if isinstance(orders, list):
                for order in orders:
                    if isinstance(order, TradeDetail):
                        orders_data.append(order.to_dict())
            res['summary'].append(summary_data)
            res['orders'] = orders_data
    except Exception as ex:
        LOGGER.exception("下载商户订单数据异常")
        res['error'] = "下载商户订单数据发生异常:%s" % ex.message
    return res
