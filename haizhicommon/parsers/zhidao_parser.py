#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Yuande Liu <miraclecome (at) gmail.com>

from __future__ import print_function, division

import re
import json

def parse_page_title(content):
    """
    :return:   0 unknow webpage
               1 question expire
               string of title
    """
    m = re.search('<title>(.*)</title>', content)
    if m:
        title = m.group(1)
        if u'_百度知道' not in title:
            if u'百度知道-信息提示' == title:
                return 0
            return -1
        title = re.sub(u'_百度知道', u'', title)
        return title
    return -1


def parse_q_time(content):
    m = re.search(
        '<em class="accuse-enter">.*\n*</ins>\n*(.*)\n*</span>', content)
    if m is None:
        return
    q_time = m.group(1)
    return q_time


def parse_q_content(content):
    q_content = ''
    m = re.search('accuse="qContent">(.*?)(</pre>|</div>)', content)
    n = re.search('accuse="qSupply">(.*?)(</pre>|</div>)', content)

    if m:
        q_content = m.group(1)
        q_content = re.sub('<.*?>', '\n', q_content)
        q_content = q_content.strip()
    if n:
        supply = n.group(1)
        q_content += supply

    if 'word-replace' in q_content:
        return

    return q_content


def parse_answer_ids(content):
    result = re.findall('id="answer-(\d+)', content)
    return result


def parse_asker_username(content):
    m = re.search('a class="user-name" alog-action="qb-ask-uname" rel="nofollow" href="http://www.baidu.com/p/(.*?)\?from=zhidao" target="_blank">', content)
    if m:
        username = m.group(1)
        return username
    return

def generate_question_json(qid, content):
    """
    :return: None means error
             {} means question expire
    """
    q_title = parse_page_title(content)
    if q_title == 0:
        return
    elif q_title == 1:
        return {}
    q_content = parse_q_content(content)
    if q_content is None:
        return

    asker_username = parse_asker_username(content)
    q_time = parse_q_time(content)
    rids = parse_answer_ids(content)
    item = {
        'id': qid,
        'question': q_title,
        'question_content': q_content,
        'question_time': q_time,
        'asker_username': asker_username,
        'answer_ids': rids,
    }
    return item


def generate_answer_json(ans_content):
    content = json.loads(ans_content)
    return {
        'question_id': content[u'encode_qid'],
        'answer_id': str(content[u'id']),
        'is_best': content[u'isBest'],
        'is_recommend': content[u'isRecommend'],
        'is_highquality': content[u'isHighQuality'],
#        'is_excellent': content[u'isExcellent'],
#        'is_special': content[u'isSpecial'],
        'answer_time': content[u'createTime'],
        'content': content[u'content'].encode('utf-8'),
        'agreement': content[u'valueNum'],
        'disagreement': content[u'valueBadNum'],
    }


def zhidao_search_parse_qids(content):
    """
    :param content: content is unicode html string
    """
    ret = re.findall('href=\"(?:http://zhidao.baidu.com)?/question/(\d+).html', content)
    if ret:
        return ret[:1]
    return []

def zhidao_search_questions(content):
    """
    :param content: content is unicode html string
    :return : a list consists of 1-2 question

    说明：
    1.先检查推荐问题，如存在且合法则直接加入结果列表。 （合法指的是来源为百度知道网页，下同）
    2.再检查一般问题，将存在赞数的合法问题放入问题列表。
    3.对问题列表按照赞数进行排序，取得最高赞回答。
    4.最后处理结果：
    i.如果结果中有推荐问题，当最高赞问题赞数高于推荐问题则加入，反之丢弃。
    ii.如果结果中没有推荐问题，直接加入最高赞问题。
    iii.如果第二步中不存在最高赞问题，即所有合法问题都无赞，则加入原始页面中第一个合法问题。

    """
    import lxml.html
    dom = lxml.html.fromstring(content)

    recommend = dom.xpath('//div[@id="wgt-autoask"]')
    result = []
    recommend_approve = 0
    if recommend:
        url = recommend[0].xpath('.//a/@href')[0]
        q_id = re.findall('zhidao.baidu.com/question/(\d+).html', url)
        if q_id:
            value_text = recommend[0].xpath('.//i[@class="i-agree"]/../text()')[1]
            recommend_approve = int(re.findall('(\d+)', value_text)[0])
            recommend_id = q_id[0]
            result.append(recommend_id)

    question_list = []
    first_q_id = None
    normal = dom.xpath('//dl[contains(@class,"dl")]')

    for node in normal:
        url = node.xpath('./dt/a/@href')
        q_id = re.findall('zhidao.baidu.com/question/(\d+).html', url[0])
        if not q_id:
            continue
        q_id = q_id[0]
        if not first_q_id:
            first_q_id = q_id
        node_text = node.xpath('.//i[@class="i-agree"]/../text()')
        if node_text:
            q_approve = int(node_text[1].strip())
            question_list.append((q_id, q_approve))

    max_approve = -1
    if question_list:
        question_list=sorted(question_list, key=lambda question: question[1])
        max_id,max_approve=question_list[-1]

    if max_approve>recommend_approve:
        result.append(max_id)
        return result
    else:
        return [first_q_id]

