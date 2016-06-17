#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuande Liu <miraclecome (at) gmail.com>
# add answer api url to zhidao-answer-xxx queue
from __future__ import print_function, division
import re
import base64
import json

from invoker.zhidao import BATCH_ID
from downloader.cache import Cache
from downloader.downloader_wrapper import DownloadWrapper
from parsers.zhidao_parser import parse_q_time, parse_q_content, parse_answer_ids, generate_question_json

from settings import CACHE_SERVER


def get_answer_url(q_id, r_id):
    return ('http://zhidao.baidu.com/question/api/mini?qid={}'
            '&rid={}&tag=timeliness'.format(q_id, r_id))


def process(url, parameter, manager, *args, **kwargs):
    if not hasattr(process, '_downloader'):
        setattr(process, '_downloader', DownloadWrapper(CACHE_SERVER, {'Host': 'zhidao.baidu.com'}))
    if not hasattr(process, '_cache'):
        setattr(process, '_cache', Cache(BATCH_ID['json'], CACHE_SERVER))


    m = re.search(
        'http://zhidao.baidu.com/question/(\d+).html', url)
    if not m:
        return False

    q_id = m.group(1)
    method, gap, js, data = parameter.split(':')
    gap = int(gap)

    timeout = 10
    content = process._downloader.downloader_wrapper(url, BATCH_ID['question'], gap, timeout=timeout, encoding='gb18030', error_check=True, refresh=True)
    if content is False:
        return False

    q_json = generate_question_json(q_id, content)
    if q_json is None:
        return False
    elif q_json == {}: # question expired in zhidao
        return True

    question_content = json.dumps(q_json)

    success = process._cache.post(url, question_content)
    if success is False:
        return False

    answer_urls = []
    for answer_id in q_json['answer_ids'][:3]:
        answer_urls.append( get_answer_url(q_id, answer_id) )
    manager.put_urls_enqueue(BATCH_ID['answer'], answer_urls)

    return True
