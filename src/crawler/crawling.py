from datetime import datetime
import logging
import json
import os
from logging.handlers import RotatingFileHandler
from src.crawler.ai.LlmUtil import LlmUtil
from src.crawler.bank_crawler.post.PostBankCrawler import PostBankCrawler
from src.crawler.bank_crawler.sc.sc_bank_crawler import SCBankCleanCrawler
from src.crawler.bank_crawler.sinhan.SinHanBankCrawler import SinHanBankCrawler
from src.crawler.util.BankLink import BankLink
from src.crawler.bank_crawler.kyongnam.KyongNamBankCrawler import KyongNamBankCrawler
from src.shared.db.bank.BankRepository import BankRepository
from src.shared.db.product.productRepository import ProductRepository
from src.shared.db.util.MysqlUtil import MysqlUtil

class Crawling:
    def __init__(self):
        self.productRepository = ProductRepository()
        self.logger = logging.getLogger(__name__)
        self.mysqlUtil = MysqlUtil()
        self.llmUtil = LlmUtil()
        self.bankRepository = BankRepository()

    def setup_logging(self):
        """로깅 설정 - 파일과 콘솔 동시 출력"""
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
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,  # 최대 10개 백업 파일
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

    # def read_json(self, file_name):
    #     directory = os.getenv("JSON_RESULT_PATH")
    #
    #     file_path = directory + "/" + file_name + ".json"
    #
    #     with open(file_path, "r", encoding="utf-8") as f:
    #         data = json.load(f)
    #
    #     return data

    def crawling(self, bank_name: str = ""):
        before_preprocessed_products = []

        if bank_name == "BNK_GYEONGNAM":
            before_preprocessed_products.extend(
                KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_DEPOSIT_LINK.value).start())
        elif bank_name == "POST_OFFICE":
            before_preprocessed_products.extend(PostBankCrawler(base_url=BankLink.POST_BANK_LINK.value).start())
        elif bank_name == "SHINHAN":
            before_preprocessed_products.extend(
                SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_ONLINE_LINK.value).start())
            before_preprocessed_products.extend(
                SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_LUMP_LINK.value).start())
            before_preprocessed_products.extend(
                SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_LUMP_ROLL_LINK.value).start())
        # elif bank_name == "KDB":
        #     before_preprocessed_products.extend(KdbCrawler(base_url=BankLink.KDB_LINK.value).start())

        # elif bank_name == "BNK_BUSAN":
        #     BusanBankUnifiedCrawler(base_url=BankLink.BUSAN_BANK_LINK.value).start()
        #     data = self.read_json("BNK_BUSAN")
        #     for i in data:
        #         before_preprocessed_products.append(i)
        #
        elif bank_name == "SC_JEIL":
            SCBankCleanCrawler(base_url=BankLink.SC_BANK_LINK.value,
                               detail_url_base=BankLink.SC_BANK_BASE_LINK.value).start()
            data = self.read_json("SC_JEIL")
            for i in data:
                before_preprocessed_products.append(i)
        #
        # elif bank_name == "GWANGJU":
        #     KJBankCompleteCrawler(base_url=BankLink.GWANGJU_BANK_LINK.value,
        #                           deposit_list_url=BankLink.GWANGJU_BANK_DEPOSIT_LINK.value).start()
        #     data = self.read_json("GWANGJU")
        #     for i in data:
        #         before_preprocessed_products.append(i)
        #
        # elif bank_name == "JEJU":
        #     JejuBankDepositSavingsOnlyCrawler(base_url=BankLink.JEJU_BANK_BASE_LINK.value).start()
        #     data = self.read_json("JEJU")
        #     for i in data:
        #         before_preprocessed_products.append(i)
        #
        # elif bank_name == "HANA":
        #     HanaBankCrawler().start()
        #     data = self.read_json("HANA")
        #     for i in data:
        #         before_preprocessed_products.append(i)
        #
        #
        # elif bank_name == "KB":
        #     KBProductCrawler().start()
        #     data = self.read_json("KB")
        #     for i in data:
        #         before_preprocessed_products.append(i)
        #
        #
        # elif bank_name == "NH":
        #     NHBankCrawler().start()
        #     data = self.read_json("NH")
        #     for i in data:
        #         before_preprocessed_products.append(i)
        #
        # elif bank_name == "WOORI":
        #     WooriBankCrawler().start()
        #     data = self.read_json("WOORI")
        #     for i in data:
        #         before_preprocessed_products.append(i)
        #
        # elif bank_name == "IBK":  # 안됨
        #     IBKFullCrawler().start()
        #
        #     data = self.read_json("IBK")
        #     for i in data["products"]:
        #         before_preprocessed_products.append(i)
        #
        # elif bank_name == "SH_SUHYUP":
        #     SuhyupBankCategoryCrawler().start()
        #     data = self.read_json("SH_SUHYUP")
        #     for i in data:
        #         before_preprocessed_products.append(i)
        #
        # elif bank_name == "IM_BANK":
        #     IMBankCompleteCrawler().start()
        #
        #     data = self.read_json("IM_BANK")
        #     for i in data["products"]:
        #         before_preprocessed_products.append(i)

        # 데이터 리턴
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

            ## 삽입
            for product in after_preprocessed_products:
                self.productRepository.save_one_product(product_data=product, bank_name=bank_name,
                                                        connection=connection)

            ## 삭제
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

        self.logger.info(f"월 마다 진행 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        for bank_name in bank_data:
            self.logger.info("=====크롤링 시작=====")
            before_preprocessed_products = self.crawling(bank_name=bank_name)
            self.logger.info("=====크롤링 끝=====")

            #######
            self.logger.info("=====전처리 시작=====")
            after_preprocessed_products = self.preprocessed(before_preprocessed_products)
            self.logger.info("=====전처리 끝=====")

            #######
            self.logger.info("=====DB에 저장 시작=====")
            self.save_to_db(after_preprocessed_products, bank_name=bank_name)
            self.logger.info("=====DB에 끝=====")

        end_time = datetime.now()
        elapsed_time = end_time - start_time
        self.logger.info(f"월 마다 진행 완료: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"총 소요 시간: {elapsed_time}")

    def start(self):
        self.logger.info("===== 상품 데이터 크롤링, 전처리, 삽입 시작 =====")

        try:
            self.logger.info("===== 은행 데이터 저장 시작 =====")
            bank_repository = BankRepository()
            bank_repository.save_bank()
            self.logger.info("===== 은행 데이터 저장 완료 =====")

            # 아래 두 줄은 테스트를 위함
            self.logger.info("===== 기존 상품 데이터 삭제 시작 (테스트용) =====")
            self.productRepository.delete_all_product()
            self.logger.info("===== 기존 상품 데이터 삭제 완료 (테스트용) =====")

            self.month_task()

            ################### 자동화 코드입니다. 주석을 풀면 됩니다.########################
            # self.logger.info("===== 스케줄러 시작 - 매일 02:00에 실행 =====")
            # schedule.every().day.at("02:00").do(self.month_task)
            #
            # while True:
            #     schedule.run_pending()
            #     time.sleep(3600)

        except Exception as e:
            self.logger.error(f"상품 데이터 크롤링, 전처리, 삽입 오류 발생: {e}")
            raise

if __name__ == "__main__":
    crawling = Crawling()
    crawling.setup_logging()
    crawling.start()
