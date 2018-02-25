# coding:utf-8

"""
ICBC批量订单下载

Author: karl(i@karlzhou.com)
"""
import gevent
from gevent import monkey

from log4cas import LOGGER
from model import MerchantInfo, TradeDetail, TradeSummary
from model import NoDataException
from utils import read_merchant_cfg

monkey.patch_all()
from gevent.pool import Pool
from order import check_session_valid, query_order_detail
from excel import save_order_data_to_excel, batch_save_order_data_to_excel

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
    global MERCHANTS_DATA
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
            if merchant_info.alias:
                # 以配置文件为准
                merchant_data.alias = merchant_info.alias
            if merchant_info.logon_id:
                # 以配置文件为准
                merchant_data.logon_id = merchant_info.logon_id
            if merchant_info.mcc:
                # mcc 获取不到，以配置文件为准
                merchant_data.mcc = merchant_info.mcc
            if not merchant_data.session_id:
                # TODO: 后续再考虑增加导入session覆盖的功能
                # 缓存里为空才更新
                merchant_data.session_id = merchant_info.session_id
            if merchant_info.store_name and not merchant_data.store_name:
                # storeName可以自动获取到，当缓存为空，配置非空更新
                merchant_data.store_name = merchant_info.store_name
            if merchant_info.shop_id and not merchant_data.shop_id:
                # 同上说明，shop_id一般人获取不到
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
    global MERCHANTS_DATA
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


def download_all_orders(order_download_date):
    """
    下载所有的商户，过滤session无效的
    :param order_download_date:
    :return:
    res = {'status': False, 'summary': summary, 'orders': orders, 'errors': errors, 'warnings': warnings, 'tip': ''}
    """
    jobs = list()
    jobs_dict = dict()
    for key in MERCHANTS_DATA:
        merchant = MERCHANTS_DATA[key]
        if isinstance(merchant, MerchantInfo):
            logon_id = merchant.logon_id
            greenlet = gevent.spawn(_download_order_by_logon_id_helper, logon_id, order_download_date)
            jobs.append(greenlet)
            jobs_dict[logon_id] = greenlet

    gevent.joinall(jobs)
    # 获取每个任务的结果输出
    warnings = list()
    errors = list()
    # 用于前台返回
    summary = list()
    orders = list()
    # 用于生成excel
    summary_dict = dict()
    orders_dict = dict()
    res = {'status': True, 'summary': summary, 'orders': orders, 'errors': errors, 'warnings': warnings, 'tip': ''}
    # 按照配置文件的顺序组装最终返回数据
    logon_ids = get_merchants_logon_ids()
    valid_logon_ids = list()
    for logon_id in logon_ids:
        job = jobs_dict.get(logon_id)
        merchant = get_merchant(logon_id)
        if isinstance(job, gevent.greenlet.Greenlet):
            job_error, job_summary, job_orders = job.get()
        else:
            LOGGER.warn("%s对应的返回数据为None，跳过,请刷新页面，加载配置数据", logon_id)
            continue
        if is_no_data(job_error):
            warnings.append("商户[%s]%s无数据，跳过" % (merchant.alias, order_download_date))
        if job_error:
            errors.append(job_error)
            # 有一个状态失败，则都失败
            res['status'] = False
        else:
            summary.append(job_summary.to_dict())
            for job_order in job_orders:
                orders.append(job_order.to_dict())
            summary_dict[logon_id] = job_summary
            orders_dict[logon_id] = job_orders
            valid_logon_ids.append(logon_id)

    try:
        file_path = batch_save_order_data_to_excel(order_download_date, valid_logon_ids, summary_dict, orders_dict)
        res['tip'] = "成功处理了%s个商户,%s条订单，文件路径：%s" % (len(valid_logon_ids), len(orders), file_path)
    except Exception as ex:
        LOGGER.exception("批量保存邮件异常：%s", ex)
        errors.append("保存excel异常%s" % ex.message)
    return res


def is_no_data(res):
    """
    tricky -- 判断是否无数据，批量下载的时候，无数据忽略，只记录
    :param res:
    :return:
    """
    if res:
        return '无数据，请重新选择日期下载' in res
    return False


def get_merchants_logon_ids():
    # 获取商户排序，根据配置文件里的数据来显示
    cfgs = get_merchant_config()
    logon_ids = list()
    for cfg in cfgs:
        if isinstance(cfg, MerchantInfo):
            logon_ids.append(cfg.logon_id)
    return logon_ids


def download_order_by_logon_id(logon_id, order_download_date, need_save=False):
    error, summary, orders = None, None, None
    try:
        error, summary, orders = _download_order_by_logon_id_helper(logon_id, order_download_date)
    except Exception as ex:
        error = "发生异常：%s" % ex.message

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
    summary = None
    orders = None
    try:
        error, summary, orders = query_order_detail(merchant.session_id, order_download_date)
    except NoDataException as ex:
        # 商户无数据
        return "商户[%s]%s无数据，请重新选择日期下载" % (merchant.alias, order_download_date), None, None
    except Exception as ex:
        LOGGER.exception("下载商户订单数据异常")
        error = "下载商户订单数据发生异常:%s" % ex.message
        return error, None, None

    try:
        if isinstance(summary, TradeSummary):
            # 更新缓存里的商户数据
            merchant.store_name = summary.store_name
            merchant.shop_id = summary.shop_id
    except Exception as ex:
        LOGGER.exception("更新缓存商户%s数据发送异常，不影响业务，忽略。 Exception:%s", logon_id, ex)

    return error, summary, orders


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