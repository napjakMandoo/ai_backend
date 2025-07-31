import uuid
import logging

from src.ai.preprocessing.db.bank.MysqlUtil import MysqlUtil

class BankRepository:

    def __init__(self):
        self.mysqlUtil = MysqlUtil()
        self.logger = logging.getLogger(__name__)

    def save_bank(self):
        self.logger.info("은행 데이터 삽입 시작")

        connection = None
        cursor = None
        try:
            connection = self.mysqlUtil.get_connection()
            cursor = connection.cursor()
            datas = self.mysqlUtil.get_bank_data()

            cursor.execute("select bank_name from bank")
            existing_banks = {row[0] for row in cursor.fetchall()}

            for bank_name, bank_path in datas:

                if bank_name in existing_banks:
                    self.logger.info(f"은행 '{bank_name}' 이미 존재하여 건너뜀")
                    continue

                bank_uuid = uuid.uuid4()
                with open(bank_path, "rb") as f:
                    logo_bytes = f.read()

                cursor.execute("insert into bank(bank_uuid ,bank_name, bank_logo) values(%s ,%s, %s)", (bank_uuid.bytes, bank_name, logo_bytes))

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