# coding:utf-8

"""
转换TradeDetail列表，并保存为excel
维持了和ICBC网站下载格式完全一样
但实际json数据有更多内容，如有需要可自行增加

注：保存文件名称：<门店名><日期>.xls

Author: karl(i@karlzhou.com)
"""
import os
import sys

import xlrd
import xlwt
from xlutils.copy import copy as xl_copy

from model import *
from utils import read_excel_cfg

reload(sys)
sys.setdefaultencoding('utf-8')

###############################################################################
# Fix Python 3.5, there's no unicode function in python3
# http://stackoverflow.com/questions/6812031/how-to-make-unicode-string-with-python3
try:
    UNICODE_EXISTS = bool(type(unicode))
except NameError:
    unicode = lambda s: str(s)

###############################################################################
# 配置
# excel 列名映射
COLUMN_MAPS = {
    "store_name": u"门店名称",
    "order_date": u"交易日期",
    "order_time": u"交易时间",
    "order_id": u"订单号",
    "card_no": u"交易卡号",
    "order_amt": u"原交易金额",
    'dis_amt': u"消费立减金额",
    "total_amount": u"净收金额(含积分及电子券抵扣金额)",
    "point_amt": u"积分抵扣金额",
    "ecoupon_amt": u"电子券抵扣金额",
    "tran_type": u"交易类型",
    "tran_way": u"交易方式"
}

# excel 列顺序
COLUMN_KEYS = [
    'store_name',
    'order_date',
    'order_time',
    'order_id',
    'card_no',
    'order_amt',
    'dis_amt',
    'total_amount',
    'point_amt',
    'ecoupon_amt',
    'tran_type',
    'tran_way'
]

# excel 列宽带设置

BASE_CHAR_WIDTH = 400
COLUMN_KEYS_WIDTH = {
    "store_name": 18 * BASE_CHAR_WIDTH,
    "order_date": 7 * BASE_CHAR_WIDTH,
    "order_time": 6 * BASE_CHAR_WIDTH,
    "order_id": 16 * BASE_CHAR_WIDTH,
    "card_no": 10 * BASE_CHAR_WIDTH,
    "order_amt": 6 * BASE_CHAR_WIDTH,
    'dis_amt': 6 * BASE_CHAR_WIDTH,
    "total_amount": 6 * BASE_CHAR_WIDTH,
    "point_amt": 6 * BASE_CHAR_WIDTH,
    "ecoupon_amt": 6 * BASE_CHAR_WIDTH,
    "tran_type": 5 * BASE_CHAR_WIDTH,
    "tran_way": 12 * BASE_CHAR_WIDTH
}


###############################################################################


###############################################################################
# 业务逻辑 -- 保存订单信息未本地文件
def save_order_data_to_excel(date, merchant_trade_summary, order_detail_datas, save_path=None):
    """
     保存信息到本地excel
     修改生成邮件的方式，同一日期的保存在一起，每个sheet一个商户，需要查看是否已有xls文件
     有则打开，根据门店名称找到对应sheet文件，更新 or 新建。

     :param date
     :param merchant_trade_summary: `TradeSummary`
     :param order_detail_datas: `TradeDetail`
     :param save_path: 保存文件路径
     :return:
     """
    if not merchant_trade_summary or not order_detail_datas:
        return None

    excel_file_name = get_excel_name(date)
    sheet_name = get_sheet_name(merchant_trade_summary)
    if not save_path:
        save_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '../', 'excels'))
    if not os.path.exists(save_path):
        os.mkdir(save_path)

    # 获取excel全路径
    file_full_path = os.path.join(save_path, excel_file_name)
    wb = get_workbook(file_full_path)

    ws_info = None
    try:
        ws_index = wb.sheet_index(sheet_name)
        ws_info = wb.get_sheet(ws_index)
    except Exception:
        # 不存在，则新建
        wb_info = init_workbook(sheet_name, parent_wb=wb, frozen=False)
        ws_info = wb_info['sheets'].get(sheet_name)
    write_sheet(ws_info, order_detail_datas)
    save_excel(wb, excel_file_name, save_path)
    return file_full_path


