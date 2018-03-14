import os
import datetime
from logging import getLogger, INFO, Formatter
from cloghandler import ConcurrentRotatingFileHandler

def get_log_object():
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
    return log