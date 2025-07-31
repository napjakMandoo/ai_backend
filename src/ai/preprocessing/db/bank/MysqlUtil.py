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

    def get_bank_data(self):
        # 부산, SC, 광주, 제주, 전북, 경남, 우체국, 신한, KDB, 농협, 우리, 하나, 국민, 수협, IBK, IM,
        busan = ["BNK_BUSAN","/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        sc = ["SC_JEIL","/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        gwangju = ["GWANGJU","/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        jeju = ["JEJU","/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        jeonbuk = ["JEONBUK", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        gyeongnam = ["BNK_GYEONGNAM", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        post = ["POST_OFFICE",  "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        sinhan = ["SHINHAN",  "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        kdb = ["KDB",  "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        nonghyup = ["NH",  "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        woori = ["WOORI",  "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        hana = ["HANA",  "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        kookmin = ["KB", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        suhyup = ["SH_SUHYUP",  "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        idk = ["IBK",  "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        im = ["IM_BANK",  "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        return [busan, sc, gwangju, jeju, jeonbuk, gyeongnam, post, sinhan, kdb, nonghyup, woori, hana, kookmin, suhyup, idk, im]