def save_order_data_to_excel_bak(merchant_trade_summary, order_detail_datas, save_path=None):
    """
    保存信息到本地excel

    :param merchant_trade_summary: `TradeSummary`
    :param order_detail_datas: `TradeDetail`
    :param save_path: 保存文件路径
    :return:
    """
    if not merchant_trade_summary or not order_detail_datas:
        return None

    file_name = get_file_name(merchant_trade_summary)

    sheet_name = u"e生活商户交易明细"
    wb = get_workbook(None)
    wb_info = init_workbook(sheet_name, parent_wb=wb, frozen=False)
    ws_info = wb_info['sheets'].get(sheet_name)

    write_sheet(ws_info, order_detail_datas)

    if not save_path:
        save_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '../', 'excels'))
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    save_excel(wb, file_name, save_path)


def write_sheet(ws, order_detail_datas, rowx=1, column_keys=COLUMN_KEYS):
    """
    :param ws: `xlwt.Worksheet` or `FitSheetWrapper
    :param order_detail_datas: `list`
    :param rowx: `int` excel起始行
    :param column_keys: `list`
    :return: None
    """
    if not isinstance(ws, xlwt.Worksheet) and \
            not isinstance(ws, FitSheetWrapper):
        LOGGER.warning("Invalid worksheet %s, nothing to do!", type(ws))
        return None

    for order_detail_data in order_detail_datas:
        add_row(ws, order_detail_data, rowx, column_keys=column_keys)
        rowx += 1


def get_excel_name(date):
    """
      保存文件名称：<日期>.xls， 如: 2018-02-06.xls
      :param date
      :return:
      """
    now = datetime.datetime.now()
    post_fix = '.xls'
    if not date:
        return now.strftime("%Y-%m-%d_%H-%M-%S") + post_fix
    else:
        file_name = "商户交易订单"
        try:
            file_name = read_excel_cfg("file_name")
        except Exception:
            pass
        return file_name + date + post_fix


def get_sheet_name(merchant_trade_summary):
    """
    保存文件名称：<门店名>
    :param merchant_trade_summary: `TradeSummary`
    :return:
    """
    if isinstance(merchant_trade_summary, TradeSummary):
        return unicode(merchant_trade_summary.store_name)
    else:
        # sheetname不能重复，加上时间
        now = datetime.datetime.now()
        return "e生活商户交易明细" + now.strftime("%Y-%m-%d_%H-%M-%S")


def get_file_name(merchant_trade_summary):
    """
    保存文件名称：<门店名><日期>.xls
    :param merchant_trade_summary: `TradeSummary`
    :return:
    """
    now = datetime.datetime.now()
    post_fix = '.xls'
    if isinstance(merchant_trade_summary, TradeSummary):
        return unicode(merchant_trade_summary.store_name + merchant_trade_summary.order_date + post_fix)
    else:
        return now.strftime("%Y-%m-%d_%H-%M-%S") + post_fix


def merge_excel_helper(date):
    excel_saved_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '../', 'excels'))
    src = os.path.normpath(os.path.join(excel_saved_path, read_excel_cfg("file_name") + date + ".xls"))
    dst = os.path.normpath(os.path.join(excel_saved_path, read_excel_cfg("file_name") + date + "-合并.xls"))
    return merge_excel(src, dst, read_excel_cfg("merged_sheet_name"))


