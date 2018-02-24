# coding:utf-8

"""
利用selenium来操作浏览器

Author: karl(i@karlzhou.com)
"""
import time

import gevent
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import order
import utils
from batch_order import MERCHANTS_DATA
from log4cas import LOGGER
from model import MerchantInfo

DRIVERS = []


def login(merchant_info):
    """
    登录商户
    :param merchant_info: `MerchantInfo`
    :return:
    """
    if not isinstance(merchant_info, MerchantInfo):
        raise Exception("参数类型错误，非MerchantInfo")

    logon_id = merchant_info.logon_id
    status = merchant_info.status
    session_id = merchant_info.session_id
    session_valid = False
    try:
        session_valid, error = order.check_session_valid(session_id)
    except Exception as ex:
        session_valid = False

    if session_valid:
        merchant_info.status = True
        # 复用有效的session，不需要登录
        re_login(session_id)
    else:
        merchant_info.status = False
        # 重新打开新窗口后，保存新生成的sessionId
        fresh_session_id = fresh_login(logon_id)
        if fresh_session_id:
            merchant_info.session_id = fresh_session_id
    return True


def fresh_login(logon_id):
    """
    全新登录，返回新打开页面的sessionId
    :param logon_id:
    :return: `str`
    """
    if not logon_id:
        return None
    # driver = webdriver.Ie()
    driver = webdriver.Chrome()
    gevent.sleep(0)
    driver.implicitly_wait(10)
    DRIVERS.append(driver)
    driver.get(_get_login_url())
    loaded = wait_element_loaded(driver, 3, _get_input_id())
    if not loaded:
        # 如果显示等待还未成功，再尝试sleep一会
        time.sleep(3)

    return set_logon_id(driver, logon_id)


def wait_element_loaded(driver, delay, element_id):
    try:
        elem_founded = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, element_id)))
        return True
    except TimeoutException:
        LOGGER.warn("等待页面加载元素%s在%s秒内超时", element_id, delay)
        return False


def set_logon_id(driver, logon_id):
    """
    向登录框填入登录账户，并返回当前页面的session

    :param driver:
    :param logon_id:
    :return:
    """
    # 用户名输入框
    ele_user_id = None
    try:
        # ele_user_id = driver.find_element_by_id(LOGON_ID_INPUT)
        # ele_user_id.clear()
        # driver.find_element_by_id("storeUserid").send_keys(user)
        driver.execute_script('document.getElementById("' + _get_input_id() + '").value = "' + logon_id + '"')
    except Exception as ex:
        LOGGER.exception("填充登录名%s. Exception:%s", logon_id, ex)

    # [{u'value': u'0000daj0cacDkAIEeAaGHCyf_bM:-1', u'name': u'JSESSIONID', u'httpOnly': True, u'secure': False}]
    cookies = driver.get_cookies()
    session_id = ''
    for cookie in cookies:
        if cookie.get('name') == 'JSESSIONID':
            session_id = cookie.get('value')
    # return session_id
    # For test
    return "aaabbbcccddd"


def re_login(session_id):
    """
    复用有效的session重新打开页面
    :param session_id:
    :return:
    """
    if not session_id:
        return None
    # 选择IE 还是 Chrome打开
    # driver = webdriver.Ie()
    driver = webdriver.Chrome()
    driver.implicitly_wait(2)
    gevent.sleep(0)
    DRIVERS.append(driver)
    driver.get(_get_login_url())
    # 把有效的sessionId更新到cookie里，覆盖新开页面的cookie值
    # [{u'value': u'0000daj0cacDkAIEeAaGHCyf_bM:-1', u'name': u'JSESSIONID', u'httpOnly': True, u'secure': False}]
    cookie = {'value': session_id, 'name': 'JSESSIONID'}
    driver.add_cookie(cookie)
    driver.refresh()


def close_all():
    """
    关闭所有selinum打开的页面
    :return:
    """
    global DRIVERS
    count = 0
    for driver in DRIVERS:
        try:
            if driver:
                driver.close()
                count += 1
        except Exception:
            pass
    DRIVERS = []
    return count


def batch_fresh_login():
    """
    批量登录，只选取session无效的，每次5个
    :return:  打开登录商户logonId
    """
    jobs = []
    alias = []

    login_count = 5
    try:
        login_count = utils.get_merchant_login_cfg('batch_login_count')
    except Exception:
        pass

    for key in MERCHANTS_DATA:
        merchant = MERCHANTS_DATA.get(key)
        if isinstance(merchant, MerchantInfo) and not merchant.status:
            # fresh_login(merchant.logon_id)
            jobs.append(gevent.spawn(batch_fresh_login_helper, merchant))
            if merchant.alias:
                alias.append(merchant.alias)
            else:
                alias.append(merchant.store_name)
            if len(jobs) >= login_count:
                break
    gevent.joinall(jobs)
    return alias


def batch_fresh_login_helper(merchant):
    fresh_session_id = fresh_login(merchant.logon_id)
    if fresh_session_id:
        merchant.session_id = fresh_session_id


def _get_input_id():
    return _get_merchant_login_cfg('logon_id_input', 'storeUserid')


def _get_login_url():
    return _get_merchant_login_cfg('login_url', 'https://biz.elife.icbc.com.cn/businessHomeLogin/loginPage.action')


def _get_merchant_login_cfg(key, default=None):
    res = default
    try:
        res = utils.get_merchant_login_cfg(key)
    except Exception:
        pass
    return res
