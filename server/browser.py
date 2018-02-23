# coding:utf-8

"""
利用selenium来操作浏览器

Author: karl(i@karlzhou.com)
"""
from selenium import webdriver

import order
from log4cas import LOGGER
from model import MerchantInfo

# LOGIN_URL = "https://biz.elife.icbc.com.cn/businessHomeLogin/loginPage.action')"
LOGIN_URL = "http://localhost:8887/order"
# LOGON_ID_INPUT = "storeUserid"
# For Test
LOGON_ID_INPUT = "sessionId"

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
    DRIVERS.append(driver)
    driver.get(LOGIN_URL)
    # 用户名输入框
    ele_user_id = None
    try:
        ele_user_id = driver.find_element_by_id(LOGON_ID_INPUT)
        ele_user_id.clear()
        # driver.find_element_by_id("storeUserid").send_keys(user)
        driver.execute_script('document.getElementById("' + LOGON_ID_INPUT + '").value = ' + logon_id)
    except Exception as ex:
        LOGGER.warn("在页面" + LOGIN_URL + "上未找到元素#" + LOGON_ID_INPUT)

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
        # driver = webdriver.Ie()
    driver = webdriver.Chrome()
    DRIVERS.append(driver)
    driver.get(LOGIN_URL)
    # 把有效的sessionId更新到cookie里，覆盖新开页面的cookie值
    # [{u'value': u'0000daj0cacDkAIEeAaGHCyf_bM:-1', u'name': u'JSESSIONID', u'httpOnly': True, u'secure': False}]
    cookie = {'value': session_id, 'name': 'JSESSIONID'}
    driver.add_cookie(cookie)
    # 是否需要sleep,待定
    driver.refresh()


def close_all():
    """
    关闭所有selinum打开的页面
    :return:
    """
    global DRIVERS
    for driver in DRIVERS:
        try:
            if driver:
                driver.close()
        except Exception:
            pass
    DRIVERS = []
