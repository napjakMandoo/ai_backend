import os

import pymysql
from dotenv import load_dotenv


class MysqlUtil:
    def __init__(self):
        load_dotenv()
        self.host = os.getenv("DATABASE_HOST")
        self.port = os.getenv("DATABASE_PORT")
        self.user = os.getenv("DATABASE_USER")
        self.password = os.getenv("DATABASE_PASSWORD")
        self.db = os.getenv("DATABASE_DATABASE")
        self.char_set = os.getenv("DATABASE_CHARSET")

    def get_connection(self):
        connect = pymysql.connect(host=self.host, port=int(self.port), user=self.user, password=self.password, db=self.db, charset=self.char_set, )
        return connect