def merge_excel(src, dst, merged_sheet_name):
    """
    合并src中所有sheet到同一个sheet里，要求表头一样，默认表头是一行。
    合并多个sheet到同一个excel里， 原文参考： https://gist.github.com/anderser/1276531
    做了部分定制，去掉了第一列的sheet名称

    :param src: 源文件
    :param dst: 目标保存文件
    :param merged_sheet_name: 合并后的sheet名称
    :return: `dict`: 统计信息，共多少商户，分别多少数据，总共多少数据
    """
    res = dict()
    res['error'] = ''
    if not os.path.exists(src):
        error = u"源文件不存在,请先下载商户订单后再合并。 请检查:[%s]" % src
        res['error'] = error
        LOGGER.error(error)
        return res

    try:
        book = xlrd.open_workbook(src, formatting_info=True)
    except Exception as ex:
        error = u"打开excel文件失败:[%s]. Exception:%s " % (src, ex)
        LOGGER.exception(error, ex)
        res['error'] = error
        return res

    res['src'] = src
    res['dst'] = dst
    res['detail'] = dict()
    res['total_count'] = 0

    merged_book = xlwt.Workbook()
    ws = merged_book.add_sheet(unicode(merged_sheet_name), cell_overwrite_ok=True)
    # 添加固定表头
    add_header(ws, COLUMN_KEYS, column_maps=COLUMN_MAPS, frozen=False)

    rowcount = 1
    datestyle = xlwt.XFStyle()
    datestyle.num_format_str = "YYYY-MM-DD"  # 暂时用不到date格式，保留
    for sheetx in range(book.nsheets):
        sheet = book.sheet_by_index(sheetx)
        if sheet:
            res['detail'][sheet.name] = sheet.nrows - 1  # 去掉表头
            res['total_count'] += sheet.nrows - 1
        for rx in range(sheet.nrows):
            if rx > 0:  # 排除第一行表头
                for cx in range(sheet.ncols):
                    value = sheet.cell_value(rx, cx)

                    # datetime check lifted from the great Everyblock ebdata excel.py code
                    # http://code.google.com/p/ebcode/

                    if sheet.cell_type(rx, cx) == 3:
                        try:
                            value = datetime.datetime(*xlrd.xldate_as_tuple(value, book.datemode))

                            ws.write(rowcount, cx, sheet.cell_value(rx, cx), datestyle)
                        except ValueError:
                            # The datetime module raises ValueError for invalid
                            # dates, like the year 0. Rather than skipping the
                            # value (which would lose data), we just keep it as
                            # a string.
                            pass
                    else:
                        ws.write(rowcount, cx, sheet.cell_value(rx, cx))

                rowcount += 1
    try:
        os.remove(dst)
    except Exception:
        # 尝试删除旧文件，失败也会覆盖
        # 有一种情况：新数据比老数据少，则会出现新老混合
        pass

    try:
        merged_book.save(dst)
    except Exception as ex:
        error = u"保存excel[%s]文件失败" % dst
        LOGGER.exception("%s,Exception:%s", error, ex)
        res['error'] = error
    return res


############ 公共函数 #########################################################
# Excel style mapping
# https://github.com/python-excel/xlwt/blob/master/examples/num_formats.py

num_format_str = "%s"
BODY_XF = xlwt.easyxf('font: name SimSun;', num_format_str=num_format_str)
WARNING_XF = xlwt.easyxf(
    'font: bold off; align: wrap on, vert center, horiz left; pattern: pattern solid, fore-colour yellow')
DANGER_XF = xlwt.easyxf(
    'font: bold off; align: wrap on, vert center, horiz left; pattern: pattern solid, fore-colour red')
# HEADING_XF = BODY_XF
HEADING_XF = xlwt.easyxf('font: name SimSun, bold on;')

STYLE_MAPS = {
    "info": BODY_XF,
    "default": BODY_XF,
    "warning": BODY_XF,
    "danger": BODY_XF
}

# Threshold阈值,显示不同颜色
DEBUG = 'debug'
INFO = 'info'
WARNING = 'warning'
DANGER = 'danger'


