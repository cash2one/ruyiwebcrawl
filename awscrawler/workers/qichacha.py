#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 注意： 企查查不能与其他爬虫同时爬取，必须单独运行
# 爬取逻辑：  1： 搜索公司名，将搜索结果即公司主页加入待爬取队列，将可能有的别名映射存入period cache
#           2： 进入公司主页，将公司详情页面和对外投资页面加入队列
#           3： 解析投资页面和详情页面，存入period cache

from __future__ import print_function, division
import sys
import json
import urllib
import re
import urlparse
import lxml.html
import requests
from datetime import datetime
from downloader.cacheperiod import CachePeriod
from downloader.cache import Cache
from downloader.downloader_wrapper import Downloader
from downloader.downloader_wrapper import DownloadWrapper

from parsers.qiparser2 import QiParser
from crawlerlog.cachelog import get_logger
from settings import REGION_NAME, CACHE_SERVER

reload(sys)
sys.setdefaultencoding('utf-8')
SITE = 'http://www.qichacha.com'

def process(url, batch_id, parameter, manager, other_batch_process_time, *args, **kwargs):
    if not hasattr(process, '_downloader'):
        domain_name =  Downloader.url2domain(url)
        headers = {'Host': domain_name}
        cookie = kwargs.get('cookie', None)
        # cookie = "gr_user_id=0fceb70d-e0ab-4c16-8f21-d49b5d242b0e; PHPSESSID=ltro2cjbvonlg6mu4hupe7dcv1; CNZZDATA1254842228=371101890-1469690209-null%7C1472547698"

        if cookie:
            # print("Got cookie:", cookie)
            headers.update({'Cookie': cookie})
        setattr(process, '_downloader', DownloadWrapper(None, headers))
    if not hasattr(process, '_cache'):
        setattr(process, '_cache', CachePeriod(batch_id, CACHE_SERVER))

    if not hasattr(process, '_regs'):
        setattr(process, '_regs', {
            'search': re.compile(urlparse.urljoin(SITE, 'search\?key=(.+?)&index=(\d+)')),
            'detail': re.compile(urlparse.urljoin(SITE, 'company_getinfos\?unique=(.+?)&companyname=(.+?)&tab=base')),
            'invest': re.compile(urlparse.urljoin(SITE, 'company_getinfos\?unique=(.+?)&companyname=(.+?)(?:&p=(\d+))?&tab=touzi(?:&box=touzi)?')),
        })

    method, gap, js, timeout, data = parameter.split(':')
    gap = float(max(0, float(gap) - other_batch_process_time))
    timeout= int(timeout)
    today_str = datetime.now().strftime('%Y%m%d')

    # if kwargs and kwargs.get("debug"):
    #     get_logger(batch_id, today_str, '/opt/service/log/').info('start download')
    def reformat(info):     # 将info按企查查页面顺序插入队列
        temp = info['info'][:]
        info['info'] = []
        info['info'].append(("统一社会信用码", temp['unified_social_credit_code']))
        info['info'].append(("注册号", temp['registration_id']))
        info['info'].append(("组织机构代码", temp['organization_code']))
        info['info'].append(("经营状态", temp['status']))
        info['info'].append(("公司类型", temp['business_type']))
        info['info'].append(("成立日期", temp['begin']))
        info['info'].append(("法定代表", temp['legal_person']))
        info['info'].append(("注册资本", temp['registered_capital']))
        info['info'].append(("营业期限", temp['end']))
        info['info'].append(("登记机关", temp['registration_authority']))
        info['info'].append(("发照日期", temp['approval_date']))
        info['info'].append(("企业地址", temp['address']))
        info['info'].append(("经营范围", temp['business_scope']))
        return info


    def parse_company_investment(tree):     # 解析对外投资页面，将子公司存入sub_companies字段下
        invest_dict = {'sub_companies': [] }
        for sub_company in tree.cssselect('.list-group a.list-group-item'):
            sub_name = sub_company.cssselect('span.clear .text-lg')[0].text_content().strip()
            href = sub_company.get('href')
            province, key_num = href.rsplit('_', 2)[-2:]
            invest_dict['sub_companies'].append({
                'name': sub_name,
                'key_num': key_num,
                'province': province,
                'href': href,
            })
        return invest_dict


    content = process._downloader.downloader_wrapper(url,
        batch_id,
        gap,
        method,
        timeout=timeout,
        encoding='utf-8')
    # print(url)
    # print(content)
    if content == '':
        get_logger(batch_id, today_str, '/opt/service/log/').info("no content")
        return False


    invest_pat = "http://www.qichacha.com/company_getinfos?unique={key_num}&companyname={name}&p={p}&tab=touzi&box=touzi"
    main_pat = "http://www.qichacha.com/company_getinfos?unique={key_num}&companyname={name}&tab=base"
    parser = QiParser()
    tree = lxml.html.fromstring(content.replace('<em>', '').replace('</em>', ''))

    # if kwargs and kwargs.get("debug"):
        # print('start parsing url')

    for label, reg in process._regs.iteritems():
        m = reg.match(url)

        if not m:
            continue

        if label == 'search':   # 搜索页面解析
            comp_name = urllib.unquote(m.group(1))
            
            get_logger(batch_id, today_str, '/opt/service/log/').info('getting items', comp_name)
            dic = { 'search_name': comp_name, 'names': [] }
            urls = []
            if tree.cssselect('.table-search-list') and tree.cssselect('.tp2_tit a'):
                items = tree.cssselect('.table-search-list')
                for idx, i in enumerate(items):
                    if not i.xpath('.//*[@class=\"tp2_tit clear\"]/a/text()'):
                        continue
                    item = {}
                    item['name'] = i.xpath('.//*[@class=\"tp2_tit clear\"]/a/text()')[0]
                    # get_logger(batch_id, today_str, '/opt/service/log/').info(item['name'])
                    item['href'] = i.xpath('.//*[@class=\"tp2_tit clear\"]/a/@href')[0]
                    item['status'] = i.xpath('.//*[@class=\"tp5 text-center\"]/a/span/text()')[0]
                    item['key_num'] = item['href'].split('firm_')[1].split('.shtml')[0]
                    # get_logger(batch_id, today_str, '/opt/service/log/').info(item['key_num'])
                    if idx == 0 and comp_name == item['name']:  # 若第一个搜索结果完全匹配则只添加第一个结果入待爬取队列
                        get_logger(batch_id, today_str, '/opt/service/log/').info('appending', item['name'])
                        urls.append(main_pat.format(key_num=item['key_num'], name=item['name']))
                        urls.append(invest_pat.format(key_num=item['key_num'], name=item['name'], p='1'))
                        break
                    elif idx < 3:   # 如果第一个不完全匹配， 将前三个搜索结果加入待爬取队列
                        urls.append(main_pat.format(key_num=item['key_num'], name=item['name']))
                        urls.append(invest_pat.format(key_num=item['key_num'], name=item['name'], p='1'))
                        dic['names'].append(item['name'])
            if not urls:
                get_logger(batch_id, today_str, '/opt/service/log/').info("no result")
                return True
            get_logger(batch_id, today_str, '/opt/service/log/').info('URLS:',str(urls))
            manager.put_urls_enqueue(batch_id, urls)
            if not dic['names']:
                return True
            else:   # 不完全匹配时将search_name与前三个搜索结果存入json用作别名映射
                data = json.dumps(dic, encoding='utf-8', ensure_ascii=False)
                get_logger(batch_id, today_str, '/opt/service/log/').info('projection:', data)
                return process._cache.post(url, data)


        elif label == 'detail':     # 解析详情页面
            comp_name = urllib.unquote(m.group(2))
            get_logger(batch_id, today_str, '/opt/service/log/').info(comp_name, "detail page")
            all_info = parser.parse_detail(tree)
            all_info['name'] = comp_name
            all_info['source'] = url
            all_info['access_time'] = datetime.utcnow().isoformat()
            all_info = reformat(all_info)
            data = json.dumps(all_info, encoding='utf-8', ensure_ascii=False)
            get_logger(batch_id, today_str, '/opt/service/log/').info(data)
            return process._cache.post(url, data)

        else:           # 解析投资页面
            comp_name = urllib.unquote(m.group(2))
            key_num = m.group(1)
            page = int(m.group(3))
            pages = tree.xpath(".//a[@id=\"ajaxpage\"]/text()")
            if '>' in pages:
                urls = [invest_pat.format(key_num=key_num, name=comp_name, p=str(page + 1))]
                manager.put_urls_enqueue(batch_id, urls)
            get_logger(batch_id, today_str, '/opt/service/log/').info(comp_name, "invest page")
            invest_dict = parse_company_investment(tree)
            if not invest_dict['sub_companies']:
                return True
            invest_dict['name'] = comp_name
            invest_dict['source'] = url
            invest_dict['access_time'] = datetime.utcnow().isoformat()
            data = json.dumps(invest_dict, encoding='utf-8', ensure_ascii=False)
            get_logger(batch_id, today_str, '/opt/service/log/').info(data)
            return process._cache.post(url, data)




