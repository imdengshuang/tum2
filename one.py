# -*- coding:utf-8 -*-
import http
import sys
import os
import datetime
import json
import time
import socket
from logging import getLogger, INFO, Formatter
from urllib import request
from pyquery import PyQuery as pyq

from cloghandler import ConcurrentRotatingFileHandler

# 自有模块
import model.model as model
import model.db as dbm

if not os.path.isdir('log'):
    os.mkdir('log')
log_file_name = '%s-%s.log' % (os.path.basename(__file__).replace('.py', ''), datetime.date.today())
log_full_file_name = os.path.join('log', log_file_name)

log = getLogger()
rotateHandler = ConcurrentRotatingFileHandler(log_full_file_name, "a", 512 * 1024, 0, 'utf-8')

datefmt_str = '%Y-%m-%d %H:%M:%S'
format_str = "[%(asctime)s - %(levelname)s - %(filename)s - LINE:%(lineno)d] %(message)s"
formatter = Formatter(format_str, datefmt_str)
rotateHandler.setFormatter(formatter)
log.addHandler(rotateHandler)
log.setLevel(INFO)
db = dbm.DbManager('tumblr2')


def main():
    """
    处理命令行参数,分发操作
    python3 one.py xxx all 强制更新
    python3 one.py xxx new 追加更新
    :return:
    """
    args = sys.argv
    enable_action = ['all', 'new']

    if len(args) != 3:
        stop_and_log('error', '参数错误 args:%s' % str(args))
        return False
    blog_name = str(args[1])
    action = args[2]
    if enable_action.count(action) == 0:
        stop_and_log('参数错误,允许的参数:%s' % enable_action)
        return False
    exist = db.find(model.Blog, model.Blog.name == blog_name)
    if not exist:
        stop_and_log('error', '%s 不存在' % blog_name)
        return False
    if exist.status == 0:
        stop_and_log('error', '%s 已停用' % blog_name)
        return False
    if action == 'all':
        update(blog_name, True)
    elif action == 'new':
        update(blog_name, False, exist.update_time)
    exist.update_time = int(time.time())
    db.add_data(exist)


def update(blog_name, is_all=False, time_line=0):
    """
    更新指定博客
    :param blog_name:博客名称
    :param is_all:是否更新全部
    :param time_line:追加更新的截止时间戳
    """
    # print(blog_name)
    if is_all:
        # 更新全部
        log.info('开始更新 %s [更新全部]' % blog_name)
        catch_data(blog_name)
    else:
        # 追加更新
        log.info('开始更新 %s [追加更新]' % blog_name)
        catch_data(blog_name, 20, 1, False, time_line)


def catch_data(blog_name, perpage=20, page=1, is_all=True, time_line=0):
    """
    抓取数据,递归方法
    :param blog_name: 博客名称
    :param perpage: 每页数据
    :param page: 页数
    :param is_all: 是否获取全部,为否时,发现存在数据则停止
    :param time_line:追加更新的截止时间戳
    :return:
    """
    try:
        post_list = catch_html(blog_name, perpage, page, 1, is_all, time_line)
    except Exception as e:
        stop_and_log('error', '[%s 第%s页 获取失败] %s' % (blog_name, page, str(e)))
        return False
    # 博文信息入库
    if post_list:
        insert_posts(post_list)
        return catch_data(blog_name, perpage, page + 1, is_all, time_line)
    else:
        # 博文获取为空,停止递归
        log.info('%s 第%s页数据 获取博文为空,停止' % (blog_name, page))
        return False


