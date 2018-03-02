# coding:utf-8
from apscheduler.schedulers.background import BlockingScheduler

from app import RUN_TIME
from server.batch_order import refresh_merchant_config
from server.log4cas import LOGGER

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


# s1 = BackgroundScheduler()
s1 = BlockingScheduler()
s1.add_job(refresh_merchant_config, 'interval', seconds=RUN_TIME)

try:
    s1.start()
    LOGGER.info(u"定时刷新session任务启动，%ss运行一次", RUN_TIME)
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
