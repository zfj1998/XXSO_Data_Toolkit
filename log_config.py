import os

# log文件的全路径
logfile_dir = os.path.dirname(os.path.abspath(__file__))  # log文件的目录
logfile_dir = os.path.join(logfile_dir, 'logs')
logfile_name = 'program.log'  # log文件名

if not os.path.exists(logfile_dir):
    os.makedirs(logfile_dir)
LOGFILE_PATH = os.path.join(logfile_dir, logfile_name)

# 2、强调：其中的%(name)s为getlogger时指定的名字
STANDARD_FORMAT = '[%(asctime)s][%(threadName)s:%(thread)d][task_id:%(name)s][%(filename)s:%(lineno)d][%(levelname)s][%(message)s]'
SIMPLE_FORMAT = '[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d]%(message)s'
TEST_FORMAT = '%(asctime)s  %(message)s'

# 3、日志配置字典：第一层的key值不能变，第二层的key值可以自定义
LOGGING_DIC = {
    # 版本
    'version': 1,

    'disable_existing_loggers': False,

    # 自己指定的多个日志格式
    'formatters': {
        'standard': {
            'format': STANDARD_FORMAT
        },
        'simple': {
            'format': SIMPLE_FORMAT
        },
        'test': {
            'format': TEST_FORMAT
        },
    },

    'filters': {},

    # 日志的接收者 -- 控制日志输出位置
    'handlers': {
        # 打印到终端的日志
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',  # 打印到屏幕
            'formatter': 'simple'
        },
        # 打印到文件的日志,收集info及以上的日志
        'robin_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件 日志轮转
            'formatter': 'standard',
            'filename': LOGFILE_PATH,  # 日志文件 可写为LOGFILE_PATH
            'maxBytes': 1024*1024*5,  # 日志大小 5M
            'backupCount': 100, # 日志份数
            'encoding': 'utf-8',  # 日志文件的编码，再也不用担心中文log乱码了
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',  # 保存到文件
            'formatter': 'test',
            'filename': LOGFILE_PATH,
            'encoding': 'utf-8',
        },
    },

    # 日志的产生者 -- 产生的日志会传递给handler然后控制输出
    'loggers': {
        # logging.getLogger(__name__)拿到的logger配置
        'production': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'console_info': {
            'handlers': ['console'],  # 产生的日志丢给console
            'level': 'ERROR',  # loggers(第一层日志级别关限制)--->handlers(第二层日志级别关卡限制)
            'propagate': False,  # 默认为True，向上（更高level的logger）传递，通常设置为False即可，否则会一份日志向上层层传递
        },
        '': {
            'handlers': ['console'],  # 产生的日志丢给console
            'level': 'DEBUG',  # loggers(第一层日志级别关限制)--->handlers(第二层日志级别关卡限制)
            'propagate': False,  # 默认为True，向上（更高level的logger）传递，通常设置为False即可，否则会一份日志向上层层传递
        },
    },
}


'''用法
# 需要先导入日志配置
import settings
from logging import config,getLogger

config.dictConfig(settings.LOGGING_DIC)
# 实例化日志对象
logger1 = getLogger('aaa')

# 输出日志
logger1.info('这是info日志')
'''
