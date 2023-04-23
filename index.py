# -*- coding: utf-8 -*-
from random import randint
from urllib.parse import unquote,quote,parse_qs
import requests
import urllib.request
import json
import time as t
import datetime
import zlib
import re
import xml.etree.ElementTree as ET
from requests_html import HTMLSession
from zlib import decompress


# import oss2

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE',
}

iqiyiplayer = {
    "User-Agent":"Qiyi List Client PC 7.2.102.1343"
}

SESSION = HTMLSession()


def get_response_iqiyi(url):
    req = urllib.request.Request(url)
    req.add_header("User-Agent",
                   "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36")
    response = urllib.request.urlopen(req).read()
    return response


def get_response(url):
    response = requests.get(url)
    response.encoding = 'utf-8'
    return response.text


def judgeIllegalChar(str):
    illegal = False  # 标志是否有非法XML字符
    for char in ["<", ">", "&", "\u0000", "\b"]:
        if char in str:
            illegal = True
            break
    return illegal


def make_response_head():
    return '<?xml version="1.0" encoding="UTF-8"?>\n<i>\n'


def make_response_foot():
    return '</i>'


def make_response_body(timepoint, content, ct=1, size=20, color=16777215,
                       unixtime=int(t.mktime(datetime.datetime.now().timetuple())), uid=0):
    return '\t<d p="{},{},{},{},{},0,{},26732601000067074">{}</d>\n'.format(timepoint, ct, size, color, unixtime, uid,
                                                                            content)
    # 第一个参数是弹幕出现的时间 以秒数为单位。
    # 第二个参数是弹幕的模式1..3 滚动弹幕 4底端弹幕 5顶端弹幕 6.逆向弹幕 7精准定位 8高级弹幕
    # 第三个参数是字号， 12非常小,16特小,18小,25中,36大,45很大,64特别大
    # 第四个参数是字体的颜色 以HTML颜色的十位数为准
    # 第五个参数是Unix格式的时间戳。基准时间为 1970-1-1 08:00:00
    # 第六个参数是弹幕池 0普通池 1字幕池 2特殊池 【目前特殊池为高级弹幕专用】
    # 第七个参数是发送者的ID，用于“屏蔽此弹幕的发送者”功能
    # 第八个参数是弹幕在弹幕数据库中rowID 用于“历史弹幕”功能。


def mgtv(url):
    cid = url.split('/')[4]
    vid = url.split('/')[5].split('?')[0].strip('.html')
    title = re.search(r'partName:"(.*?)",', get_response(url))
    if title is not None:
        title = title.group(1)
    else:
        title = 'Unknow'
    contents = set()
    ret = make_response_head()

    time = 0
    total = 0  # 弹幕总数
    cnt = 0  # 筛选弹幕数
    while True:
        result = get_response('https://galaxy.bz.mgtv.com/rdbarrage?vid=' + vid + '&cid=' + cid + '&time=' + str(time))
        danmu = json.loads(result)
        if danmu['data']['items'] == None:
            break
        for j in danmu['data']['items']:
            total += 1
            if judgeIllegalChar(j['content']):
                continue
            timepoint = j['time'] / 1000  # 弹幕发送时间
            uid = j['uid']  # 发送者uid
            content = j['content']  # 弹幕内容
            if content not in contents:
                cnt += 1
                contents.add(content)
                ret += make_response_body(timepoint=timepoint, content=content, uid=uid)
        time = danmu['data']['next']
    ret += make_response_foot()
    print("Download {} danmakus, Select {} danmakus\nfinish.".format(total, cnt))
    return [title, ret]


