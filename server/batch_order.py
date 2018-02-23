# coding:utf-8

"""
ICBC批量订单下载

Author: karl(i@karlzhou.com)
"""
from model import MerchantInfo
from utils import read_merchant_cfg

# 商户缓存数据，以登录账户为key
MERCHANTS_DATA = dict()


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
    # FIXME: gevent并发检查session有效性
    for cfg in cfgs:
        if isinstance(cfg, MerchantInfo):
            pass
    pass


if __name__ == '__main__':
    get_merchant_config()