def get_workbook(file_path):
    """为了向同一个wb对象里添加sheet，
    另一种做法更tricky：打开生成的host_info_xxxx.xls, xlutil.copy 一份，然后往里加入新的sheet
    http://stackoverflow.com/questions/38081658/adding-a-sheet-to-an-existing-excel-worksheet-without-deleting-other-sheet
    这里为了简单，但是会耦合严重。
    """
    if not os.path.exists(file_path):
        # 路径不存在，重新创建一个
        return xlwt.Workbook(encoding="utf-8")
    else:
        try:
            rb = xlrd.open_workbook(file_path, formatting_info=True)
            return xl_copy(rb)
        except Exception as ex:
            # 如果读取失败需要记录
            LOGGER.exception("打开excel文件[%s]失败,尝试重新创建全新的. Exception: %s", file_path, ex)
            # raise ex


# 生成excel内容
def init_workbook(sheets, parent_wb=None, cell_overwrite=True,
                  column_maps=COLUMN_MAPS,
                  column_keys=COLUMN_KEYS, frozen=True, frozen_horz=1,
                  frozen_vert=2):
    """初始化Workbook，创建对应sheets

    :param sheets: `list`
    :param parent_wb: `xlwt.Workbook`
    :param cell_overwrite: `bool`, default True
    :param column_maps: `dict`
    :param column_keys: `list`
    :param frozen: `bool`，是否需要锁定
    :param frozen_horz: `int`, 需要锁定表头前多少行，相对于第一行rowx算
    :param frozen_vert: `int`, 需要锁定前多少列
    :return: `dict`
        {
            "wb": `xlwt.Workbook`,
            "sheets":{
                "aws": `xlwt.Worksheet` or `FitSheetWrapper`,
                "qcloud": `xlwt.Worksheet` or `FitSheetWrapper`,
                "balabala": `xlwt.Worksheet` or `FitSheetWrapper`
            }
        }
    """
    if not isinstance(parent_wb, xlwt.Workbook):
        parent_wb = get_workbook()
    ws_temp = dict()
    if not isinstance(sheets, list):
        sheets = [sheets]
    for sheet in sheets:
        ws = parent_wb.add_sheet(unicode(sheet), cell_overwrite_ok=cell_overwrite)
        # 暂时不调整宽度
        # ws = FitSheetWrapper(ws)
        add_header(ws, column_keys, column_maps=column_maps,
                   frozen=frozen, frozen_horz=frozen_horz,
                   frozen_vert=frozen_vert)
        ws_temp[unicode(sheet)] = ws

    res = {'wb': parent_wb, 'sheets': ws_temp}
    return res


def add_header(ws, headers, rowx=0, column_maps=COLUMN_MAPS, style=HEADING_XF,
               frozen=True, frozen_horz=1, frozen_vert=2):
    """添加表格头

    :param ws: `xlwt.Worksheet` or `FitSheetWrapper`
    :param headers: `list`, 存储列名的数组
    :param rowx: `int`, 左上角坐标，默认添加到第0行
    :param column_maps: `dict`, 列名映射
    :param style: `xlwt.Style.XFStyle`, 不设置则用默认style
    :param frozen: `bool`，是否需要锁定
    :param frozen_horz: `int`, 需要锁定表头前多少行，相对于第一行rowx算
    :param frozen_vert: `int`, 需要锁定前多少列
    :return: None
    :raises: ParseException
    """
    if not isinstance(headers, list):
        return None

    for idx, head in enumerate(headers):
        head_str = column_maps.get(head, unicode(head))
        ws.col(idx).width = COLUMN_KEYS_WIDTH.get(head, 10 * BASE_CHAR_WIDTH)
        ws.write(rowx, idx, head_str, style)

    if frozen:
        # frozen headings instead of split panes
        ws.set_panes_frozen(True)
        # in general, freeze after last heading row
        ws.set_horz_split_pos(rowx + frozen_horz)
        # first two column
        ws.set_vert_split_pos(frozen_vert)
        # if user does unfreeze, don't leave a split there
        ws.set_remove_splits(True)


