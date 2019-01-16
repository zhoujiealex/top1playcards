# -*- coding: utf-8 -*-
from __future__ import print_function

import datetime
import os
import random
import string
import sys
import time

import gevent
import requests
from gevent import monkey
from gevent.pool import Pool

reload(sys)
sys.setdefaultencoding('utf-8')

monkey.patch_all()

CONTRACT_STATUS_UNKNOWN = -1
CONTRACT_STATUS_OK = 0
CONTRACT_STATUS_NOT_EXISTED = 1
CONTRACT_STATUS_FINISHED = 2
CONTRACT_STATUS_INVALID = 3

POOL_SIZE = 100
SLEEP_TIME = 0.1

CHECK_CONTRACT_POOL = Pool(POOL_SIZE)


def check_contract(contract_no):
    """
    校验合同
    :param contract_no: 合同编号

    :return:
        -1: 未遇到过的情况，不确定
        0: ok
        1: 标的不存在
        2: 无法查看已取消借款或已完结的标的
    """
    contract_no_str = contract_no.strip()
    if len(contract_no_str) <= 0:
        return CONTRACT_STATUS_INVALID

    url = "http://www.yidai.com/invest/a" + contract_no_str + ".html"
    # url = "http://www.baidu.com/"

    headers = {
        'Host': 'www.yidai.com',
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; Tablet PC 2.0)',
        '6ePf_d8cc_colseBrowser': generate_random_str(40),
        'sec': generate_random_str(40),
        'sec_tc': generate_random_str(32),
        '6ePf_d8cc_p2pfront': generate_random_str(40)
    }
    res = requests.get(url, headers=headers)
    res_code = CONTRACT_STATUS_UNKNOWN
    if res.ok and res.status_code == 200:
        if u'标的不存在' in res.text:
            res_code = CONTRACT_STATUS_NOT_EXISTED
        elif u'借款金额' in res.text and u'借贷双方约定利率' in res.text:
            res_code = CONTRACT_STATUS_OK

    if not res.ok or res.status_code != 200:
        if u'无法查看已取消借款或已完结的标的' in res.text:
            res_code = CONTRACT_STATUS_FINISHED
    return res_code


def check_contract_bak2(contract_no):
    print(contract_no)
    res = requests.get("http://www.baidu.com")
    print_time()
    print(unicode(res.text))


def get_save_file_path(file_prefix, res_code):
    """
    获取保存文件结果，默认是前缀+几种结果分类+当天日期时间
    :param file_prefix:
    :param res_code: 处理识别结果
    :return:
    """
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    file_name = date_str + file_prefix.strip()
    res_str = ""
    if res_code == CONTRACT_STATUS_UNKNOWN:
        res_str = "UNKNOWN"
    elif res_code == CONTRACT_STATUS_FINISHED:
        res_str = u"疑似完结"
    elif res_code == CONTRACT_STATUS_NOT_EXISTED:
        res_str = u"不存在"
    elif res_code == CONTRACT_STATUS_OK:
        res_str = u"有效"
    elif res_code == CONTRACT_STATUS_INVALID:
        res_str = u"非法无效"
    file_name += "[" + res_str + "]"
    file_full_path = os.path.realpath(os.path.join(os.path.dirname(__file__), './dstFile', file_name.strip()))
    return file_full_path


def process_contracts(file_name):
    """
    读取当前文件夹下的文件.
    分类标号合同到特定文件下
    :param file_name:
    :return:
    """
    file_full_path = os.path.realpath(os.path.join(os.path.dirname(__file__), './srcFile', file_name.strip()))
    print(file_full_path)
    time_start = time.time()

    check_res = {CONTRACT_STATUS_OK: [], CONTRACT_STATUS_NOT_EXISTED: [],
                 CONTRACT_STATUS_FINISHED: [], CONTRACT_STATUS_UNKNOWN: [], CONTRACT_STATUS_INVALID: []}

    with open(file_full_path) as f:
        i = 0
        for contract_no in f.readlines():
            i += 1
            if i % 20 == 1:
                time.sleep(SLEEP_TIME * 20)

            print(get_now_time_str() + u"开始处理第" + str(i) + u"个数据：")
            contract_no = contract_no.strip()
            try:
                res = check_contract(contract_no)
                check_res[res].append(contract_no)
                gevent.sleep(SLEEP_TIME)
                print(u"第" + str(i) + u"个数据：no=" + contract_no + u",resCode=" + str(res))
            except Exception as ex:
                print(u"处理出现异常，no=" + contract_no + ",num=" + str(i) + ex.message)
                check_res[CONTRACT_STATUS_INVALID].append(contract_no)

    time_end = time.time()
    print('totally cost', time_end - time_start)
    if not check_res or not file_name:
        return
    for key in check_res:
        save_single_file(key, file_name, check_res.get(key, []), time_start, time_end)


def save_single_file(res_code, file_name, check_res_data, start, end):
    if not check_res_data or len(check_res_data) <= 0:
        return
    save_res_file = get_save_file_path(file_name, res_code)
    with open(save_res_file, 'a') as f:
        f.write("                                \n")
        f.write("                                \n")
        f.write(get_now_time_str() + "开始刷新保存文件， 共" + str(len(check_res_data)) + "条数据\n")
        f.write("start=" + str(start) + ",end=" + str(end) + ",totally cost=" + str(end - start))
        f.write("==================================\n")
        for data in check_res_data:
            f.write(str(data) + "\n")
        f.write("***********************************\n")


def get_now_time_str():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')


def generate_random_str(length=16):
    """
    生成一个指定长度的随机字符串，其中
    string.digits=0123456789
    string.ascii_letters=abcdefghigklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ
    """
    str_list = [random.choice(string.digits + string.ascii_letters) for i in range(length)]
    random_str = ''.join(str_list)
    return random_str


if __name__ == '__main__':
    # process_contracts("sample.txt")
    process_contracts("供链贷103.txt")
    process_contracts("车贷3682.txt")
    process_contracts("房贷13506.txt")
    # save_single_file(1, "testFang", ["1", "2", "3", "4", "5"])
