from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String
import time
from sqlalchemy import MetaData, Table


class DbManager(object):
    """docstring for DbManager"""

    def __init__(self, dbname):
        super(DbManager, self).__init__()
        self.dbname = dbname
        # print(dbname)
        self.engine = create_engine(
            'mysql+pymysql://root:root@/' + dbname + '?unix_socket=/Applications/MAMP/tmp/mysql/mysql.sock',
            connect_args={'charset': 'utf8'})
        DBSession = sessionmaker(bind=self.engine)
        self.session = DBSession()

    def add_data(self, data):
        try:
            self.session.add(data)
            self.session.commit()
            return True
        except Exception as e:
            print(e)
            return False

    def find(self, model, params):
        return self.session.query(model).filter(params).first()

    def select(self, model, params):
        return self.session.query(model).filter(params).all()
