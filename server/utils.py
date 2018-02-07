# coding:utf-8

import ConfigParser
import os


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
