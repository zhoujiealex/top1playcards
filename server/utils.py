# coding:utf-8

import ConfigParser
import codecs
import json
import os
from datetime import datetime, date, timedelta

from log4cas import LOGGER


def read_cfg(section, key, cfg_file_name):
    """
    读取指定文件里的指定key的值
    :param section:
    :param key:
    :param cfg_file_name:
    :return:
    """
    conf = ConfigParser.ConfigParser()
    cfg_file = os.path.join(os.path.dirname(__file__), '../', 'conf', cfg_file_name)
    if not os.path.exists(cfg_file):
        raise Exception(u"配置文件不存在，请检查,cfg_file=%s" % cfg_file)
    conf.read(cfg_file)
    return conf.get(section, key)


def read_excel_cfg(key):
    return read_cfg("excel", key, "config.ini")


def read_merchant_cfg():
    """
    读取商户json配置，返回dict
    :return: `dict`
    """
    cfg_file = get_merchant_cfg_file()
    if not os.path.exists(cfg_file):
        raise Exception(u"商户配置json文件不存在，请检查,cfg_file=%s" % cfg_file)
    res = None
    with open(cfg_file, 'r') as data:
        try:
            content = data.read()
            if content.startswith(codecs.BOM_UTF8):
                content = content.decode('utf-8-sig')
            res = json.loads(content)
        except Exception as ex:
            LOGGER.exception(u"商户配置json文件格式不合法，请检查%s", ex)
            raise Exception(u"商户配置json文件格式不合法，请检查")
    return res


def get_merchant_cfg_file():
    cfg_file = os.path.join(os.path.dirname(__file__), '../', 'conf', 'merchants.json')
    return cfg_file


def get_merchant_login_cfg(key):
    return read_cfg("merchant_login", key, "config.ini")


def get_specific_merchant_ids():
    """
    获取指定要登录的商户ids
    :return:
    """
    logon_ids = read_cfg("merchant_ids", "specific_ids", "config.ini")
    return [id.strip() for id in logon_ids.split("|")]


def get_refresh_threshold():
    """
    前台是否要加载的阈值，默认30%
    :return:
    """
    return int(get_merchant_login_cfg("force_refresh_threshold"))


def convert_str_to_bool(bool_str):
    """
    把前台的json的布尔值转换为python的bool
    :return:
    """
    return bool_str == "true"


def get_now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_now_date_str():
    """
    获取当天时间
    :return:
    """
    return date.today().strftime("%Y-%m-%d")


def get_yesterday_date_str():
    """
    获取昨天的日期
    :return:
    """
    yesterday = date.today() + timedelta(days=-1)
    return yesterday.strftime("%Y-%m-%d")
