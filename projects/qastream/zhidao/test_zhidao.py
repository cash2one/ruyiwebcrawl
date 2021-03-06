#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib
import os
import sys
import collections
import codecs
import datetime
import json
import re

sys.path.append(os.path.abspath(os.path.dirname(__file__)) )
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

reload(sys)
sys.setdefaultencoding("utf-8")

#   from handler import ZhidaoSearchHandler
from zhidao_scheduler import Scheduler
from hzlib import libregex

def test():
    qword = u"天空为什么是蓝色的"

    if not libregex.is_question_baike(qword):
        print "skip not baike"
        return

    cacheserver = "http://192.168.1.179:8000"
    api = Scheduler(cacheserver=cacheserver)
    ret = api.zhidao_search_select_best(qword)
    assert(ret)
    print json.dumps(ret, ensure_ascii=False, indent=4, sort_keys=True)

    ret = api.zhidao_search_select_best_qids(qword)
    assert(ret)
    print json.dumps(ret, ensure_ascii=False, indent=4, sort_keys=True)

    ret = api.run(qword)
    assert(ret)
    print json.dumps(ret, ensure_ascii=False, indent=4, sort_keys=True)

def main():
    #print sys.argv

    if len(sys.argv)<2:
        return

    option= sys.argv[1]

    if "test" == option:
        test()


if __name__ == "__main__":
    main()
