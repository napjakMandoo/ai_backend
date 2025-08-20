import uuid
import logging

from src.crawler.util import BankLink
from src.shared.db.util.MysqlUtil import MysqlUtil
import dotenv
import os
class BankRepository:
    def __init__(self):
        self.mysqlUtil = MysqlUtil()
        self.logger = logging.getLogger(__name__)

    def get_bank_data(self):
        # 부산, SC, 광주, 제주, 전북, 경남, 우체국, 신한, KDB, 농협, 우리, 하나, 국민, 수협, ibk, im,
        return [
            "BNK_BUSAN", "SC_JEIL", "GWANGJU", "JEJU", "JEONBUK",
            "BNK_GYEONGNAM", "POST_OFFICE", "SHINHAN", "KDB", "NH",
            "WOORI", "HANA", "KB", "SH_SUHYUP", "IBK", "IM_BANK"
        ]

    def get_url_by_bank_name(self, bank_name):
        if bank_name == "BNK_BUSAN":
            return BankLink.BankLink.BUSAN_BANK_LINK.value
        elif bank_name == "SC_JEIL":
            return BankLink.BankLink.SC_BANK_LINK.value
        elif bank_name == "GWANGJU":
            return BankLink.BankLink.GWANGJU_BANK_LINK.value
        elif bank_name == "JEJU":
            return BankLink.BankLink.JEJU_BANK_BASE_LINK.value
        elif bank_name == "JEONBUK":
            return BankLink.BankLink.JEONBUK.value
        elif bank_name == "POST_OFFICE":
            return BankLink.BankLink.POST_BANK_LINK.value
        elif bank_name == "BNK_GYEONGNAM":
            return BankLink.BankLink.KYONGNAM_BANK_DEPOSIT_LINK.value
        elif bank_name == "SHINHAN":
            return BankLink.BankLink.SINHAN_BANK_ONLINE_LINK.value
        elif bank_name == "KDB":
            return BankLink.BankLink.KDB_LINK.value
        elif bank_name == "NH":
            return BankLink.BankLink.NH_BANK_LINK.value
        elif bank_name == "WOORI":
            return BankLink.BankLink.WOORI_BANK_BASE_LINK.value
        elif bank_name == "HANA":
            return BankLink.BankLink.HANA_BANK_LINK.value
        elif bank_name == "KB":
            return BankLink.BankLink.KB_BANK_LINK.value
        elif bank_name == "SH_SUHYUP":
            return BankLink.BankLink.SH_BANK_LINK.value
        elif bank_name == "IBK":
            return BankLink.BankLink.IBK_BANK_DEPOSIT_LINK.value
        elif bank_name == "IM_BANK":
            return "https://www.imbank.co.kr/com_ebz_fpm_main.act"

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

            for bank_name in datas:
                if bank_name in existing_banks:
                    self.logger.info(f"은행 '{bank_name}' 이미 존재하여 건너뜀")
                    continue

                bank_uuid = uuid.uuid4().bytes

                cursor.execute("insert into bank(bank_uuid ,bank_name) values(%s ,%s)", (bank_uuid, bank_name))

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