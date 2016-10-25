# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yixuan Zhao <johnsonqrr (at) gmail.com>

import os
import time
import datetime
import hashlib
import sys
import re
sys.path.append('..')

from cleansing_hcrawler.hprice_cleaning import  *
from collections import Counter

class XiamiDataMover(object):
    def __init__(self, origin_dir='/data/crawler_file_cache/xiami-1015/raw/latest/0/11'):
        origin_dir =  '/data/crawler_file_cache/xiami-1015'
        self.count = 0
        self.jsons = []
        self.origin_dir = origin_dir
        self.tag_counter = Counter()
        self.versions = set()
        self.tags_by_artist = {}

    def calculate_score(self, artist_fans, song_share, comment_cnt):
        return artist_fans * 0.001 + song_share * 0.599 + comment_cnt * 0.4

    def set_directory_list(self):
        # 是一个层序遍历的函数，利用列表模拟队列
        # 输入：上级目录，得到：所有最下级目录
        # 注意break条件的判断，这是出于默认所有file同级下方可使用（即树的所有树叶深度相同），以适应aws的储存逻辑，如果不全同级则要更改判断条件
        dir_list = [self.origin_dir]
        while 1:
            directory = dir_list[0]
            sub_dir_list = os.listdir(directory)
            if not os.path.isdir(os.path.join(directory, sub_dir_list[0])):
                break
            else:
                for dirname in sub_dir_list:
                    dir_list.append(os.path.join(directory, dirname))    
                dir_list.pop(0)
        self.dir_list = dir_list

    def clean_dot(self, word):
        # word = re.sub(u'[·-‧()•]・', u'',word)
        dot_list = [u'·', u'-', u'‧', u'(', u')', u'•', u'・']  # 对于歌名，删除括号显得多余，对歌手名，需要删除括号
        for dot in dot_list:
            word = word.replace(dot, u'')
        return word

    def clean_bracket(self, song_item):
        word = song_item[u'name']
        if u'(' in word:
            left = word.find(u'(')
            right = word.find(u')')
            version = word[left+1:right]
            self.versions.add(version)
            song_item[u'tags'].append(version)
            song_item[u'name'] = re.sub('\(.*\)', '',word).strip()

    def clean_pay(self, song_item):
        # for item in song_item['raw_api_json'][u'purview_flag']:
        for item in song_item[u'purview_flag']:
            if item[u'action'] == u'LISTEN' and item[u'opt'] == u'FREE':
                song_item[u'pay'] = 0
                return
        else:
            song_item[u'pay'] = 1


    def clean_tags(self, song_item):
        tags = song_item['tags']
        artist_id = song_item['artistid']
        cleaned_tags = []
        for tag in tags:
            cleaned_tags.extend(tag.split(u' '))        # 处理空格
        cleaned_tags = list(set(cleaned_tags))            # 去重
        tag_pool = self.tags_by_artist[artist_id]
        for tag in cleaned_tags[::-1]:                  # 考虑到有删除操作，采用倒序遍历
            if not tag in tag_pool or not tag:              # 第二个条件判断偶有的空格情况
                cleaned_tags.remove(tag)
        song_item['tag_pool']     = tag_pool
        song_item['origin_tags']  = tags
        song_item['tags'] = cleaned_tags



    def clean_single_song(self, song_item):
        song_item[u'artist_fans'] = song_item[u'fans']
        del song_item[u'fans']                                   # 将fans字段替换成artist_fans

        self.clean_tags(song_item)                              # 处理空格，符号，以及按照百分比过滤

        alias_string = self.clean_dot(song_item[u'artist_alias']).strip()
        song_item['artist_alias'] = [song_item[u'artist']]           # 按照知识图谱的习惯，别名里第一个为歌手本名

        if u';' in song_item[u'artist']:                             # 合唱情况一般用;分隔
            song_item['artist_alias'].extend(song_item[u'artist'].split(u';'))
        elif u' x ' in song_item[u'artist']:                         # 有时也用 x 分隔
            song_item['artist_alias'].extend(song_item[u'artist'].split(u' x '))

        if alias_string:
            song_item['artist_alias'].extend(alias_string.split(u'/'))

        for index in range(len(song_item['artist_alias'])):
            alias = self.clean_dot(song_item['artist_alias'][index]).strip()
            song_item[u'artist_alias'][index]  = alias
            song_item[u'tags'].append(u'AN:{}'.format(alias))

        self.clean_bracket(song_item)
        self.clean_pay(song_item)
        song_item[u'name'] = self.clean_dot(song_item['name'])
        song_item[u'songName'] = song_item[u'name']
        song_item[u'tags'].append(u'MN:{}'.format(song_item[u'name']))
        song_item[u'tags'].append(u'BN:{}'.format(song_item[u'album'].strip()))
        song_item[u'hot_score'] = self.calculate_score(song_item[u'artist_fans'], song_item[u'song_share'], song_item[u'comment_cnt'])
        
        self.jsons.append(song_item)
        self.count += 1
        with open('song_dic.txt', 'a') as f:        # 导出歌曲名词典
            f.write(
                song_item[u'songName']      + '\t' +
                song_item[u'artist']        + '\t' +
                str(song_item[u'plays'])    + '\t' +
                song_item[u'id']            + '\n'
            )
        if self.count == 300:              # 说明，由于部分歌曲歌词很长，每次发送300个json可能会使data大小超出es服务器的限制
            try:                           # 但是每次发送100个又会使es插入速度太慢，所以采取这种优先发送300个，失败后再分开发送
                sendto_es(self.jsons)
            except:
                sendto_es(self.jsons[0:50])
                sendto_es(self.jsons[50:100])
                sendto_es(self.jsons[150:200])
                sendto_es(self.jsons[200:250])
                sendto_es(self.jsons[250:])
            self.count = 0
            self.jsons = []

    def statistic_one_song(self, item):
        for tag in item['tags']:
            if tag[0:3] in [u'AN:',u'BN:',u'MN:']:  # AN歌手名，BN专辑名，MN歌曲名，是在爬取过程中二次加入的，（如 AN:周杰伦 MN：晴天 ）。
              continue
            else:
                self.tag_counter[tag] += 1

        with open('artisits_alias_by_table.txt','a') as f:
            f.write('\t'.join(item['artist_alias']) + '\n')

        # with open('songname.txt','a') as f:
            # f.write(item['songName'] + '\n')


    def read_and_insert(self, dir_path):
        file_name_list = os.listdir(dir_path)
        for file_name in file_name_list:
            abs_file_path = os.path.join(dir_path, file_name)
            with open(abs_file_path, 'r') as f:
                song_list = json.load(f)
                for song in song_list:
                    self.clean_single_song(song)
                    #self.statistic_one_song(song)

    def count_for_tag(self, song_item):
        artist_id = song_item[u'artistid']
        if not self.tags_by_artist.get(artist_id, None):
            self.tags_by_artist[artist_id] = Counter()
        tags = song_item[u'tags']
        for tag in tags:
            self.tags_by_artist[artist_id][tag] += 1

    def cut_tags_by_percent(self, percent=0.2):
        for artist_id, tag_counter in self.tags_by_artist.iteritems():
            length = len(tag_counter.keys())
            self.tags_by_artist[artist_id] = [ele[0] for ele in tag_counter.most_common(int(length * percent + 0.99))]  # 保证向上取整

    def filter_tags(self, dir_path):   # 统计歌手名下所有tag出现的次数，并且只留下前20%的tag
        file_name_list = os.listdir(dir_path)
        for file_name in file_name_list:
            abs_file_path = os.path.join(dir_path, file_name)
            with open(abs_file_path, 'r') as f:
                song_list = json.load(f)
                for song in song_list:
                    self.count_for_tag(song)   # 计数

    def run(self):
        self.set_directory_list()
        for dir_path in self.dir_list:          # 由于储存粒度为专辑，先遍历第一遍，得出所有歌手的tag情况并过滤
            self.filter_tags(dir_path)
            print dir_path
        print 192
        self.cut_tags_by_percent()
        for dir_path in self.dir_list:
            self.read_and_insert(dir_path)      # 再遍历第二遍，进行清洗和插入操作

        if self.jsons:
            sendto_es(self.jsons)
        # with open('version.txt', 'w') as f:
        #     for line  in self.versions:
        #         f.write(line + '\n')


if __name__ == '__main__':
    mover = XiamiDataMover()
    mover.run()
