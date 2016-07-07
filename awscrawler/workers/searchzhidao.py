#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuande Liu <miraclecome (at) gmail.com>

from __future__ import print_function, division

import json
import urllib
import re
import urlparse
from datetime import datetime

from downloader.caches3 import CacheS3
from downloader.downloader_wrapper import Downloader
from downloader.downloader_wrapper import DownloadWrapper
from parsers.zhidao_parser import parse_search_json_v0707

from crawlerlog.cachelog import get_logger
from settings import REGION_NAME

SITE = 'http://zhidao.baidu.com'

def process(url, batch_id, parameter, manager, *args, **kwargs):
    if not hasattr(process, '_downloader'):
        domain_name =  Downloader.url2domain(url)
        headers = {'Host': domain_name}
        setattr(process, '_downloader', DownloadWrapper(None, headers, REGION_NAME))
    if not hasattr(process, '_cache'):
        head, tail = batch_id.split('-')
        print(batch_id)
        setattr(process, '_cache', CacheS3(head + '-json-' + tail))

    if not hasattr(process, '_regs'):
        setattr(process, '_regs', re.compile(urlparse.urljoin(SITE, 'search\?word=(.+)')) )


    method, gap, js, timeout, data = parameter.split(':')
    gap = int(gap)
    timeout= int(timeout)

    today_str = datetime.now().strftime('%Y%m%d')

    if kwargs and kwargs.get("debug"):
        get_logger(batch_id, today_str, '/opt/service/log/').info('start download')

    content = process._downloader.downloader_wrapper(url,
        batch_id,
        gap,
        timeout=timeout,
        encoding='gb18030')

    if content == '':
        return False

    if kwargs and kwargs.get("debug"):
        get_logger(batch_id, today_str, '/opt/service/log/').info('start parsing url')

    try:
        result = parse_search_json_v0707(content)
    except:
        content = process._downloader.downloader_wrapper(url,
            batch_id,
            gap,
            timeout=timeout,
            encoding='gb18030',
            refresh=True)
        if content == '':
            return False
        result = parse_search_json_v0707(content)

    if kwargs and kwargs.get("debug"):
        get_logger(batch_id, today_str, '/opt/service/log/').info('start post json')

    return process._cache.post(url, json.dumps(result))

