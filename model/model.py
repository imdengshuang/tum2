import configparser

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
import time
from sqlalchemy import create_engine

Base = declarative_base()


class Item(Base):
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True, nullable=False)
    url = Column(String(500), comment='链接地址', nullable=False)
    blog_name = Column(String(100), comment='博客名称')
    type = Column(Integer, comment='类型,0图片,1视频', default=0)
    status = Column(Integer, comment='状态,0待下载,1下载中,2下载失败,3下载成功', default=0)
    create_time = Column(Integer, comment='添加时间', default=0)
    post_time = Column(Integer, comment='发布时间', default=0)
    post_id = Column(String(30), comment='博文唯一码')

    def __repr__(self):
        return "<User(id='%s', name='%s', status='%s',url='%s')>" % (
            self.id, self.blog_name, self.status, self.url)


class Blog(Base):
    __tablename__ = 'blog'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), comment='名称')
    status = Column(Integer, comment='状态,0停用1启用', default=1)
    create_time = Column(Integer, comment='添加时间')
    update_time = Column(Integer, comment='更新时间')

    def __repr__(self):
        create_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.create_time))
        update_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.update_time))
        return "<User(id='%s', name='%s', status='%s',create_time='%s',update_time='%s')>" % (
            self.id, self.name, self.status, create_time_str, update_time_str)


def init_db(engine):
    Base.metadata.create_all(engine)


def drop_db(engine):
    Base.metadata.drop_all(engine)


conf = configparser.ConfigParser()
conf.read('../conf/config.ini')
mysql_string = conf.get('db', 'mysql_string')
engine = create_engine(
    mysql_string,
    connect_args={'charset': 'utf8'})
init_db(engine)
