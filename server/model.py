# coding:utf-8

"""
ICBC模型

Author: karl(i@karlzhou.com)
"""

import datetime

from log4cas import LOGGER


class NoDataException(Exception):
    """
    无数据-业务异常，不中断处理
    """
    pass


class MerchantInfo(object):

    def __init__(self):
        # 商家门店id, 需要解析html获取，前台不感知
        self._shop_id = None
        # 商户门店名称
        self._store_name = None
        # mcc
        self._mcc = None
        # alias别名
        self._alias = None
        # 登录账户
        self._logon_id = None
        # session
        self._session_id = None
        # status 状态, 不直接设置，登录成功后更新为True
        self._status = False
        # errors
        self._errors = list()

    def to_dict(self):
        res = dict()
        res['alias'] = self.alias
        res['logonId'] = self.logon_id
        res['mcc'] = self.mcc
        res['storeName'] = self.store_name
        res['sessionId'] = self.session_id
        res['shopId'] = self.shop_id
        res['status'] = self.status
        return res

    @property
    def shop_id(self):
        return self._shop_id

    @shop_id.setter
    def shop_id(self, shop_id):
        self._shop_id = shop_id

    @property
    def store_name(self):
        return self._store_name

    @store_name.setter
    def store_name(self, store_name):
        self._store_name = store_name

    @property
    def mcc(self):
        return self._mcc

    @mcc.setter
    def mcc(self, mcc):
        self._mcc = mcc

    @property
    def alias(self):
        return self._alias

    @alias.setter
    def alias(self, alias):
        self._alias = alias

    @property
    def logon_id(self):
        return self._logon_id

    @logon_id.setter
    def logon_id(self, logon_id):
        self._logon_id = logon_id

    @property
    def session_id(self):
        return self._session_id

    @session_id.setter
    def session_id(self, session_id):
        self._session_id = session_id

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status

    @property
    def errors(self):
        return self._errors

    @errors.setter
    def errors(self, errors):
        self._errors.append(errors)

    def __unicode__(self):
        return u'alias=[%s] logonId=[%s] mcc=[%s] storeName=[%s] sessionId=[%s] shopId=[%s] status=[%s]' % (
            self.alias, self.logon_id, self.mcc, self.store_name, self.session_id, self.shop_id, self.status)

    def __str__(self):
        # it seems there's something wrong when name isn't ascii character.
        return unicode(self).encode('utf-8')


class TradeSummary(object):
    def __init__(self):
        # 交易日期
        self._order_date = None
        # 门店id
        self._shop_id = ''
        # 门店名称
        self._store_name = ''
        # 总订单金额
        self._total_amount = 0
        # 总消费立减金额
        self._total_dis_amt = 0
        # 总电子券抵扣金额
        self._total_ecoupon_amt = 0
        # FIXME: 总净收金额, 页面上未用到，实际数据比total_amount少几元，待确定
        self._total_money = 0
        # 总积分抵扣金额
        self._total_point_amt = 0

    def to_dict(self):
        res = dict()
        res['orderDate'] = self._order_date
        res['shopId'] = self._shop_id
        res['storeName'] = self._store_name
        res['totalAmount'] = self._total_amount
        res['totalDisAmt'] = self._total_dis_amt
        res['totalEcouponAmt'] = self._total_ecoupon_amt
        res['totalMoney'] = self._total_money
        res['totalPointAmt'] = self._total_point_amt
        return res

    def __unicode__(self):
        return u'order_date=[%s] shop_id=[%s] store_name=[%s] total_amount=[%s]' % (
            self._order_date, self._shop_id, self._store_name, self._total_amount)

    def __str__(self):
        # it seems there's something wrong when name isn't ascii character.
        return unicode(self).encode('utf-8')

    @property
    def order_date(self):
        return self._order_date

    @order_date.setter
    def order_date(self, order_date):
        # 只取日期yyyy-mm-dd
        self._order_date = format_date(order_date, "%Y-%m-%d")

    @property
    def shop_id(self):
        return self._shop_id

    @shop_id.setter
    def shop_id(self, shop_id):
        self._shop_id = shop_id

    @property
    def store_name(self):
        return self._store_name

    @store_name.setter
    def store_name(self, store_name):
        self._store_name = store_name

    @property
    def total_amount(self):
        return self._total_amount

    @total_amount.setter
    def total_amount(self, total_amount):
        self._total_amount = convert_cent_to_yuan(total_amount)

    @property
    def total_dis_amt(self):
        return self._total_dis_amt

    @total_dis_amt.setter
    def total_dis_amt(self, total_dis_amt):
        self._total_dis_amt = convert_cent_to_yuan(total_dis_amt)

    @property
    def total_ecoupon_amt(self):
        return self._total_ecoupon_amt

    @total_ecoupon_amt.setter
    def total_ecoupon_amt(self, total_ecoupon_amt):
        self._total_ecoupon_amt = convert_cent_to_yuan(total_ecoupon_amt)

    @property
    def total_money(self):
        return self._total_money

    @total_money.setter
    def total_money(self, total_money):
        self._total_money = convert_cent_to_yuan(total_money)

    @property
    def total_point_amt(self):
        return self._total_point_amt

    @total_point_amt.setter
    def total_point_amt(self, total_point_amt):
        self._total_point_amt = convert_cent_to_yuan(total_point_amt)