def generate_excel(save_file):
    """生存excel文件
    cell_overwrite_ok默认为False, 覆盖时候出现：
        Exception: Attempt to overwrite cell: sheetname=u'test1' rowx=0 colx=0

    :param save_file: `str`, full path and file name
    :return: None
    """
    wb = xlwt.Workbook(encoding="utf-8")
    sheet1 = wb.add_sheet('test1', cell_overwrite_ok=True)
    sheet1.write(0, 0, "test 0-0")
    wb.save(save_file)

    wb = xlwt.Workbook(encoding="utf-8")
    ws_aws = wb.add_sheet('aws', cell_overwrite_ok=True)
    ws_aws.normal_magn = 100
    ws_aws = FitSheetWrapper(ws_aws)


def write_sheet(ws, host_infos, rowx=1, column_keys=COLUMN_KEYS):
    """A wrapper, save all host infos into related ws

    :param ws: `xlwt.Worksheet` or `FitSheetWrapper
    :param host_infos: `list`
    :param rowx: `int`
    :param column_keys: `list`
    :return: None
    """
    if not isinstance(ws, xlwt.Worksheet) and \
            not isinstance(ws, FitSheetWrapper):
        LOGGER.warning("Invalid worksheet %s, nothing to do!", type(ws))
        return None

    for host_info in host_infos:
        # TODO: 对应每个host info进行解析，判断是否需要设置报警style,可以在下层精确到cell
        add_row(ws, host_info, rowx, column_keys=column_keys)
        rowx += 1


def add_row(ws, order_detail_data, row, style=BODY_XF, column_keys=COLUMN_KEYS):
    """根据预处理过后的host信息，添加表格行，如果当前行处理出现错误，忽略

    :param ws: `xlwt.Worksheet` or `FitSheetWrapper`
    :param order_detail_data: `dict`, 函数wash_info返回的
    :param row: `int`
    :param style: `xlwt.Style.XFStyle`, 不设置则用默认style
    :param column_keys: `list`, 取出数组中对应key的值
        注：对于的列取值有两类：1.简单字符串 2.dict，取msg值
    :return: None
    """
    default_style = style
    for idx, key in enumerate(column_keys):
        val = getattr(order_detail_data, key)
        if val is not None:
            label = unicode(val)
            if isinstance(val, dict):
                label = val.get('msg', '')
                level = val.get('level', 'default')
                style = STYLE_MAPS.get(level, BODY_XF)

            ws.write(row, idx, label, style)
            style = default_style


def save_excel(wb, file_name, path):
    """保存excel表格

    :param wb: `xlwt.Workbook`
    :param file_name: `str`, 如果缺少后缀 'xls' 则加上'xls',
         xlwt只能支持到xls: compatible with MS Excel 97/2000/XP/2003 XLS files
    :param path: `str`, full path
    :return: None
    :raise: `ParseException`
    """
    if not isinstance(wb, xlwt.Workbook):
        raise Exception("Invalid type %s, expected xlwt.Workbook" % type(wb))

    file_extension = os.path.splitext(unicode(file_name))[1]
    if not len(file_extension):
        file_name += '.xls'
    try:
        wb.save(os.path.join(path, file_name))
        LOGGER.info("Excel %s saved!", file_name)
    except Exception as ex:
        LOGGER.exception("Save failed. Exception: %s", ex)
        raise ex


