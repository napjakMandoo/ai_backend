import uuid
import logging

from src.preprocessing.db.util.MysqlUtil import MysqlUtil

class BankRepository:
    def __init__(self):
        self.mysqlUtil = MysqlUtil()
        self.logger = logging.getLogger(__name__)

    def get_bank_data(self):
        # 부산, SC, 광주, 제주, 전북, 경남, 우체국, 신한, KDB, 농협, 우리, 하나, 국민, 수협, ibk, im,
        busan = ["BNK_BUSAN", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        sc = ["SC_JEIL", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        gwangju = ["GWANGJU", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        jeju = ["JEJU", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        jeonbuk = ["JEONBUK", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        gyeongnam = ["BNK_GYEONGNAM", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        post = ["POST_OFFICE", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        sinhan = ["SHINHAN", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        kdb = ["KDB", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        nonghyup = ["NH", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        woori = ["WOORI", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        hana = ["HANA", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        kookmin = ["KB", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        suhyup = ["SH_SUHYUP", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        idk = ["IBK", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        im = ["IM_BANK", "/home/jeonggiju/hanium/ai_backend/src/static/logos/kyongnam_logo.png"]
        return [busan, sc, gwangju, jeju, jeonbuk, gyeongnam, post, sinhan, kdb, nonghyup, woori, hana, kookmin, suhyup,
                idk, im]

    def save_bank(self):
        self.logger.info("은행 데이터 삽입 시작")

        connection = None
        cursor = None
        try:
            connection = self.mysqlUtil.get_connection()
            cursor = connection.cursor()
            datas = self.get_bank_data()

            cursor.execute("select bank_name from bank")
            existing_banks = {row[0] for row in cursor.fetchall()}

            for bank_name, bank_path in datas:
                if bank_name in existing_banks:
                    self.logger.info(f"은행 '{bank_name}' 이미 존재하여 건너뜀")
                    continue

                bank_uuid = uuid.uuid4().bytes
                with open(bank_path, "rb") as f:
                    logo_bytes = f.read()

                cursor.execute("insert into bank(bank_uuid ,bank_name, bank_logo) values(%s ,%s, %s)", (bank_uuid, bank_name, logo_bytes))

                self.logger.info(f"은행 '{bank_name}' 삽입 완료")
            connection.commit()

        except Exception as e:
            self.logger.error("은행 데이터 삽입 중, db 저장 오류: %s", e)
            if connection:
                connection.rollback()
        finally:
            self.logger.info("은행 데이터 삽입 리소스 반환")
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def get_uuid_by_bank_name(self, bank_name):
        connection = self.mysqlUtil.get_connection()
        cursor = connection.cursor()

        cursor.execute("select bank_uuid from bank where bank_name=%s", bank_name)
        row = cursor.fetchone()
        if row:
            return uuid.UUID(bytes=row[0])
        else:
            return None