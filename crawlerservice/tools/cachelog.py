#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuande Liu <miraclecome (at) gmail.com>

from __future__ import print_function, division

import logging
import os

from settings import FSCACHEDIR
from tools import log, ip, path

def get_logger(batch_id, today_str):
    """ 127.0.0.1_20160522.log

    :param today_str: datetime.now().strftime('%Y%m%d')
    """

    def filename_in_logger_out():
        absdir = os.path.join(FSCACHEDIR, batch_id, 'meta')
        path.makedir(absdir)
        absfname = os.path.join(absdir, 
                                '{}_{}.log'.format(
                                    get_logger._ipaddr,
                                    get_logger._today_str)
                               )
        if not os.path.isfile(absfname):
            with open(absfname, 'a'):
                pass
        return log.init(batch_id, absfname, level=logging.INFO, size=100*1024*1024)

    if not hasattr(get_logger, '_ipaddr'):
        setattr(get_logger, '_ipaddr', ip.get_local_ip_address())

    if not hasattr(get_logger, '_today_str'):
        setattr(get_logger, '_today_str', today_str)
        setattr(get_logger, '_logger', filename_in_logger_out())

    if get_logger._today_str != today_str:
        setattr(get_logger, '_today_str', today_str)
        setattr(get_logger, '_logger', filename_in_logger_out())

    return get_logger._logger