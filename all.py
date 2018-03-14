# -*- coding:utf-8 -*-
import http
import sys
import json
import threading
import time
import socket

from urllib import request
from urllib import error

import threadpool
from pyquery import PyQuery as pyq

# 自有模块
import model.model as model
import model.db as dbm

import mylog


def main():
    """
    处理命令行参数,分发操作
    python3 one.py xxx all 强制更新
    python3 one.py xxx new 追加更新
    :return:
    """
    args = sys.argv
    # 日志相关初始化
    log = mylog.get_log_object()
    db = dbm.DbManager()
    if len(args) == 2:
        blog_name = str(args[1])
        limit = 10
    elif len(args) == 3:
        blog_name = str(args[1])
        limit = int(args[2])
    elif len(args) == 1:
        session = db.get_session()
        one = session.query(model.Blog).filter(model.Blog.update_time == 0).order_by(model.Blog.id.asc()).first()
        blog_name = one.name
        limit = 10
    else:
        stop_and_log('error', '参数错误 args:%s' % str(args), log)
        return False

    exist = db.find(model.Blog, model.Blog.name == blog_name)
    if not exist:
        stop_and_log('error', '%s 不存在' % blog_name, log)
        return False
    if exist.status == 0:
        stop_and_log('error', '%s 已停用' % blog_name, log)
        return False

    try:
        res_up = update(blog_name, limit, log)
    except Exception as e:
        print(e)
        return False
    if res_up == 1:
        try:
            db = dbm.DbManager()
            session = db.get_session()
            exist.update_time = int(time.time())
            session.add(exist)
            session.commit()
            session.close()
        except Exception as e:
            print('%s %s' % (blog_name, str(e)))
        print('更新成功')
    elif res_up == 0:
        print('更新失败')
    elif res_up == -1:
        session = db.get_session()
        exist.update_time = int(time.time())
        exist.status = 0
        session.add(exist)
        session.commit()
        session.close()
        print('停止更新')
    else:
        print('异常 %s' % str(res_up))
    log.info('执行完毕')


def update(blog_name, thread_num=10, log=None):
    # 获取博文总数
    total = get_total_post(blog_name, log)
    if not total:
        return False
    elif total == -1:
        return -1
    db = dbm.DbManager()
    session = db.get_session()
    blog_data = session.query(model.Blog).filter(model.Blog.name == blog_name).first()
    blog_data.total_post = total
    session.add(blog_data)
    session.commit()
    session.close()
    # print(total)
    # return False
    perpage = 10
    limit = total // perpage
    # print(thread_num)
    # return False
    # 创建多线程

    # 实例化线程锁
    lock = threading.Lock()
    if thread_num > (limit + 1):
        thread_num = limit + 1

    log.info('开始执行: 启动%s个线程下载%s个博文' % (thread_num, total))
    # 创建线程池
    pool = threadpool.ThreadPool(thread_num)
    requests_list = []
    for x in range(limit + 1):
        requests_list.append(([blog_name, perpage, x + 1, lock, log, thread_num], None))
    requests_res = threadpool.makeRequests(catch_html, requests_list)
    [pool.putRequest(req) for req in requests_res]
    pool.wait()
    return True


def get_total_post(blog_name, log=None):
    # 组装连接
    url = 'https://%s.tumblr.com/api/read/json?start=%s&num=%s' % (
        blog_name, 0, 10)
    # 设置代理
    socket.setdefaulttimeout(20)
    proxy = "https://127.0.0.1:1087"
    proxy_handler = request.ProxyHandler({'https': proxy})
    opener = request.build_opener(proxy_handler)
    request.install_opener(opener)
    # log.info('开始抓取%s' % blog_name)
    # 开始获取HTML
    try:
        content = request.urlopen(url).read().decode('UTF-8')
    except (http.client.IncompleteRead, socket.timeout) as ie:
        log.info('url:%s 出错:%s 获取不完整,重试' % (url, str(ie)))
        return get_total_post(blog_name, log)
    except error.HTTPError as e:
        if hasattr(e, 'code'):
            if e.code == 404:
                stop_and_log('error', '[%s 获取失败] url:%s; %s' % (blog_name, url, str(e)), log)
                # 404 返回-1,方便停止改博客
                return -1
            else:
                log.info('url:%s 出错:%s 获取获取失败,重试' % (url, str(e)))
                return get_total_post(blog_name, log)
        else:
            log.info('url:%s 出错:%s 获取获取失败,重试' % (url, str(e)))
            return get_total_post(blog_name)
    except Exception as e:
        log.info('url:%s 出错:%s 获取获取失败,重试' % (url, str(e)))
        return get_total_post(blog_name, log)
    # 修整数据格式
    try:
        content = content[22:len(content) - 2].replace("{'", '{"').replace("'}", '"}')
        content = content.replace(",'", ',"')
    except Exception as e:
        stop_and_log('error', '[%s 修整数据格式出错] url:%s; %s' % (blog_name, url, str(e)), log)
        return False
    # 转换为数据字典
    try:
        json_data = json.loads(content)
    except Exception as e:
        stop_and_log('error', '[%s 解析json数据失败] url:%s; %s;%s' % (blog_name, url, str(e), content), log)
        return False
    post_total = json_data['posts-total']
    return post_total


