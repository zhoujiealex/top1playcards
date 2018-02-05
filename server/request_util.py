# coding:utf-8


"""
用于ICBC网站登陆，cookie较简单，只有一个
   JSESSIONID: 0000Nv7i0SwGja0eQ2UkCr1Ap_X:-1
   
"""
import requests
from log4cas import LOGGER

# https://biz.elife.icbc.com.cn/businessHomeLogin/receiveCommon.action

ICBC_HOST = "https://biz.elife.icbc.com.cn/"


def get_session(session_id):
    """
    返回一个request的session
    :param session_id:
    :return:
    """
    s = requests.Session()
    s.headers.update({'JSESSIONID': session_id})
    return s


def get_url(session, url):
    return requests.get(__build_url(url))


def post_url(session, url):
    return requests.post(__build_url())

def __build_url(url):
    return ICBC_HOST + url

