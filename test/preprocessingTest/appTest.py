from datetime import datetime
import logging
import json
import os
from logging.handlers import RotatingFileHandler
from src.shared.ai.LlmUtil import LlmUtil
from src.shared.db.bank.BankRepository import BankRepository
from src.shared.db.product.productRepository import ProductRepository
from src.shared.db.util.MysqlUtil import MysqlUtil

class App:
    def __init__(self):
        self.productRepository = ProductRepository()
        self.logger = logging.getLogger(__name__)
        self.mysqlUtil = MysqlUtil()
        self.llmUtil = LlmUtil()
        self.bankRepository = BankRepository()

    def setup_logging(self):
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f"bank_crawler_{datetime.now().strftime('%Y%m%d')}.log")

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=50 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def read_json(self, file_name):
        directory = os.getenv("JSON_TEST_PATH")

        file_path = directory + "/" + file_name + ".json"

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data

    def crawling(self, bank_name: str = ""):
        before_preprocessed_products = []

        if bank_name == "BNK_BUSAN":
            data = self.read_json("BNK_BUSAN")
            for i in data:
                before_preprocessed_products.append(i)

        elif bank_name == "SC_JEIL":
            data = self.read_json("SC_JEIL")
            for i in data:
                before_preprocessed_products.append(i)

        elif bank_name == "GWANGJU":
            data = self.read_json("GWANGJU")
            for i in data:
                before_preprocessed_products.append(i)

        elif bank_name == "JEJU":
            data = self.read_json("JEJU")
            for i in data:
                before_preprocessed_products.append(i)

        return before_preprocessed_products

    def preprocessed(self, before_preprocessed_products):
        preprocessed_products = []
        for product in before_preprocessed_products:
            json = self.llmUtil.create_preferential_json(content=product)
            preprocessed_products.append(json)
        return preprocessed_products

    def save_to_db(self, after_preprocessed_products, bank_name: str = ""):
        connection = self.mysqlUtil.get_connection()

        try:
            connection.begin()

            for product in after_preprocessed_products:
                self.productRepository.save_one_product(product_data=product, bank_name=bank_name,
                                                        connection=connection)

            products_name_set = set()

            for product in after_preprocessed_products:
                products_name_set.add(product.product_name)

            self.productRepository.check_is_deleted(bank_name=bank_name, new_products_name=products_name_set,
                                                    connection=connection)
            connection.commit()
        except Exception as e:
            self.logger.error(f"mysql 데이터 삽입 에러: {e}")
            connection.rollback()
        finally:
            connection.close()

    def month_task(self):
        start_time = datetime.now()
        bank_repository = BankRepository()
        bank_data = bank_repository.get_bank_data()
        bank_name_list = []
        for bank in bank_data:
            bank_name_list.append(bank[0])

        self.logger.info(f"테스트  진행 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        for bank_name in bank_name_list:
            self.logger.info("===== 시작=====")
            before_preprocessed_products = self.crawling(bank_name=bank_name)
            self.logger.info("=====크롤링 끝=====")

            # #######
            self.logger.info("=====전처리 시작=====")
            after_preprocessed_products = self.preprocessed(before_preprocessed_products)
            self.logger.info("=====전처리 끝=====")
            #
            # #######
            self.logger.info("=====DB에 저장 시작=====")
            self.save_to_db(after_preprocessed_products, bank_name=bank_name)
            self.logger.info("=====DB에 끝=====")

        end_time = datetime.now()
        elapsed_time = end_time - start_time
        self.logger.info(f"월 마다 진행 완료: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"총 소요 시간: {elapsed_time}")

    def start(self):
        self.logger.info("===== 애플리케이션 시작 =====")

        try:
            self.logger.info("===== 은행 데이터 저장 시작 =====")
            bank_repository = BankRepository()
            bank_repository.save_bank()
            self.logger.info("===== 은행 데이터 저장 완료 =====")

            self.logger.info("===== 기존 상품 데이터 삭제 시작 (테스트용) =====")
            self.productRepository.delete_all_product()
            self.logger.info("===== 기존 상품 데이터 삭제 완료 (테스트용) =====")

            self.month_task()

        except Exception as e:
            self.logger.error(f"애플리케이션 실행 중 오류 발생: {e}")
            raise

if __name__ == "__main__":
    app = App()
    app.setup_logging()
    app.start()