# 抓取HTML
def catch_html(blog_name, perpage=20, page=1, lock=None, thread_log=None, thread_num=0):
    """
    抓取博客数据
    :param thread_num:
    :param thread_log: 
    :param lock:
    :param blog_name: 博客名
    :param perpage: 每页数据
    :param page: 页数
    :return: mixed
    """
    thread_log.info('开始抓取 %s 第%s页数据' % (blog_name, page))
    start = (page - 1) * perpage
    url = 'https://%s.tumblr.com/api/read/json?start=%s&num=%s' % (
        blog_name, start, perpage)
    # print(url)
    # 设置代理
    socket.setdefaulttimeout(20)
    proxy = "https://127.0.0.1:1087"
    proxy_handler = request.ProxyHandler({'https': proxy})
    opener = request.build_opener(proxy_handler)
    request.install_opener(opener)
    begin = time.time()
    try:
        content = request.urlopen(url).read().decode('UTF-8')
    except (http.client.IncompleteRead, socket.timeout) as ie:
        thread_log.info('url:%s 出错:%s 获取不完整,重试' % (url, str(ie)))
        return catch_html(blog_name, perpage, page, lock, thread_log, thread_num)
    except error.HTTPError as e:
        if hasattr(e, 'code'):
            if e.code == 404:
                stop_and_log('error', '[%s 第%s页 获取失败] url:%s; %s' % (blog_name, page, url, str(e)), thread_log)
                # 404 返回-1,方便停止改博客
                return -1
            else:
                thread_log.info('url:%s 出错:%s 获取获取失败,重试' % (url, str(e)))
                return catch_html(blog_name, perpage, page, lock, thread_log, thread_num)
        else:
            thread_log.info('url:%s 出错:%s 获取获取失败,重试' % (url, str(e)))
            return catch_html(blog_name, perpage, page, lock, thread_log, thread_num)
    except Exception as e:
        thread_log.info('url:%s 出错:%s 获取获取失败,重试' % (url, str(e)))
        return catch_html(blog_name, perpage, page, lock, thread_log, thread_num)
        # stop_and_log('error', '[%s 第%s页 获取失败] url:%s; %s' % (blog_name, page, url, str(e)))
        # return False
    # thread_log.info('%s 第%s页数据 开始整理数据格式' % (blog_name, page))
    # 修整数据格式
    try:
        content = content[22:len(content) - 2].replace("{'", '{"').replace("'}", '"}')
        content = content.replace(",'", ',"')
    except Exception as e:
        stop_and_log('error', '[%s 第%s页 修整数据格式出错] url:%s; %s' % (blog_name, page, url, str(e)), thread_log)
        return False

    # 转换为数据字典
    try:
        json_data = json.loads(content)
    except Exception as e:
        stop_and_log('error', '[%s 第%s页 解析json数据失败] url:%s; %s;%s' % (blog_name, page, url, str(e), content),
                     thread_log)
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
        item = {'id': post_id, 'blog_name': blog_name, 'post_type': post_type, 'unix_timestamp': unix_timestamp,
                'img': '', 'video': ''}
        # print(item)
        # continue
        if post_type == 'regular':
            pass
        elif post_type == 'photo':
            res_img = analysis_img(post, thread_log)
            if not res_img:
                thread_log.info('获取图片都失败: %s' % json.dumps(post))

            item['img'] = res_img
        elif post_type == 'video':
            res_video = analysis_video(post, thread_log)
            if not res_video:
                thread_log.info('获取视频都失败: %s' % json.dumps(post))
            item['video'] = res_video

        # print(item)
        post_list.append(item)
        # return False
    # lock.acquire()
    try:
        db = dbm.DbManager()
        session = db.get_session()
        for post in post_list:
            if post['post_type'] == 'photo':
                source_url = post['img']
                post_type = 0
            elif post['post_type'] == 'video':
                source_url = post['video']
                post_type = 1
            else:
                continue
            exist = session.query(model.Item).filter(model.Item.url == source_url).first()
            if not exist:
                data = model.Item(url=source_url, blog_name=post['blog_name'], type=post_type,
                                  create_time=int(time.time()),
                                  post_time=post['unix_timestamp'], post_id=post['id'])
                session.add(data)
                session.commit()
        session.close()
    except Exception as e:
        print(str(e))
        thread_log.info('[%s] 第%s页 插入数据库失败: %s' % (blog_name, page, str(e)))
        return catch_html(blog_name, perpage, page, lock, thread_log, thread_num)
    finally:
        # lock.release()
        pass
    end = time.time()
    thread_log.info('[%s] 第%s页处理完毕 用时%s秒' % (blog_name, page, str(int(end - begin))))
    return True


def analysis_video(post, log):
    """
    从json格式的post解析出视频url
    :param log:
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


def analysis_img(post, log):
    """
    从json格式的post解析出图片url
    :param log:
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


def stop_and_log(level, message, log):
    """
    输出错误信息到日志和控制台
    :param log:
    :param level:错误日志等级
    :param message:错误信息
    """
    print(message)
    if level == 'debug':
        log.debug(message)
    elif level == 'error':
        log.error(message)


if __name__ == '__main__':
    main()
