#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yixuan Zhao <johnsonqrr (at) gmail.com>
# 总数据接近5000条，插入时会有10条左右的record重复


import json
import os
import hashlib
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from loader import Loader
from hzlib import libfile
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class YaotongnewdailyLoader(Loader):
    def read_jsn(self, data_dir):
        for fname in os.listdir(data_dir):
            for js in libfile.read_file_iter(os.path.join(data_dir, fname), jsn=True):
                try:
                    self.parse(js)
                except Exception, e:
                    print ('{}: {}'.format(type(e), e.message))

    def parse(self, jsn):
        self.success = 0
        source = 'http://www.yt1998.com/priceInfo.html'
        domain = self.url2domain(source)
        for row in jsn[u'data']:
            trackingId = hashlib.sha1('{}_{}'.format(source, row[u'access_time'])).hexdigest()
            name = row[u'ycnam']
            priceType = ''
            productPlaceOfOrigin = row[u'chandi']
            sellerMarket = row[u'shichang']
            if not sellerMarket.endswith(u'市场'):
                sellerMarket = u'{}市场'.format(sellerMarket)
            productGrade = row[u'guige']
            validDate = row[u'dtm']
            price = row[u'pri']
            tags = [name, priceType, productPlaceOfOrigin, sellerMarket, productGrade]
            rid = hashlib.sha1('{}_{}_{}'.format('_'.join(tags), validDate, domain)).hexdigest()
            series = '_'.join(tags)
            seriesid = '{}_{}'.format(series, domain)
            self.insert_meta_by_series(series, seriesid)
            self.pipe_line.clean_product_place(tags[2], tags)

            record = {
                'rid': rid,
                'gid': rid, # 不可变
                'series': series,
                'seriesid': seriesid,
                'tags': [ tag for tag in tags if tag],
                'createdTime': datetime.utcnow(),
                'updatedTime': datetime.utcnow(),
                'source': {
                    'url': source,
                    'domain': domain,
                    'trackingId': trackingId,
                    'confidence': '0.7', 
                },
                'claims': [],
            }
            record['claims'].append({'p': u'商品名称', 'o': name})
            record['claims'].append({'p': u'日期', 'o': validDate})
            record['claims'].append({'p': u'价格', 'o': str(price)})
            record['claims'].append({'p': u'价格单位', 'o': u'元/千克',})
            record['claims'].append({'p': u'产地','o': productPlaceOfOrigin})
            record['claims'].append({'p': u'报价地点','o': sellerMarket})
            record['claims'].append({'p': u'规格', 'o': productGrade})
            record['claims'].append({'p': u'币种', 'o': u'CNY' })
            record['recordDate'] = validDate
            try:
                self.node.insert(record)
                self.success += 1
            except DuplicateKeyError as e:
                print (e)
        print ('success: {}'.format(self.success))

def load_all(path='/data/hproject/2016'):
    obj = YaotongnewdailyLoader()
    for diretory in os.listdir(path):
        if diretory.startswith('yaotongnewdaily'):
            abs_path = os.path.join(path, diretory)
            obj.read_jsn(abs_path)

if __name__ == '__main__':
    # obj = YaotongnewdailyLoader()
    #obj.read_jsn('/tmp/yaotongnewdaily-20160913')
    load_all()