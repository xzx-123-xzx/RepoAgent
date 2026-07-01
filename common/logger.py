import logging
import os

from common.config import Config

conf = Config()


def setup_logging(log_file=conf.LOG_FILE):
    # 创建日志目录
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    # 获取日志器
    my_logger = logging.getLogger("RepoAgent")
    # 设置日志级别
    my_logger.setLevel(logging.INFO)
    # print(f'my_logger.handlers-->{my_logger.handlers}')
    # 避免重复添加处理器
    if not my_logger.handlers:
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # 为处理器设置格式
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        # 将文件添加进处理器
        my_logger.addHandler(file_handler)
        my_logger.addHandler(console_handler)
    # 返回日志器
    return my_logger

# 初始化日志器
my_logger = setup_logging()

if __name__ == '__main__':
    my_logger.info("hello world")