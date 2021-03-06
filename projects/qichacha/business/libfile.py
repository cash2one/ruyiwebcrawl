# encoding=utf-8
'''
change log
2016-05-24    created
'''

import glob
import os
import sys
import json
import collections
from collections import defaultdict
import codecs
import re
import hashlib

def genEsId(text):
    #assert question as utf8
    text =text.encode('utf-8')
    return hashlib.md5(text).hexdigest()


def writeExcel(items, keys, filename):
    import xlwt
    wb = xlwt.Workbook()
    PAGE_SIZE = 60000
    rowindex =0
    sheetindex=0
    for item in items:
        if rowindex % PAGE_SIZE ==0:
            sheetname = "%02d" % sheetindex
            ws = wb.add_sheet(sheetname)
            rowindex = 0
            sheetindex +=1

            colindex =0
            for key in keys:
                ws.write(rowindex, colindex, key)
                colindex+=1
            rowindex +=1

        colindex =0
        for key in keys:
            v = item.get(key,"na")
            if type(v) == list:
                v = ','.join(v)
            if type(v) == set:
                v = ','.join(v)
            ws.write(rowindex, colindex, v)
            colindex+=1
        rowindex +=1

    print filename
    wb.save(filename)


def readExcel(headers, filename, start_row=0, non_empty_col=-1):
    # http://www.lexicon.net/sjmachin/xlrd.html
    import xlrd
    counter = collections.Counter()
    workbook = xlrd.open_workbook(filename)
    ret = defaultdict(list)
    for name in workbook.sheet_names():
        sh = workbook.sheet_by_name(name)
        for row in range(start_row, sh.nrows):
            item={}
            rowdata = sh.row(row)
            if len(rowdata)< len(headers):
                print "skip",rowdata
                continue

            for col in range(len(headers)):
                value = sh.cell(row,col).value
                if type(value) in [unicode, basestring]:
                    value = value.strip()
                item[headers[col]]= value

            if non_empty_col>=0 and not item[headers[non_empty_col]]:
                #print "skip empty cell"
                continue

            ret[name].append(item)
        print "loaded",filename, len(ret[name])
    return ret


def file2list(filename, encoding='utf-8'):
    ret = list()
    visited = set()
    with codecs.open(filename,  encoding=encoding) as f:
        for line in f:
            line = line.strip()
            #skip comment line
            if line.startswith('#'):
                continue

            if line and line not in visited:
                ret.append(line)
                visited.add(line)
    return ret

def file2set(filename, encoding='utf-8'):
    ret = set()
    with codecs.open(filename,  encoding=encoding) as f:
        for line in f:
            line = line.strip()
            #skip comment line
            if line.startswith('#'):
                continue

            if line and line not in ret:
                ret.add(line)
    return ret

def lines2file(lines, filename, encoding='utf-8'):
    with codecs.open(filename, "w", encoding=encoding) as f:
        for line in lines:
            f.write(line)
            f.write("\n")

def json2file(data, filename,encoding ='utf-8'):
    with codecs.open(filename, "w", encoding=encoding) as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def items2file(items, filename,encoding ='utf-8', modifier='w'):
    with codecs.open(filename, modifier, encoding=encoding) as f:
        for item in items:
            f.write("{}\n".format(json.dumps(item, ensure_ascii=False)))
