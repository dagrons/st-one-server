import json
import logging
import logging.handlers
import multiprocessing
import sys
import time
from pathlib import Path


class NonBlockingQueueHandler(logging.Handler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        try:
            self.queue.put_nowait(record)
        except Exception:
            self.handleError(record)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "filename": record.filename,
            "funcName": record.funcName,
            "lineno": record.lineno,
            "message": record.msg if isinstance(record.msg, dict) else {'message': record.msg}
        }
        return json.dumps(log_record)


def logger_process(queue, log_file):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # 创建文件处理器，大小到10MB时轮转
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JsonFormatter())

    # 创建stdout处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(JsonFormatter())

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    while True:
        try:
            record = queue.get()
            if record is None:  # 停止信号
                break
            root.handle(record)
        except Exception as e:
            print(f"Logger process error: {e}")
            break


def get_logger(queue):
    logger = logging.getLogger('non_blocking_logger')
    logger.setLevel(logging.DEBUG)
    handler = NonBlockingQueueHandler(queue)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger


if __name__ == "__main__":
    log_queue = multiprocessing.Queue()
    log_file = str(Path('.').resolve().parent.parent / 'application.log')
    print(log_file)

    log_process = multiprocessing.Process(target=logger_process, args=(log_queue, log_file))
    log_process.start()

    logger = get_logger(log_queue)

    try:
        while True:
            logger.info('This is a info log message')
            logger.error('This a warning log message')
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        log_queue.put(None)
        log_process.join()
