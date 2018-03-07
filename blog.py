# -*- coding:utf-8 -*-
import configparser
import datetime
import os
import sys
import time
import pytumblr
from logging import getLogger, INFO, Formatter

from cloghandler import ConcurrentRotatingFileHandler

import model.db as dbm
# 自有模块
import model.model as model

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


def main():
    """
    处理命令行参数,分发操作
    python3 blog.py add xxx   新增博客
    python3 blog.py show      展示所有博客
    python3 blog.py update    更新博客
    python3 blog.py show  xxx 展示指定博客
    python3 blog.py stop xxx  停用博客
    python3 blog.py start xxx 启用博客
    """
    args = sys.argv
    if len(args) == 2:
        action = str(args[1])
        if action not in ['show', 'update']:
            print('缺少参数')
        elif action == 'update':
            update_following_blog_name(1, 20)
        else:
            show()
    if len(args) == 3:
        action = str(args[1])
        blog_name = args[2]
        if action == 'add':
            add(blog_name)
        elif action == 'stop':
            stop(blog_name)
        elif action == 'start':
            start(blog_name)
        elif action == 'show':
            show(blog_name)
        else:
            print('参数异常')
            log.error('参数错误 args:%s' % str(args))
    if (len(args) < 2) or (len(args) > 3):
        print('错误参数')
        log.error('参数错误 args:%s' % str(args))


def add(blog_name):
    """
    添加博客
    :param blog_name: 博客名称
    """
    db = dbm.DbManager()
    exist = db.find(model.Blog, model.Blog.name == blog_name)
    if exist:
        print('%s已经存在' % blog_name)
    else:
        data = model.Blog(name=blog_name, create_time=int(time.time()))
        db.add_data(data)
        log.info("%s添加完成" % blog_name)
        print('添加完成')


def stop(blog_name):
    """
    停止博客
    :param blog_name:博客名称
    """
    db = dbm.DbManager()
    exist = db.find(model.Blog, model.Blog.name == blog_name)
    if exist:
        exist.status = 0
        db.add_data(exist)
        print('停止成功')
    else:
        print('%s不存在' % blog_name)


def start(blog_name):
    """
    开始博客
    :param blog_name:博客名称
    """
    db = dbm.DbManager()
    exist = db.find(model.Blog, model.Blog.name == blog_name)
    if exist:
        exist.status = 1
        db.add_data(exist)
        print('启动成功')
    else:
        print('%s不存在' % blog_name)


def show(blog_name=''):
    """
    展示博客信息
    :param blog_name:博客名称
    """
    db = dbm.DbManager()
    if blog_name == '':
        data = db.select(model.Blog, 1 == 1, model.Blog.update_time.desc())
    else:
        data = db.select(model.Blog, model.Blog.name == blog_name)
    if data:
        for one in data:
            if one.status == 1:
                status = '启动'
            else:
                status = '停止'
            update_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(one.update_time))
            print('%s [%s] 更新时间:%s' % (one.name, status, update_str))
    else:
        print('%s 不存在' % blog_name)
        log.error('%s 不存在' % blog_name)


def update_following_blog_name(page, per_page):
    """
    更新自己关注的博客,递归
    :param page:页数
    :param per_page:每页数量
    :return:
    """
    conf = configparser.ConfigParser()
    conf.read('./conf/config.ini')
    consumer_key = conf.get('pytumblr', 'consumer_key')
    consumer_secret = conf.get('pytumblr', 'consumer_secret')
    oauth_token = conf.get('pytumblr', 'oauth_token')
    oauth_secret = conf.get('pytumblr', 'oauth_secret')
    client = pytumblr.TumblrRestClient(
        consumer_key,
        consumer_secret,
        oauth_token,
        oauth_secret
    )
    # print(consumer_key)
    # return False
    offset = (page - 1) * per_page
    data = client.following(limit=per_page, offset=offset)
    # print(data)
    # return False
    try:
        if len(data['blogs']) == 0:
            return False
        else:
            for blog_data in data['blogs']:
                # print(blog_data['name'])
                add(blog_data['name'])
            return update_following_blog_name(page + 1, per_page)
    except Exception as e:
        print(e)
        print(data)
        return False


if __name__ == '__main__':
    main()
