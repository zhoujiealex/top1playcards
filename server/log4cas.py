"""
Created on Oct 24, 2015
If building a library:
use get_logger to retrieve a dummy logger, then configure and use.

If building application:
Could just use get_predefined_main_logger to get a pre-defined logger.

Or use get_main_logger_or_predefined in both situation.

@author: borrowed from ace_luo by karl_zhou
"""

import logging
import logging.config
import os

# disable exception in logging module for production
logging.raiseExceptions = False


def get_main_logger():
    logger = logging.getLogger('main')
    if len(logger.handlers) < 1:
        logger.addHandler(logging.NullHandler())
    return logger


def get_predefined_main_logger():
    log_conf_file = os.path.join(os.path.dirname(__file__), 'log4cas.conf')
    logging.config.fileConfig(log_conf_file)
    return logging.getLogger('main')


def get_predefined_sql_logger():
    log_conf_file = os.path.join(os.path.dirname(__file__), 'log4cas.conf')
    logging.config.fileConfig(log_conf_file)
    return logging.getLogger('sqlalchemy')


def get_main_logger_or_predefined():
    logger = get_main_logger()
    _handlers = logger.handlers
    if len(_handlers) == 1 and isinstance(_handlers[0], logging.NullHandler):
        logger = get_predefined_main_logger()
    return logger


LOGGER = get_predefined_main_logger()

if __name__ == '__main__':
    pass