def parse_search_get_best(content):
    search_result_json = parse_search_json_v0615(content)

    # get the best answer
    if search_result_json:
        for item in search_result_json:
            if item["is_recommend"] == 1:
                return item

    return False



def parse_search_json_v0615(content, start_result_index=0, use_recommend_only = False):
    """
    :param content: content is unicode html string
    :return : a list consists of 1-2 question
    """
    result = parse_search_json_v0707(content)
    if result:
        return result["results"]
    else:
        return []

def parse_search_json_v0707(content, word=None, start_result_index=0, use_recommend_only=False):
    ret = []
    result = {"results": ret, "total": 0, "word": word}
    #print (type(content), len(content))
    if not isinstance(content, unicode):
        content = content.decode("gb18030")

    import lxml.html
    dom = lxml.html.fromstring(content)
    #print (content)
    baike = dom.xpath('//div[@id="wgt-baike"]')
    if baike:
        url = baike[0].xpath('.//a/@href')[0]
        q_id = re.findall('http://baike.baidu.com/subview/\d+/(\d+).htm', url)
        if q_id:
            node = baike[0]
            question = u"".join(node.xpath('.//dt[@class="title"]/a//text()')).strip()
            question = question.replace(u"_百度百科","")
            answers_raw = u"".join(node.xpath('.//div[@class="desc"]/p[not(contains(@class, "lnkList"))]//text()')).strip()

            src = "baike"
            item = {
                "id": u"{}:{}".format(src, q_id),
                "question_id": q_id[0],
                "source": src,
                "cnt_answer": 0,
                "cnt_like": 0,
                "question": question,
                "answers": clean_answers(answers_raw),
                "answers_raw": answers_raw,
            }
            #print (json.dumps(item, ensure_ascii=False, indent=4))
            ret.append(item)

    #print (len(content), content[0:1000])
    list_text = dom.xpath('//div[@id="wgt-picker"]//span[contains(@class,"f-lighter")]//text()')
    result_total = u"".join(list_text).strip()
    #print ("result_total>>>>>", result_total)

    if result_total:
        result_total = re.sub(ur"[^0-9]","", result_total)
        if re.search(ur"^[0-9]+$", result_total):
            result["total"] = int(result_total)
    #print ("result_total>>>>>", result_total, result.get("total"))


    recommend = dom.xpath('//div[@id="wgt-autoask"]')
    #print (len(recommend))
    for node in recommend:
        item = parse_search_result_item(node)
        if item:
            ret.append(item)
            item["result_index"] = start_result_index + len(ret)
            item["is_recommend"] = 1

    if not use_recommend_only:
        normal = dom.xpath('//dl[contains(@class,"dl")]')
        #print (len(normal))
        for node in normal:
            #print (idx)
            item = parse_search_result_item(node)
            if item:
                ret.append(item)
                item["is_recommend"] = 0
                item["result_index"] = start_result_index + len(ret)

    #print (len(ret))
    return result

URL_PATTERNS = [
    {
        "source":"zhidao",
        "url_pattern":"zhidao.baidu.com/question/(\d+).html"
    },
    {
        "source":"zybang",
        #http://www.zybang.com/question/2c934b18be91da5fa4133d793c702900.html
        "url_pattern":"zybang.com/question/(.+).html"
    },
    {
        "source":"muzhi",
        #http://muzhi.baidu.com/question/1240767390499604219.html?fr=iks&word=%CE%AA%CA%B2%C3%B4%C8%CB%BB%E1%B3%F6%BA%B9%3F&ie=gbk
        "url_pattern":"muzhi.baidu.com/question/(\d+).html"
    },
    {
        "source":"baobao",
        #http://muzhi.baidu.com/question/1240767390499604219.html?fr=iks&word=%CE%AA%CA%B2%C3%B4%C8%CB%BB%E1%B3%F6%BA%B9%3F&ie=gbk
        "url_pattern":"baobao.baidu.com/question/(.+).html"
    },
    {
        "source":"other",
        #http://www.zybang.com/question/2c934b18be91da5fa4133d793c702900.html
        "url_pattern":"http://.+/question/(.+).html"
    }
]


