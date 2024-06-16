import multiprocessing
import os
import time
import unittest

from app.core.logger import logger_process, get_logger


class TestNonBlockingLogging(unittest.TestCase):
    def setUp(self):
        self.log_queue = multiprocessing.Queue()
        self.log_file = 'test_application.log'
        self.log_process = multiprocessing.Process(target=logger_process, args=(self.log_queue, self.log_file))
        self.log_process.start()
        self.logger = get_logger(self.log_queue)

    def tearDown(self):
        self.log_queue.put(None)
        self.log_process.join()
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        for i in range(1, 6):  # 清理轮转的日志文件
            rotated_log_file = f'{self.log_file}.{i}'
            if os.path.exists(rotated_log_file):
                os.remove(rotated_log_file)

    def test_log_message(self):
        test_message = 'This is a test log message'
        self.logger.info(test_message)
        time.sleep(1)  # 等待日志进程处理

        # 验证日志是否写入文件
        with open(self.log_file, 'r') as f:
            log_contents = f.read()
        self.assertIn(test_message, log_contents)


if __name__ == '__main__':
    unittest.main()