class TradeDetail(object):
    """
    交易详情, 暂时只定义了excel中显示的字段
    金额以分为单位，需要进行转换成元，保留小数点2位，并落地为str
    交易日期只记录date，不记录时间time，转换为yyyy-mm-dd
    交易时间只记录time，不记录日期，转换为hh:mm:ss
    """

    def __init__(self):
        # 1.门店名称
        self._store_name = None
        # 2.交易日期
        self._order_date = None
        # 3.交易时间
        self._order_time = None
        # 用于页面显示的时间，不需要拆成两列
        self._order_time_full = None
        # 4.订单号
        self._order_id = None
        # 5.交易卡号
        self._card_no = None
        # 6.原交易金额
        self._order_amt = None
        # 7.消费立减金额
        self._dis_amt = None
        # 8.净收金额(含积分及电子券抵扣金额)
        self._total_amount = None
        # 9.积分抵扣金额
        self._point_amt = None
        # 10.电子券抵扣金额
        self._ecoupon_amt = None
        # 11.交易类型, 写死，code: 0
        self._tran_type = u"消费"
        # 12.交易方式
        self._tran_way = None

    def to_dict(self):
        res = dict()
        res['storeName'] = self._store_name
        res['orderDate'] = self._order_date
        res['orderTime'] = self._order_time
        res['orderTimeFull'] = self._order_time_full
        res['orderId'] = self._order_id
        res['cardNo'] = self._card_no
        res['orderAmt'] = self._order_amt
        res['disAmt'] = self._dis_amt
        res['totalAmount'] = self._total_amount
        res['pointAmt'] = self._point_amt
        res['ecouponAmt'] = self._ecoupon_amt
        res['tranType'] = self._tran_type
        res['tranWay'] = self._tran_way
        return res

    @property
    def store_name(self):
        return self._store_name

    @store_name.setter
    def store_name(self, store_name):
        self._store_name = store_name

    @property
    def order_date(self):
        return self._order_date

    @order_date.setter
    def order_date(self, order_date):
        # 只取日期yyyy-mm-dd
        self._order_date = format_date(order_date, "%Y-%m-%d")

    @property
    def order_time(self):
        return self._order_time

    @order_time.setter
    def order_time(self, order_time):
        # 只取时间hh:mm:ss
        self._order_time = format_date(order_time, "%H:%M:%S")

    @property
    def order_time_full(self):
        return self._order_time_full

    @order_time_full.setter
    def order_time_full(self, order_time):
        # 只取时间hh:mm:ss
        self._order_time_full = format_date(order_time, "%Y-%m-%d %H:%M:%S")

    @property
    def order_id(self):
        return self._order_id

    @order_id.setter
    def order_id(self, order_id):
        self._order_id = order_id

    @property
    def card_no(self):
        return self._card_no

    @card_no.setter
    def card_no(self, card_no):
        self._card_no = card_no

    @property
    def order_amt(self):
        return self._order_amt

    @order_amt.setter
    def order_amt(self, order_amt):
        self._order_amt = convert_cent_to_yuan(order_amt)

    @property
    def dis_amt(self):
        return self._dis_amt

    @dis_amt.setter
    def dis_amt(self, dis_amt):
        self._dis_amt = convert_cent_to_yuan(dis_amt)

    @property
    def total_amount(self):
        return self._total_amount

    @total_amount.setter
    def total_amount(self, total_amount):
        self._total_amount = convert_cent_to_yuan(total_amount)

    @property
    def point_amt(self):
        return self._point_amt

    @point_amt.setter
    def point_amt(self, point_amt):
        self._point_amt = convert_cent_to_yuan(point_amt)

    @property
    def ecoupon_amt(self):
        return self._ecoupon_amt

    @ecoupon_amt.setter
    def ecoupon_amt(self, ecoupon_amt):
        self._ecoupon_amt = convert_cent_to_yuan(ecoupon_amt)

    @property
    def tran_type(self):
        return self._tran_type

    @tran_type.setter
    def tran_type(self, tran_type):
        if tran_type == '0':
            self._tran_type = u"消费"
        else:
            self._tran_type = str(tran_type)

    @property
    def tran_way(self):
        return self._tran_way

    @tran_way.setter
    def tran_way(self, tran_way):
        self._tran_way = tran_way


def convert_cent_to_yuan(cent):
    if not isinstance(cent, str):
        return format(float(cent) / 100.0, '.2f')
    else:
        return cent


def format_date(timestamp, format_str):
    try:
        date_obj = datetime.datetime.fromtimestamp(timestamp / 1e3)
        return datetime.datetime.strftime(date_obj, unicode(format_str))
    except Exception as ex:
        # ignore
        LOGGER.error(u"日期转换出错，输入timestamp=%s, Exception:%s", timestamp, ex)
        return unicode(timestamp)
