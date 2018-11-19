# coding:utf-8
from apscheduler.schedulers.background import BlockingScheduler

from app import RUN_TIME
from server.batch_order import refresh_merchant_config, download_all_orders
from server.log4cas import LOGGER
from server.utils import get_now_date_str

#
# LOGGER.info("try to run...")
# # scheduler.init_app(app)
# scheduler.start()
# LOGGER.info("run ok")
#
# try:
#     import uwsgi
#
#     LOGGER.info("uwsgi import ok")
#     import uwsgidecorators
#
#
#     @timer(1, target='mule')
#     def hello():
#         LOGGER.info("heelo")
#
#
#     while True:
#         sig = uwsgi.signal_wait()
#         LOGGER.info(sig)
# except Exception as err:
#     pass


s1 = BlockingScheduler()


def refresh_session_job():
    # s1 = BackgroundScheduler()
    LOGGER.info(u"开始：定时刷新session任务启动，%ss运行一次", RUN_TIME)
    refresh_merchant_config()
    LOGGER.info(u"完成：定时刷新session任务")


def refresh_merchant_data_job():
    """
    0 1,31 0-1,7-23 * * ? *
    每分钟的1，31； 小时0~1;7~23
    https://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html?highlight=cron
    http://cron.qqe2.com/
    :return:
    """
    order_date = get_now_date_str()
    LOGGER.info(u"开始：定时刷新商户数据缓存,date=%s", order_date)
    res = download_all_orders(order_date)
    LOGGER.info(u"完成：定时刷新商户数据缓存，详情：%s", res.get('tip'))


def start_scheduler():
    try:
        s1.add_job(refresh_session_job, 'interval', seconds=RUN_TIME)
        s1.add_job(refresh_merchant_data_job, 'cron', minute="1,31", hour="0,1,7-23")
        s1.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as ex:
        LOGGER.exception(u"uwsgi的mule方式启动BackgroundScheduler失败,%s", ex)

    try:
        import uwsgi

        while True:
            # 阻塞uwsgi，避免一直启动mule
            sig = uwsgi.signal_wait()
            LOGGER.info(sig)
    except Exception as err:
        pass


start_scheduler()
