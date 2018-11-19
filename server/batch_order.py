# coding:utf-8

"""
ICBC批量订单下载

Author: karl(i@karlzhou.com)
"""
import datetime
import os
import pickle
import random

import gevent
from gevent import monkey

from log4cas import LOGGER
from model import MerchantInfo, TradeDetail, TradeSummary
from model import NoDataException
from utils import read_merchant_cfg, get_refresh_threshold, get_now_str, get_now_date_str

monkey.patch_all()
from gevent.pool import Pool
from order import check_session_valid, query_order_detail
from excel import save_order_data_to_excel, batch_save_order_data_to_excel

# 商户缓存数据，以登录账户为key
MERCHANTS_DATA = dict()
MERCHANTS_DATA_REFRESH_POOL = Pool(20)
SUMMARY_INFO = dict()


def refresh_merchant_config(from_front=False):
    """
    刷新商户状态和配置等
    :return:
    """
    LOGGER.info(u"获取商户配置数据")
    cfgs = get_merchant_config()
    if can_refresh(from_front):
        check_status(cfgs)
    res = list()
    count = 0
    for d in cfgs:
        res.append(d.to_dict())
        if d.status:
            count += 1
    LOGGER.info(u"在线商户:%s", count)
    record_offline_time(count)
    return sort_merchant(res)


def sort_merchant(merchant_list):
    """
    排序，已登录的排在前面
    :param merchant_list:
    :return:
    """
    valid_merchants = list()
    invalid_merchants = list()
    for m in merchant_list:
        if m['status']:
            valid_merchants.append(m)
        else:
            invalid_merchants.append(m)
    valid_merchants.sort()
    invalid_merchants.sort()
    return valid_merchants + invalid_merchants


def record_offline_time(count):
    """
    尝试记录商户全部掉线时间
    :param count: 当前在线商户个数
    :return:
    """
    global SUMMARY_INFO
    SUMMARY_INFO["last_valid_count"] = SUMMARY_INFO.get("current_valid_count", None)
    SUMMARY_INFO["current_valid_count"] = count

    if SUMMARY_INFO["last_valid_count"] and count <= 0:
        # 最近一次不同，且有非0->0，说明下线了
        SUMMARY_INFO['offline_time'] = get_now_str()

    if not SUMMARY_INFO["last_valid_count"] and count:
        SUMMARY_INFO['online_time'] = get_now_str()


def can_refresh(from_front):
    """
    是否可以刷新，前台需要满足随机数百分比，后台定时总是要刷新
    :param from_front:
    :return:
    """
    if from_front and not frontend_need_refresh():
        return False
    return True


def frontend_need_refresh():
    """
    利用随机数来控制前台是否要强制刷新
    :return:
    """
    magic = random.randint(0, 100)
    threshold = get_refresh_threshold()
    return magic <= threshold


def get_merchant_config():
    global MERCHANTS_DATA
    merchant_cfg_datas = read_merchant_cfg()
    res = list()
    for merchant in merchant_cfg_datas:
        logon_id = merchant.get('logonId')
        merchant_info = MerchantInfo()
    record_offline_time(1)


def can_refresh(from_front):
    """
    是否可以刷新，前台需要满足随机数百分比，后台定时总是要刷新
    :param from_front:
    :return:
    """
    if from_front and not frontend_need_refresh():
        return False
    return True


def frontend_need_refresh():
    """
    利用随机数来控制前台是否要强制刷新
    :return:
    """
    magic = random.randint(0, 100)
    threshold = get_refresh_threshold()
    return magic <= threshold


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


def summary_merchant_status(order_download_date):
    """
    统计当前商户的各种信息，如登录数，总数，缓存刷新时间等。
    :return:
    """
    global SUMMARY_INFO
    SUMMARY_INFO['totalMerchant'] = len(MERCHANTS_DATA)
    SUMMARY_INFO['totalValidMerchant'] = 0
    for m in MERCHANTS_DATA:
        if MERCHANTS_DATA.get(m).status:
            SUMMARY_INFO['totalValidMerchant'] += 1
    # if ALL_MERCHANT_DATA_CACHE.get("updateAt"):
    #     SUMMARY_INFO["allDataUpdateAt"] = ALL_MERCHANT_DATA_CACHE.get("updateAt")
    SUMMARY_INFO[order_download_date] = get_file_modified_time(order_download_date)
    return SUMMARY_INFO


def check_status_merchant(merchant_info):
    if not isinstance(merchant_info, MerchantInfo):
        return False
    res, error = check_session_valid(merchant_info.session_id)
    if res:
        LOGGER.debug(u"商户(%s)的session有效性=%s", merchant_info.alias, res)
    merchant_info.status = res
    return res


def download_all_orders(order_download_date=None, enable_cache=False):
    """
    下载所有的商户，过滤session无效的
    :param order_download_date:
    :return:
    res = {'status': False, 'summary': summary, 'orders': orders, 'errors': errors, 'warnings': warnings, 'tip': ''}
    """
    if not order_download_date:
        order_download_date = get_now_date_str()

    if enable_cache:
        return get_all_data_from_cache(order_download_date)

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
        elif job_error:
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
    save_all_data_to_cache(order_download_date, res)
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
        error = "有部分商户未登录无法下载（已自动忽略），请检查后重新登录该部分商户"
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
        LOGGER.exception("下载商户订单数据异常%s", ex)
        res['error'] = "下载商户订单数据发生异常:%s" % ex.message
    return res


def get_all_data_from_cache(order_download_date):
    """
    从缓存中获取所有商户信息数据
    :return:
    """
    try:
        cache_file_full_path = get_cache_full_path(order_download_date)
        with open(cache_file_full_path, 'rb') as cache_file:
            res = pickle.load(cache_file)
            LOGGER.info("加载商户缓存数据成功")
            return res
    except Exception as ex:
        LOGGER.error("加载商户缓存数据异常，Exception=%s", ex)


def save_all_data_to_cache(order_download_date, res):
    """
    保存所有信息到缓存
    :return:
    """
    if not is_valid_data(res):
        LOGGER.warn("跳过刷新商户数据缓存，无效的缓存。res=%s", res)
        return None

    try:
        cache_file_full_path = get_cache_full_path(order_download_date)
        with open(cache_file_full_path, 'wb') as cache_file:
            pickle.dump(res, cache_file)
            LOGGER.info("刷新商户数据缓存成功,tip=%s", res.get('tip'))
    except Exception as ex:
        LOGGER.error("刷新商户数据缓存异常，%s", ex)


def is_valid_data(data):
    """
    判断是否有效数据，有效则尝试缓存
    :param datas:
    :return:
    """
    if data.get('status'):
        return True

    if len(data.get('orders', [])) > 0:
        return True

    if len(data.get('summary', [])) > 0:
        return True

    if not data.get('errors'):
        return True

    if "无数据，请重新选择日期下载" in data.get('errors'):
        return True

    return False


def get_cache_path():
    """
    获取缓存存放全路径，相对于当前文件
    :return:
    """
    cache_path = os.path.join(os.path.dirname(__file__), '../', 'cache')
    if not os.path.exists(cache_path):
        os.mkdir(cache_path)
    return cache_path


def get_cache_full_path(file_name):
    return os.path.normpath(os.path.join(get_cache_path(), file_name))


def get_file_modified_time(order_download_date):
    file_path = get_cache_full_path(order_download_date)
    if os.path.exists(file_path):
        modify_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        return modify_time.strftime('%Y-%m-%d %H:%M:%S')
    return "-"