# 抓取HTML
def catch_html(blog_name, perpage=20, page=1, try_times=1, is_all=False, time_line=0):
    """
    抓取博客数据
    :param blog_name: 博客名
    :param perpage: 每页数据
    :param page: 页数
    :param try_times:尝试次数
    :param is_all:是否更新全部
    :param time_line:更新的截止时间戳
    :return: mixed
    """
    log.info('开始抓取 %s 第%s页数据' % (blog_name, page))
    start = (page - 1) * perpage
    url = 'https://%s.tumblr.com/api/read/json?start=%s&num=%s' % (
        blog_name, start, perpage)
    # print(url)
    # 设置代理
    socket.setdefaulttimeout(5)
    proxy = "https://127.0.0.1:1087"
    proxy_handler = request.ProxyHandler({'https': proxy})
    opener = request.build_opener(proxy_handler)
    request.install_opener(opener)

    try:
        content = request.urlopen(url).read().decode('UTF-8')
    except (http.client.IncompleteRead, socket.timeout) as ie:
        if try_times > 3:
            stop_and_log('error', '[%s 第%s页 获取失败] url:%s; 尝试次数过多' % (blog_name, page, url))
            return False
        else:
            log.info('url:%s 出错:%s 获取不完整,重试' % (url, str(ie)))
            return catch_html(blog_name, perpage, page, try_times + 1, is_all, time_line)
    except Exception as e:
        stop_and_log('error', '[%s 第%s页 获取失败] url:%s; %s' % (blog_name, page, url, str(e)))
        return False
    log.info('%s 第%s页数据 开始整理数据格式' % (blog_name, page))
    # 修整数据格式
    try:
        content = content[22:len(content) - 2].replace("{'", '{"').replace("'}", '"}')
        content = content.replace(",'", ',"')
    except Exception as e:
        stop_and_log('error', '[%s 第%s页 修整数据格式出错] url:%s; %s' % (blog_name, page, url, str(e)))
        return False

    # 转换为数据字典
    try:
        json_data = json.loads(content)
    except Exception as e:
        stop_and_log('error', '[%s 第%s页 解析json数据失败] url:%s; %s;%s' % (blog_name, page, url, str(e), content))
        return False
    # print(jsonData)
    posts = json_data['posts']
    post_list = []
    # 遍历获取博文信息
    for post in posts:
        post_type = post['type']
        unix_timestamp = post['unix-timestamp']
        # print(post['id'])
        post_id = post['id']
        if not is_all and unix_timestamp < time_line:
            log.info(
                '当前博文发布时间:%s 更新截止时间:%s 时间线之前的数据,跳过' % (
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(unix_timestamp)),
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_line))))
            continue
        item = {'id': post_id, 'blog_name': blog_name, 'post_type': post_type, 'unix_timestamp': unix_timestamp,
                'img': '', 'video': ''}
        # print(item)
        # continue
        if post_type == 'regular':
            pass
        elif post_type == 'photo':
            res_img = analysis_img(post)
            if not res_img:
                log.info('获取图片都失败: %s' % json.dumps(post))

            item['img'] = res_img
        elif post_type == 'video':
            res_video = analysis_video(post)
            if not res_video:
                log.info('获取视频都失败: %s' % json.dumps(post))
            item['video'] = res_video

        # print(item)
        post_list.append(item)
        # return False
    return post_list


def analysis_video(post):
    """
    从json格式的post解析出视频url
    :param post:json格式的post数据
    :return:失败则返回False,成功返回url
    """
    try:
        video_player = post['video-player']
        doc = pyq(video_player)
        cts = doc('source')
        for i in cts:
            a = pyq(i)
            url = a.attr('src')
            # print(url)
            return url
        return False
    except Exception as e:
        # raise e
        # print(e)
        log.info('获取video失败 e:%s' % str(e))
        return False


def analysis_img(post):
    """
    从json格式的post解析出图片url
    :param post:json格式的post数据
    :return:失败则返回False,成功返回url
    """
    try:
        img = post['photo-url-1280']
        # print(img)
        return img
    except Exception as e:
        # raise e
        # print(e)
        log.info('获取img失败 e:%s' % str(e))
        return False


def stop_and_log(level, message):
    """
    输出错误信息到日志和控制台
    :param level:错误日志等级
    :param message:错误信息
    """
    print(message)
    if level == 'debug':
        log.debug(message)
    elif level == 'error':
        log.error(message)


def insert_posts(post_list):
    """
    将博文列表插入到数据中
    :param post_list: 博文列表
    """
    has_exist = False
    for post in post_list:
        if post['post_type'] == 'photo':
            source_url = post['img']
            post_type = 0
        elif post['post_type'] == 'video':
            source_url = post['video']
            post_type = 1
        else:
            continue
        exist = db.find(model.Item, model.Item.url == source_url)
        if not exist:
            data = model.Item(url=source_url, blog_name=post['blog_name'], type=post_type, create_time=int(time.time()),
                              post_time=post['unix_timestamp'], post_id=post['id'])
            db.add_data(data)
        else:
            log.info('博文已存在 [%s] data:%s' % (str(exist), json.dumps(post)))
            has_exist = True

    return has_exist


if __name__ == '__main__':
    main()
