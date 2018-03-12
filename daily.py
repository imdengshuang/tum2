# -*- coding:utf-8 -*-
from one import *

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
db = dbm.DbManager()


def main():
    """
    每日追加更新模式:获取今日未更新过的博客的博文,如果发现已经获取过的博文,终止更新
    python3 daily.py 10 更新10个,今日未更新的博客
    :return:
    """
    args = sys.argv
    # update('mtypepotato')
    if len(args) != 2:
        stop_and_log('error', '参数错误 args:%s' % str(args))
        return False
    limit = int(args[1])
    # 获取当前时间
    timestamp = time.mktime(
        time.strptime(time.strftime("%Y-%m-%d 00:00:00", time.localtime(int(time.time()))), "%Y-%m-%d %H:%M:%S"))

    time_line = int(timestamp)

    # 获取待更新博客列表
    session = db.get_session()
    blog_list = session.query(model.Blog).filter(model.Blog.status == 1, model.Blog.update_time < time_line).order_by(
        model.Blog.update_time.desc()).limit(limit).all()
    # print(blog_list)
    # 循环更新博客
    for blog in blog_list:
        # print(blog.name)
        blog_name = blog.name
        res_up = update_blog(blog_name)
        if res_up:
            print('%s 更新完毕' % blog_name)
        else:
            print('%s 更新失败' % blog_name)


def update_blog(blog_name):
    """
    追加更新指定博客
    :param blog_name:
    :return:
    """
    exist = db.find(model.Blog, model.Blog.name == blog_name)
    if not exist:
        stop_and_log('error', '%s 不存在' % blog_name)
        return False
    if exist.status == 0:
        stop_and_log('error', '%s 已停用' % blog_name)
        return False
    update(blog_name, False, exist.update_time)
    exist.update_time = int(time.time())
    session = db.get_session()
    session.add(exist)
    session.commit()
    return True


if __name__ == '__main__':
    main()
    # blog_name = 'xxxhotpics'
    # catch_data(blog_name, 100, 11, False, 0)