def tencentvideo(url):
    # url = 'https://v.qq.com/x/cover/a8oeend1e9gfdzs/f0031nbupkq.html' # 视频的url
    video_info = json.loads(
        str([s for s in get_response(url).split('\n') if 'VIDEO_INFO' in str(s)]).strip('[\'var VIDEO_INFO = ').strip(
            '\']'))
    duration = video_info['duration']
    title = video_info['title']
    vid = video_info['vid']
    targetid = json.loads(get_response('http://bullet.video.qq.com/fcgi-bin/target/regist?otype=json&vid=' + vid).strip(
        'QZOutputJson=').strip(';'))['targetid']
    contents = set()
    ret = make_response_head()

    total = 0  # 弹幕总数
    cnt = 0  # 筛选弹幕数
    for i in range(int(duration) // 30 + 1):
        timestamp = i * 30
        danmu = json.loads(
            get_response('http://mfm.video.qq.com/danmu?timestamp=' + str(timestamp) + '&target_id=' + targetid),
            strict=False)
        for j in danmu['comments']:
            total += 1
            if judgeIllegalChar(j['content']):
                continue
            timepoint = j['timepoint']  # 弹幕发送时间
            ct = 1  # 弹幕样式
            size = 20  # 字体大小
            # 获取颜色
            if "color" in j["content_style"]:
                content_style = json.loads(j["content_style"])
                color = int(content_style["color"], 16)
            else:
                color = 16777215
            unixtime = int(t.mktime(datetime.datetime.now().timetuple()))  # unix时间戳
            content = j['content']  # 弹幕内容
            if content not in contents:
                cnt += 1
                contents.add(content)
                ret += '\t<d p="{},{},{},{},{},0,0,26732601000067074">{}</d>\n'.format(timepoint, ct, size, color,
                                                                                       unixtime, content)
    ret += make_response_foot()
    print("Download {} danmakus, Select {} danmakus\nfinish.".format(total, cnt))
    return [title, ret]


def youku(url):
    # url = 'https://v.youku.com/v_show/(%id%).html'  # 视频的url'
    res = get_response(url)
    title = re.search(r'<title>(.*)</title>', res).group(1).split('—')[0]
    iid = re.search(r'videoId: \'(\d*)\'', res).group(1)
    duration = float(re.search(r'seconds: \'(.*)\',', res).group(1))
    contents = set()

    total = 0  # 弹幕总数
    cnt = 0  # 筛选弹幕数
    ret = make_response_head()
    for mat in range(int(duration) // 60 + 1):
        # req = urllib.request.Request('https://service.danmu.youku.com/list?mat=' + str(mat) + '&ct=1001&iid=' + iid)
        # req.add_header("User-Agent",
        #                "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36")
        # response = urllib.request.urlopen(req)
        response = get_response('https://service.danmu.youku.com/list?mat=' + str(mat) + '&ct=1001&iid=' + iid)
        danmu = json.loads(response)
        for i in range(len(danmu["result"])):
            total += 1
            if judgeIllegalChar(danmu["result"][i]["content"]):
                continue
            playat = danmu["result"][i]["playat"] / 1000  # 弹幕发送时间
            # 获取颜色
            if "color" in danmu["result"][i]["propertis"]:
                propertis = json.loads(danmu["result"][i]["propertis"])
                color = propertis["color"]
            else:
                color = 16777215
            content = danmu["result"][i]["content"]  # 弹幕内容
            if content not in contents:
                contents.add(content)
                cnt += 1
                ret += make_response_body(timepoint=playat, color=color, content=content)
    ret += make_response_foot()
    print("Download {} danmakus, Select {} danmakus\nfinish.".format(total, cnt))
    return [title, ret]


def iqiyi(url):
    # url = 'https://www.iqiyi.com/(%id%).html'  # 视频的url'
    # ret = get_response(url)
    ret = SESSION.get(url)

    dataList = []

    re_str = 'window.Q.PageInfo.playPageInfo=({.+?\};)'
    stats_re = re.compile(re_str, re.MULTILINE | re.DOTALL)
    htmlText = ret.html.text
    for match in stats_re.findall(htmlText):
        jsonStr = match[:-1]
        dataList.append(json.loads(jsonStr))

    page_info = dataList[0]
    duration_str = page_info['duration'].split(':')
    duration = 0
    for i in range(len(duration_str) - 1):
        duration = (duration + int(duration_str[i])) * 60
    duration = duration + int(duration_str[-1])
    title = page_info['name']
    albumid = page_info['albumId']
    tvid = page_info['tvId']
    categoryid = page_info['cid']
    page = duration // (60 * 5) + 1
    contents = set()

    total = 0  # 弹幕总数
    cnt = 0  # 筛选弹幕数
    ret = make_response_head()
    for i in range(duration // (60 * 5) + 1):
        dec = zlib.decompressobj(32 + zlib.MAX_WBITS)
        b = dec.decompress(get_response_iqiyi(
            'http://cmts.iqiyi.com/bullet/' + str(tvid)[-4:-2] + '/' + str(tvid)[-2:] + '/' + str(tvid) + '_300_' + str(
                i + 1) + '.z?rn=0.' + ''.join(["%s" % randint(0, 9) for num in range(0,
                                                                                     16)]) + '&business=danmu&is_iqiyi=true&is_video_page=true&tvid=' + str(
                tvid) + '&albumid=' + str(albumid) + '&categoryid=' + str(categoryid) + '&qypid=01010021010000000000'))
        root = ET.fromstring(b.decode("utf-8"))
        for bulletInfo in root.iter('bulletInfo'):
            total += 1
            timepoint = bulletInfo[3].text  # 弹幕发送时间
            color = int(bulletInfo[5].text, 16)  # 颜色
            content = bulletInfo[1].text  # 弹幕内容
            size = bulletInfo[4].text
            if content not in contents:
                cnt += 1
                contents.add(content)
                ret += make_response_body(timepoint=timepoint, color=color, content=content, size=size)
    ret += make_response_foot()
    print("Download {} danmakus, Select {} danmakus\nfinish.".format(total, cnt))
    return [title, ret]


def iqiyi_by_vinfo(vinfo):
    # url = 'https://www.iqiyi.com/(%id%).html'  # 视频的url'

    duration_str = page_info['duration'].split(':')
    duration = 0
    for i in range(len(duration_str) - 1):
        duration = (duration + int(duration_str[i])) * 60
    duration = duration + int(duration_str[-1])
    title = page_info['tvName']
    albumid = page_info['albumId']
    tvid = page_info['tvId']
    categoryid = page_info['cid']
    page = duration // (60 * 5) + 1
    contents = set()

    total = 0  # 弹幕总数
    cnt = 0  # 筛选弹幕数
    ret = make_response_head()
    for i in range(duration // (60 * 5) + 1):
        dec = zlib.decompressobj(32 + zlib.MAX_WBITS)
        b = dec.decompress(get_response_iqiyi(
            'http://cmts.iqiyi.com/bullet/' + str(tvid)[-4:-2] + '/' + str(tvid)[-2:] + '/' + str(tvid) + '_300_' + str(
                i + 1) + '.z?rn=0.' + ''.join(["%s" % randint(0, 9) for num in range(0,
                                                                                     16)]) + '&business=danmu&is_iqiyi=true&is_video_page=true&tvid=' + str(
                tvid) + '&albumid=' + str(albumid) + '&categoryid=' + str(categoryid) + '&qypid=01010021010000000000'))
        root = ET.fromstring(b.decode("utf-8"))
        for bulletInfo in root.iter('bulletInfo'):
            total += 1
            timepoint = bulletInfo[3].text  # 弹幕发送时间
            color = int(bulletInfo[5].text, 16)  # 颜色
            content = bulletInfo[1].text  # 弹幕内容
            size = bulletInfo[4].text
            if content not in contents:
                cnt += 1
                contents.add(content)
                ret += make_response_body(timepoint=timepoint, color=color, content=content, size=size)
    ret += make_response_foot()
    print("Download {} danmakus, Select {} danmakus\nfinish.".format(total, cnt))
    return [title, ret]


def get_vinfos_by_alumnId(albumId, locale="zh_cn"):
    api_url = "http://cache.video.iqiyi.com/avlist/{}/1/".format(albumId)
    if locale != "zh_cn":
        api_url += "?locale=" + locale
    try:
        response = SESSION.get(api_url)
        
    except Exception as e:
        print("get_vinfos requests error info -->", e)
        return None
    data = json.loads(response.text[len("var videoListC="):])
    try:
        vlist = data["data"]["vlist"]
    except Exception as e:
        print("get_vinfos load vlist error info -->", e)
        return None
    vinfos = [{'shortTitle': v["shortTitle"], "timeLength": v["timeLength"], "id": v["id"], "url": v["vurl"]} for v in vlist]
    return vinfos


# def save2oss(title, xml, download):
#     url = "XML/" + title + ".xml"
#     auth = oss2.Auth('******', '******')
#     endpoint_internal = 'oss-cn-******-internal.aliyuncs.com'
#     endpoint = 'oss-cn-******.aliyuncs.com'
#     bucketName = '****'
#     bucket = oss2.Bucket(auth, endpoint, bucketName)
#     headers = {}
#     if (download):
#         headers['Content-Type']='application/force-download'
#     else:
#         headers['Content-Type']='application/xml'

#     result = bucket.put_object(url, xml,headers=headers)
#     print('Upload URL:{}\tHTTP status: {}'.format(url, result.status))
#     #bucket = oss2.Bucket(auth, endpoint, bucketName)
#     return unquote(bucket.sign_url('GET', url, 120),'utf-8')


def bilibili(url):
    text = get_response(url)
    keyStr = re.findall(r'"cid":[\d]*', text)  # B站有两种寻址方式，第二种多一些
    if not keyStr:  # 若列表为空，则等于“False”
        keyStr = re.findall(r'cid=[\d]*', text)
        key = eval(keyStr[0].split('=')[1])
    else:
        key = eval(keyStr[0].split(':')[1])
    commentUrl = 'https://comment.bilibili.com/' + str(key) + '.xml'  # 弹幕存储地址
    return commentUrl


def build_response(url,download):
    if url.find('mgtv.com') >= 0:
        [title, ret] = mgtv(url)
    elif url.find('qq.com') >= 0:
        [title, ret] = tencentvideo(url)
    elif url.find('youku.com') >= 0:
        [title, ret] = youku(url)
    elif url.find('iqiyi.com') >= 0:
        [title, ret] = iqiyi(url)
    elif url.find('bilibili.com') >= 0:
        return bilibili(url)
    else:
        return None
    
    return ret
    # return save2oss(title, ret, download)


def handler(environ, start_response):
    if 'QUERY_STRING' not in environ:
        status = '200 OK'
        response_headers = [('Content-type', 'text/html; charset=UTF-8')]
        with open("index.html", "r", encoding="utf-8") as f:
            ret = f.read()
    else:
        query_string = environ['QUERY_STRING']
        params = parse_qs(query_string)
        download = params.get('download',['off'])[0]
        download = (download == 'on')
        url = unquote(params['url'][0], 'utf-8')
        returl = build_response(url,download)
        if returl is not None:
            status = '302 Found'
            response_headers = [('Location', quote(returl,safe='/:?&='))]
            ret = ''
        else:
            status = '200 OK'
            response_headers = [('Content-type', 'text/html; charset=UTF-8')]
            ret = "不支持的视频网址"
    start_response(status, response_headers)
    return [ret.encode('utf8')]


def get_danmu_by_tvid(tvid, title, duration):
    # http://cmts.iqiyi.com/bullet/41/00/10793494100_300_3.z
    if tvid.__class__ == int:
        tvid = str(tvid)
    api_url = "http://cmts.iqiyi.com/bullet/{}/{}/{}_{}_{}.z"
    timestamp = 300
    index = 0
    max_index = duration // timestamp + 1
    comments = []
    contents = set()
    while index < max_index:
        dec = zlib.decompressobj(32 + zlib.MAX_WBITS)
        res_content = requests.get(url, headers=iqiyiplayer).content
        raw_xml = decompress(bytearray(res_content), 15+32).decode('utf-8')
        root = ET.fromstring(b.decode("utf-8"))
        for bulletInfo in root.iter('bulletInfo'):
            total += 1
            timepoint = bulletInfo[3].text  # 弹幕发送时间
            color = int(bulletInfo[5].text, 16)  # 颜色
            content = bulletInfo[1].text  # 弹幕内容
            size = bulletInfo[4].text
            if content not in contents:
                cnt += 1
                contents.add(content)
                ret += make_response_body(timepoint=timepoint, color=color, content=content, size=size)
    ret += make_response_foot()
    print("Download {} danmakus, Select {} danmakus\nfinish.".format(total, cnt))
    return [title, ret]


if __name__ == '__main__':
    url = input('请输入要下载弹幕的视频网址：')
    
    response = SESSION.get(url)
    a = 1
    dataList = []

    re_str = 'window.Q.PageInfo.playPageInfo=({.+?\};)'
    stats_re = re.compile(re_str, re.MULTILINE | re.DOTALL)
    htmlText = response.html.text
    for match in stats_re.findall(htmlText):
        jsonStr = match[:-1]
        dataList.append(json.loads(jsonStr))

    media_data = dataList[0]
    tvId = media_data['tvId']
    albumId = media_data['albumId']
    channelId = media_data['channelId']
    vid = media_data['vid']
    album_name = media_data['albumName']

    vinfos = get_vinfos_by_alumnId(albumId)

    files = []
    i = 0
    for vinfo in vinfos:
        if(i == 2): break
        i = i +1
        [title, ret] = iqiyi(vinfo['url'])
        files.append({"title": title, "file": ret})
    for file in files:
        with open(file["title"] + ".xml", "w") as f:
            f.write(file['file'])

    
        
    # for vinfo in vinfos:

   # build_response(url, True)