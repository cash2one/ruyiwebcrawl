#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuande Liu <miraclecome (at) gmail.com>

from __future__ import print_function, division

#from selenium import webdriver
import requests
import time
import sys

from .cache import Cache

class Downloader(object):

    def __init__(self, batch_id, cacheserver, request=False, gap=0, timeout=10, groups=None, refresh=False):
        """ batch_id can be 'zhidao', 'music163', ...
        """
        self.request = request
        self.TIMEOUT = timeout
        self.RETRY = 2

        self.batch_key_file = batch_id.rsplit('-', 1)[0].replace('-', '_')
        self.cache = Cache(batch_id, cacheserver)
        self.gap = gap
        self.groups = groups
        self.refresh = refresh

        self.login()

    def login(self):
        common_header = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Accept-Language': 'zh-CN,en-US;q=0.8,en;q=0.6',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': 1,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.84 Safari/537.36',
        }

        if self.request is True:
            session = requests.Session()
            session.mount('http://', requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=30, max_retries=self.RETRY))
            session.headers = common_header
            self.driver = session

        else:
            self.driver = webdriver.Firefox()
            self.driver.implicitly_wait(30)
            time.sleep(5)

    def close(self):
        if self.request is False:
            self.driver.quit()

    def update_header(self, header):
        if self.request is True:
            self.driver.headers.update(header)

    def _get_sleep_period(self):
        """ sleep for cookie
        """
        return self.gap

    def request_download(self, url, method='get', encoding='utf-8', redirect_check=False, error_check=False, data=None):
        for i in range(self.RETRY):

            try:
                if method == 'post':
                    response = self.driver.post(url, timeout=self.TIMEOUT, data=data)
                else:
                    response = self.driver.get(url, timeout=self.TIMEOUT)

                if response.status_code == 200:
                    if redirect_check and response.url != url:
                        continue
                    if error_check:
                        if __import__('downloader.error_checker.{}'.format(self.batch_key_file), fromlist=['error_checker']).error_checker(response):
                            continue
                    response.encoding = encoding
                    return response.text # text is unicode
            except Exception as e: # requests.exceptions.ProxyError, requests.ConnectionError, requests.ConnectTimeout
                                   # requests.exceptions.MissingSchema
                print('requests failed: {}, detail: {}'.format(sys.exc_info()[0], e))
            finally:
                time.sleep(self._get_sleep_period())
        else:
            return u''


    def selenium_download(self, url):
        for i in range(self.RETRY):
            try:
                self.driver.get(url)
                source = self.driver.page_source # unicode
                return source
            except:
                continue
            finally:
                time.sleep(self._get_sleep_period())
        else:
            return u''

    def requests_with_cache(self,
                            url,
                            method='get',
                            encoding='utf-8',
                            redirect_check=False,
                            error_check=False,
                            data=None,
                            groups=None,
                            refresh=False):

        def save_cache(url, source, groups, refresh):
            refresh = self.refresh if refresh is None else refresh
            groups = self.groups if groups is None else groups
            ret = self.cache.post(url, source, groups, refresh)
            if ret not in [True, False]:
                print('request with cache save_cach return: ', ret)
                return False
            return ret

        if refresh is False:
            content = self.cache.get(url)
            if content != u'':
                return content

        if self.request is True:
            source = self.request_download(url, method, encoding, redirect_check, error_check, data)
        else:
            source = self.selenium_download(url)

        if source == u'':
            return source
        save_cache(url, source, groups, refresh)

        return source