###############################################################################
# https://github.com/juanpex/django-model-report/blob/master/model_report/arial10.py
charwidths = {
    '0': 262.637,
    '1': 262.637,
    '2': 262.637,
    '3': 262.637,
    '4': 262.637,
    '5': 262.637,
    '6': 262.637,
    '7': 262.637,
    '8': 262.637,
    '9': 262.637,
    'a': 262.637,
    'b': 262.637,
    'c': 262.637,
    'd': 262.637,
    'e': 262.637,
    'f': 146.015,
    'g': 262.637,
    'h': 262.637,
    'i': 117.096,
    'j': 88.178,
    'k': 233.244,
    'l': 88.178,
    'm': 379.259,
    'n': 262.637,
    'o': 262.637,
    'p': 262.637,
    'q': 262.637,
    'r': 175.407,
    's': 233.244,
    't': 117.096,
    'u': 262.637,
    'v': 203.852,
    'w': 321.422,
    'x': 203.852,
    'y': 262.637,
    'z': 233.244,
    'A': 321.422,
    'B': 321.422,
    'C': 350.341,
    'D': 350.341,
    'E': 321.422,
    'F': 291.556,
    'G': 350.341,
    'H': 321.422,
    'I': 146.015,
    'J': 262.637,
    'K': 321.422,
    'L': 262.637,
    'M': 379.259,
    'N': 321.422,
    'O': 350.341,
    'P': 321.422,
    'Q': 350.341,
    'R': 321.422,
    'S': 321.422,
    'T': 262.637,
    'U': 321.422,
    'V': 321.422,
    'W': 496.356,
    'X': 321.422,
    'Y': 321.422,
    'Z': 262.637,
    ' ': 146.015,
    '!': 146.015,
    '"': 175.407,
    '#': 262.637,
    '$': 262.637,
    '%': 438.044,
    '&': 321.422,
    '\'': 88.178,
    '(': 175.407,
    ')': 175.407,
    '*': 203.852,
    '+': 291.556,
    ',': 146.015,
    '-': 175.407,
    '.': 146.015,
    '/': 146.015,
    ':': 146.015,
    ';': 146.015,
    '<': 291.556,
    '=': 291.556,
    '>': 291.556,
    '?': 262.637,
    '@': 496.356,
    '[': 146.015,
    '\\': 146.015,
    ']': 146.015,
    '^': 203.852,
    '_': 262.637,
    '`': 175.407,
    '{': 175.407,
    '|': 146.015,
    '}': 175.407,
    '~': 291.556}


def colwidth(n):
    '''Translate human-readable units to BIFF column width units'''
    if n <= 0:
        return 0
    if n <= 1:
        return n * 456
    return 200 + n * 256


def fitwidth(data, bold=False):
    '''Try to autofit Arial 10'''
    maxunits = 0
    # Fix by karl, when data is not string which has no split.
    m_data = unicode(data)
    for ndata in m_data.split("\n"):
        units = 220
        for char in ndata:
            if char in charwidths:
                units += charwidths[char]
            else:
                units += charwidths['0']
        if maxunits < units:
            maxunits = units
    if bold:
        maxunits *= 1.1
    return max(maxunits, 700)  # Don't go smaller than a reported width of 2


def fitheight(data, bold=False):
    '''Try to autofit Arial 10'''
    rowlen = len(data.split("\n"))
    if rowlen > 1:
        units = 230 * rowlen
    else:
        units = 290
    if bold:
        units *= 1.1
    return int(units)


# http://stackoverflow.com/questions/6929115/python-xlwt-accessing-existing-cell-content-auto-adjust-column-width
class FitSheetWrapper(object):
    """Try to fit columns to max size of any entry.
    To use, wrap this around a worksheet returned from the
    workbook's add_sheet method, like follows:

        sheet = FitSheetWrapper(book.add_sheet(sheet_name))

    The worksheet interface remains the same: this is a drop-in wrapper
    for auto-sizing columns.
    """

    def __init__(self, sheet):
        self.sheet = sheet
        self.widths = dict()

    def write(self, r, c, label='', *args, **kwargs):
        self.sheet.write(r, c, label, *args, **kwargs)
        width = int(fitwidth(label, True))  # treat it as bold
        if width > self.widths.get(c, 0):
            self.widths[c] = width
            self.sheet.col(c).width = width

    def __getattr__(self, attr):
        return getattr(self.sheet, attr)


###############################################################################

if __name__ == '__main__':
    # For test
    save_path = os.path.join(os.path.dirname(__file__), '../', 'excels')
    excel_file_name = u"商户交易订单2018-02-05.xls"
    merged_sheet_name = read_excel_cfg("merged_sheet_name")
    res = merge_excel(os.path.join(save_path, excel_file_name),
                      os.path.join(save_path, merged_sheet_name), merged_sheet_name)
