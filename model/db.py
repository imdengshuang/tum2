import configparser

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class DbManager(object):
    """数据连接类"""

    def __init__(self, dbname):
        super(DbManager, self).__init__()
        self.dbname = dbname
        # print(dbname)
        conf = configparser.ConfigParser()
        conf.read('./conf/config.ini')
        mysql_string = conf.get('db', 'mysql_string')
        self.engine = create_engine(
            mysql_string,
            connect_args={'charset': 'utf8'})
        DBSession = sessionmaker(bind=self.engine)
        self.session = DBSession()

    def add_data(self, data):
        try:
            self.session.add(data)
            self.session.commit()
            self.session.close()
            return True
        except Exception as e:
            print(e)
            return False

    def find(self, model, params, order_by=None):
        if order_by is None:
            return self.session.query(model).filter(params).first()
        else:
            return self.session.query(model).filter(params).order_by(order_by).first()

    def select(self, model, params, order_by=None):
        if order_by is None:
            return self.session.query(model).filter(params).all()
        else:
            return self.session.query(model).filter(params).order_by(order_by).all()

    def get_session(self):
        return self.session