def parse_search_result_item(node):
    url = node.xpath('.//a/@href')[0]
    qid = None
    item = None
    for srcitem in URL_PATTERNS:
        src = srcitem["source"]
        qids = re.findall(srcitem["url_pattern"], url)
        if qids:
            #print (qids)
            qid = "{0}:{1}".format(src, qids[0])
            #print (qids)
            item = {
                "id":qid,
                "question_id": qids[0],
                "source": src,
                "cnt_answer": 0,
                "cnt_like": 0
            }
            break

    if not qid:
        print ("!!!!!!!!UNKNOWN URL", url)
        return None

    item["question"] = u"".join(node.xpath('.//dt/a//text()')).strip()
    #item["question_good"] =  (re.search(ur"^[^？。！]+[。！？]?$", item["question"]) is not None)

    value_text = node.xpath('.//i[@class="i-agree"]/../text()')
    if value_text:
        digit_text = re.findall('(\d+)', value_text[1])
        if digit_text:
            item["cnt_like"]  = int(digit_text[0])

    value_text = node.xpath('.//dd[contains(@class,"explain")]//a/text()')
    if value_text:
        #print (json.dumps(value_text, ensure_ascii=False))
        digit_text = re.findall('(\d+)', value_text[-1])
        if digit_text:
            item["cnt_answer"]  = int(digit_text[0])

    value_text = node.xpath('.//dd[contains(@class,"summary")]//text()')
    #print ("---", len(value_text))
    if value_text:
        temp = u"".join(value_text[1:]).strip()
        #temp = temp.replace(u"...","")
        item["question_content"] = temp
        #temp = re.sub(ur"([。！？ ]).*$",r"\1", temp).strip()
        #item["question_content"] = temp
        #item["question_content_good"] =  (re.search(ur"^[^？。！]+[。！]?$", temp) is not None)


    value_text = node.xpath('.//dd[contains(@class,"answer")]//text()')
    if value_text:
        temp = u"".join(value_text[1:]).strip()
        temp = temp.replace(u"推荐答案","").replace(u"[详细]","").strip()
        item["answers_raw"] = temp


        answers_clean  = clean_answers(temp)

        #if re.search(ur"(：|；|，|。。｜\.\.)$", answers_clean):
        #    return None

        #print("answers", type(temp), temp)
        item["answers"] = answers_clean
        #temp = re.sub(ur"([。！？ ]).*$",r"\1", temp).strip()
        #item["answers_"] = temp
        #item["answers_good"] =  (re.search(ur"^[^？。！]+[。！]?$", temp) is not None)

    """
    {
        "answers": "《伊索寓言》原书名为《埃索波斯故事集成》，是古希腊民间流传的讽喻故事，经后人加工，成为现在流传的《伊索寓言》。《伊索寓言》是一部世界上最早的寓言故事集。伊索，弗里吉亚人，伊索是公元前6世纪古希腊著名的寓言家。他与克雷洛夫、拉·封丹和莱辛并称世界四大寓言家。他曾是萨摩斯岛雅德蒙家的奴隶，曾被转卖多次，但因知识渊博，聪颖过人，最后获得自由。公元前6世纪的希腊寓言家。一个丑陋无比,但是智慧无穷的寓言大师。据希罗...",
        "cnt_answer": 0,
        "cnt_like": 6,
        "id": "zhidao:363990033",
        "is_recommend": 1,
        "question": "伊索寓言是一本什么书？",
        "question_id": "363990033",
        "result_index": 1,
        "source": "zhidao"
    }
    """
    return item

def clean_answers(answers):

    temp = re.sub(ur"[\.]{3,10}$", "",answers)
    if temp == answers or re.search(ur"[。！？]", temp):
        temp = re.sub(ur"([。！？])[^。！？]*$",r"\1", temp)
    elif re.match(ur"^[\u4E00-\u9FA5]{20,1000}$", temp):
        temp = ""
    elif len(temp)>80 and not re.search("[a-zA-Z]{2,100}", temp):
        index = temp.find(" ",80)
        if index > 80:
            temp = temp[:index]
    elif len(temp)>120 :
        temp = re.sub(ur"([，,])[^,，]*$",r"", temp)
    temp = temp.strip()
    return temp

    # index = "temp".find(" ")
    # if index > 5:
    #     temp = temp[:index]
    # else:
    #     temp = re.sub(ur"\(.?\)","", temp)
    #     temp = re.sub(ur"([。！？])[^。！？]*$",r"\1", temp).strip()
    # return temp
