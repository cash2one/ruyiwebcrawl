#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuande Liu <miraclecome (at) gmail.com>

from __future__ import print_function, division

from collections import Counter


alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
punctuation = '!@#$%^&*()-_+={}[]|\;:<>,./?~`，。、！？（）‘’《》｛｝＊…～★【】“” ｜”『』'
symbol = alphabet + punctuation

def split_by_word_length(fname):
    fd1 = open(fname + '1.txt', 'w')
    fd2 = open(fname + '2.txt', 'w')
    fd3 = open(fname + '3.txt', 'w')
    fd4 = open(fname + '4.txt', 'w')
    with open(fname) as fd:
        count = 0
        for line in fd:
            count += 1
            line = line.strip()
            for char in line:
                if char not in symbol:
                    break
            else:
                if line.isalnum():
                    pass
                else:
                    continue

            if len(unicode(line)) == 1:
                fd1.write(line + '\n')
            elif len(unicode(line)) == 2:
                fd2.write(line + '\n')
            elif len(unicode(line)) == 3:
                fd3.write(line + '\n')
            else:
                fd4.write(line + '\n')

    print('finish')
    fd1.close()
    fd2.close()
    fd3.close()
    fd4.close()


def test_coverage():
    test_words = set()
    entities = set()
    with open('baike_test0623.txt') as fd:
        for line in fd:
            if line.strip() == '':
                continue
            test_words.add(line.strip())

    with open('entities/entities_0623.txt') as fd:
        for line in fd:
            entities.add(line.strip())

    intersection = test_words.intersection(entities)
    coverage = len(intersection) / len(test_words)
    print(coverage)

def statistics_length_by_word():
    counter = Counter()
    with open('entities/entities_0623_raw.txt') as fd,\
         open('entities_lte7.txt', 'w') as wfd7,\
         open('entities_gt7.txt', 'w') as wfd8:

        for line in fd:
            uline = line.strip().decode('utf-8')
            counter[len(uline)] += 1

            if len(uline) <= 7:
                wfd7.write(line)
            else:
                wfd8.write(line)
    print(counter)
