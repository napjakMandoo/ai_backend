from datetime import datetime
import logging
import schedule
import time

from src.preprocessing.crawling.ai.LlmUtil import LlmUtil
from src.preprocessing.crawling.BankLink import BankLink
from src.preprocessing.crawling.crawler.kyongnam.KyongNamBankCrawler import  KyongNamBankCrawler
from src.preprocessing.db.bank.BankRepository import BankRepository
from src.preprocessing.db.product.productRepository import ProductRepository
from src.preprocessing.db.util.MysqlUtil import MysqlUtil
import json

class AppTest:
    def __init__(self):
        self.productRepository = ProductRepository()
        self.logger = logging.getLogger(__name__)
        self.mysqlUtil = MysqlUtil()
        self.llmUtil = LlmUtil()
        self.bankRepository = BankRepository()

    def crawling(self):
        before_preprocessed_products = []
        # # 정기주 테스트 -> 상품명으로 중복 여부를 체크하는데, LLM이 상품명을 가끔 다르게 뱉음 " "와 같은 공백을 넣을떄도 있음
        # before_preprocessed_products.extend(KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_DEPOSIT_LINK.value).start())

        # # 이수민님 테스트
        # hana = "/home/jeonggiju/hanium/ai_backend/src/preprocessing/crawling/crawler/hana/hana_bank_products.json"
        # with open(hana, "r", encoding="utf-8") as f:
        #     data = json.load(f)
        #
        # for i in data:
        #     before_preprocessed_products.append(i)

        # 은주연 테스트
        jeju = "/home/jeonggiju/hanium/ai_backend/src/preprocessing/crawling/crawler/jeju/JEJU.json"
        with open(jeju, "r", encoding="utf-8") as f:
            data = json.load(f)

        for i in data:
            before_preprocessed_products.append(i)


        # 박연제님 테스트
        # sh = "/home/jeonggiju/hanium/ai_backend/src/preprocessing/crawling/crawler/sh/suhyup_category_products_20250730_170125.json"
        # with open(sh, "r", encoding="utf-8") as f:
        #     data = json.load(f)
        #
        # for i in data["products"]:
        #     before_preprocessed_products.append(i)

        return before_preprocessed_products

    def preprocessed(self, before_preprocessed_products):
        preprocessed_products = []
        for product in before_preprocessed_products:
            json = self.llmUtil.create_preferential_json(content=product)
            preprocessed_products.append(json)
        return preprocessed_products

    # after_preprocessed_products는 전처리된 데이터들 묶음
    def saveToDB(self, after_preprocessed_products, bank_name:str=""):
        if not bank_name:
            self.logger.info("은행 명이 없음")
        connection = self.mysqlUtil.get_connection()

        try:
            connection.begin()
            ## 삽입 ##
            for product in after_preprocessed_products:
                self.productRepository.save_one_product(product_data=product,bank_name=bank_name,connection=connection)

            ## 삭제 ##
            products_name_set = set()

            print(after_preprocessed_products)
            for product in after_preprocessed_products:
                products_name_set.add(product.product_name)

            self.productRepository.check_is_deleted(bank_name=bank_name, new_products_name=products_name_set,connection=connection)
            connection.commit()
        except Exception as e:
            self.logger.error(f"mysql 데이터 삽입 에러: {e}")
            connection.rollback()
        finally:
            connection.close()


    def month_task(self):
        bank_repository = BankRepository()
        bank_data = bank_repository.get_bank_data()
        bank_name_list = []
        for bank in bank_data:
            bank_name_list.append(bank[0])

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"월 마다 진행: {current_time}")

        bank_name = "SH_SUHYUP" # 테스트할때 바꿔줘야함
        self.logger.info("=====크롤링 시작=====")
        # before_preprocessed_products = self.crawling(bank_name=bank_name)
        before_preprocessed_products = self.crawling()
        self.logger.info("=====크롤링 끝=====")

        #######
        self.logger.info("=====전처리 시작=====")
        after_preprocessed_products = self.preprocessed(before_preprocessed_products)
        self.logger.info("=====전처리 끝=====")


        #######
        self.logger.info("=====DB에 저장 시작=====")
        self.saveToDB(after_preprocessed_products,  bank_name=bank_name)
        self.logger.info("=====DB에 끝=====")

        ####### 삭제를 위한 데이터(은행 상품)


        self.logger.info(f"월 마다 진행: {current_time}")


    def start(self):
        # 해야할 거: @자동화 해야함, url, 팀원들 크롤링 합쳐야함, @print 대신 로깅 처리, 사진도 넣어야함, 크롤링 테스트

        self.logger.info("=====은행 데이터 저장 시작=====")
        bank_repository = BankRepository()
        bank_repository.save_bank()
        self.logger.info("=====은행 데이터 저장 끝=====")

        self.productRepository.delete_all_product()
        self.month_task()

        ################### 자동화 코드입니다. 주석을 풀면 됩니다.########################
        # schedule.every().day.at("02:00").do(self.month_task)
        #
        # while True:
        #     schedule.run_pending()
        #     time.sleep(3600)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )
    ### 시작전 삭제
    ProductRepository().delete_all_product()

    app = AppTest()
    app.start()

