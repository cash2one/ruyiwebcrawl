#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuande Liu <miraclecome (at) gmail.com>

from __future__ import print_function, division

import codecs
import lxml.html
import json
import re
import string
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from hzlib.libfile import read_file_iter, write_file
from filter_lib import regdisambiguation, regfdentitysearch


def zgdbk_parse_entity(entity):
    if entity.startswith('<font'):
        return entity[entity.find('red>')+4:].replace('</font>', '')
    if entity.startswith('\xee'): # human unreadable string
        return
    return entity

def zgdbk_extract_entity(infilename):
    entities = set()
    re_entity = re.compile('<span id="span2" class="STYLE2">(.+)</span')

    for line in read_file_iter(infilename):
        m = re_entity.match(line)
        if m:
            entity = zgdbk_parse_entity( m.group(1) )
            if entity:
                entities.add(entity.strip().lower())

    write_file('entities/zgdbk_entities.txt', entities)
    print('zgdbk entities length: ', len(entities))
    return entities


def bdbk_extract_entity(ifilename):
    entities = set()
    last_line = '</>'

    for line in read_file_iter(ifilename):
        line = line.lower()
        if last_line == '</>':
            entities.add(line)
        elif line.startswith('@@@LINK='):
            entities.add(line[8:])
        last_line = line

    write_file('entities/{}_entities.txt'.format(ifilename), entities)
    print('bdbk entities length: ', len(entities))
    return entities


def wiki_extract_entity():
    entities = set()

    for jsn in read_file_iter('wikidata_zh_simplified.json', jsn=True):
        m = regdisambiguation.match(jsn[u'chinese_label'])
        item = m.group(1) if m else jsn[u'chinese_label']
        entities.add(item.encode('utf-8').strip().lower())
        if u'chinese_aliases' in jsn:
            entities.update(map(string.lower, map(string.strip, map(lambda x: x.encode('utf-8'), jsn[u'chinese_aliases']))))

    for jsn in read_file_iter('merge_step_5_simplified.json', jsn=True):
        key = jsn.keys()[0]
        key = key[key.rfind('/') + 1:-1].strip().lower()
        m = regdisambiguation.match(key)
        entity = m.group(1) if m else key
        entities.add(entity.encode('utf-8'))

    write_file('entities/wiki_entities.txt', entities)
    print('wiki entities length: ', len(entities))
    return entities


def wiki_title_entity(fname):
    entities = set()

    for line in read_file_iter(fname):
        m = regdisambiguation.match(line.strip().decode('utf-8'))
        item = m.group(1).encode('utf-8') if m else line.strip()
        if not item.startswith('\xee'): # human unreadable string
            entities.add(item.strip().lower())

    write_file('entities/{}_title'.format(fname), entities)
    print('wiki title entities length: ', len(entities))
    return entities


def comic_song_extract_entity(fname):
    entities = set()

    for line in read_file_iter(fname):
        m = regfdentitysearch.match(line.decode('utf-8'))
        entity = m.group(1).encode('utf-8') if m else line
        entities.add(entity)

    return entities


if __name__ == '__main__':
    entities = set()

    entities.update( zgdbk_extract_entity('zgdbk.txt') )
    entities.update( bdbk_extract_entity('vbk2012.txt') )
    entities.update( bdbk_extract_entity('vbk2012_ext.txt') )
    entities.update( wiki_extract_entity() )
    entities.update( wiki_title_entity('zhwiki-20160601-all-titles-in-ns2.txt') )

    entities.remove('')
    write_file('entities/entities_0629_raw.txt', entities)
