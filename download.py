# -*- coding:utf-8 -*-
import datetime
import http
import os
import socket
import sys
import threading
import time
from logging import getLogger, INFO, Formatter
from tqdm import tqdm

import requests
import threadpool
from cloghandler import ConcurrentRotatingFileHandler

import model.db as dbm
# 自有模块
import model.model as model

finish_num = 0


def download(key, lock, log, progress, thread_num):
    """
    多线程,线程指定函数
    :param progress: 进度条对象
    :param thread_num: 进程编号
    :param key: 多个任务中的第key个,用于展示或日志
    :param lock: 锁,用于数据库的排他
    :param log: 日志对象,用于全局的日志记录
    :return:
    """
    start = time.time()
    log.info('开始下载 key:%s' % key)
    lock.acquire()
    try:
        db = dbm.DbManager()
        session = db.get_session()
        one_data = session.query(model.Item).filter(model.Item.status == 0).first()
        if one_data:
            data_id = one_data.id
            data_url = one_data.url
            data_type = one_data.type
            data_name = one_data.blog_name
            data_time = one_data.post_time
            one_data.status = 1
            db.add_data(one_data)
            log.info('获取数据完成 key: %s id: %s' % (key, str(data_id)))
        else:
            log.info('获取数据失败 key: %s' % key)
            return False
    except Exception as e:
        # raise e
        print(e)
        log.error('id: %s key: %s 发生错误: %s' % (str(one_data.id), str(key), str(e)))
        return False
    finally:
        lock.release()

    download_data = {'id': data_id, 'url': data_url, 'blog_name': data_name, 'type': data_type, 'time': data_time}
    res = download_img(download_data, 1, log, thread_num, key)
    if not res:
        db = dbm.DbManager()
        one_data = db.session.query(model.Item).filter(model.Item.id == data_id).first()
        one_data.status = 2
        db.add_data(one_data)
        log.info('下载失败 key:%s id: %s' % (key, data_id))
        return False
    else:
        db = dbm.DbManager()
        one_data = db.session.query(model.Item).filter(model.Item.id == data_id).first()
        one_data.status = 3
        db.add_data(one_data)
        end = time.time()
        log.info('下载完毕 key:%s 用时: %s秒' % (key, int(end - start)))
        # print('下载完毕 key:%s 用时: %s秒' % (key, int(end - start)))
        global finish_num
        finish_num = finish_num + 1
        # print(finish_num)
        progress.update(1)
        return True


def download_img(one_data, try_times=1, log=None, thread_num=0, key=0):
    """
    实际下载方法,递归实现多次尝试
    :param key: 多个任务中的第key个,用于展示或日志
    :param thread_num:进程编号
    :param one_data: 需要下载的数据 字典类型
    :param try_times: 尝试次数,默认为1
    :param log: 日志对象
    :return:
    """
    # 绝对路径
    target_path = '/Volumes/hhd/python_download/tum/'
    if not os.path.exists(target_path):
        os.mkdir(target_path)
    try:
        # this_dir = os.path.join(target_path, 'download_' + time.strftime("%Y-%m-%d", time.localtime()))
        this_dir = os.path.join(target_path, 'download_' + time.strftime("%Y-%m-%d", time.localtime(one_data['time'])))

        video_dir = os.path.join(this_dir, 'video')
        pic_dir = os.path.join(this_dir, 'pic')
        if one_data['type'] == 1:
            # 根据不同类型设置过期时间
            time_limit = 30
            # 视频写死扩展
            ext = '.mp4'
            new_dir = os.path.join(video_dir, one_data['blog_name'])
        else:
            # 根据不同类型设置过期时间
            time_limit = 10
            # 动态获取扩展
            ext = os.path.splitext(one_data['url'])[1]
            new_dir = os.path.join(pic_dir, one_data['blog_name'])

        if not os.path.exists(new_dir):
            # 目录自动创建
            os.makedirs(new_dir)
        # 组装文件名称
        new_filename = os.path.join(new_dir, str(one_data['id']) + ext)
        # 获取开始下载时间

        url = one_data['url']

        proxies = {"http": "http://127.0.0.1:1087", "https": "https://127.0.0.1:1087", }
        r = requests.get(url, proxies=proxies, stream=True, timeout=time_limit)
        size = int(r.headers['Content-Length']) // 1024
        try:
            with open(new_filename, 'wb') as f:
                for data in tqdm(iterable=r.iter_content(1024), total=size, unit='k', desc='%d' % (key % thread_num),
                                 position=(key % thread_num + 1)):
                    f.write(data)
        except (http.client.IncompleteRead, socket.timeout) as ie:
            # 下载超时或不完整则重试
            if try_times > 3:
                log.error('id: %s 尝试次数过多 url:%s' % (one_data['id'], one_data['url']))
                return False
            else:
                log.info('id: %s 获取不为完整,重试: %s' % (one_data['id'], str(ie)))
                return download_img(one_data, try_times + 1, log, thread_num, key)

        return True
    except Exception as e:
        print(e)
        print(one_data['url'])
        return False


def main():
    """
    多线程博文下载:采用多线程下载博文,博文根据博客名分文件夹.再根据发布日期分文件夹
    python3 download.py 1000 10 启动10个线程下载1000个博文
    """
    args = sys.argv
    if len(args) == 2:
        limit = int(args[1])
        thread_num = 8
    elif len(args) == 3:
        limit = int(args[1])
        thread_num = int(args[2])
    else:
        limit = 1
        thread_num = 1
    begin = time.time()

    # 日志相关初始化
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

    log.info('开始执行: 启动%s个线程下载%s个博文' % (thread_num, limit))
    # 实例化线程锁
    lock = threading.Lock()
    # 创建线程池
    pool = threadpool.ThreadPool(thread_num)
    requests_list = []
    progress = tqdm(total=limit, desc='total')
    for x in range(limit):
        requests_list.append(([x, lock, log, progress, thread_num], None))
    requests_res = threadpool.makeRequests(download, requests_list)
    [pool.putRequest(req) for req in requests_res]
    pool.wait()


def fmt_time(sec):
    if 60 <= sec <= 3600:
        return '%d分%d秒' % (sec / 60, sec % 60)
    elif sec < 60:
        return '%d秒' % sec
    elif sec > 3600:
        return '%d小时%d分%d秒' % (sec / 3600, sec % 3600 / 60, sec % 3600 % 60)


if __name__ == '__main__':
    main()
