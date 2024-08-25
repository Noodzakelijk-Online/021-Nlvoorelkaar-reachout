import logging
import os


class LoggingManager:
    def __init__(self, log_folder_name="logs"):
        self.log_folder_name = log_folder_name

    def config(self):
        if not os.path.exists(self.log_folder_name):
            os.makedirs(self.log_folder_name)

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        info_handler = logging.FileHandler(f'{self.log_folder_name}/info.log')
        info_handler.setLevel(logging.INFO)

        error_handler = logging.FileHandler(f'{self.log_folder_name}/error.log')
        error_handler.setLevel(logging.ERROR)

        formatter = logging.Formatter('%(asctime)s - %(message)s')
        info_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)

        logger.addHandler(info_handler)
        logger.addHandler(error_handler)
