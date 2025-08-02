from datetime import datetime
import logging
import schedule
import time
import json
from src.preprocessing.crawling.ai.LlmUtil import LlmUtil
from src.preprocessing.crawling.BankLink import BankLink
from src.preprocessing.crawling.crawler.busan.busan_bank_crawler import BusanBankUnifiedCrawler
from src.preprocessing.crawling.crawler.gwangju.gwangju_bank_crawler import KJBankCompleteCrawler
from src.preprocessing.crawling.crawler.hana.hana import HanaBankCrawler
from src.preprocessing.crawling.crawler.ibk.ibk_bank import IBKFullCrawler
from src.preprocessing.crawling.crawler.im.IM import IMBankCompleteCrawler
from src.preprocessing.crawling.crawler.jeju.jeju_bank_crawler import JejuBankDepositSavingsOnlyCrawler
from src.preprocessing.crawling.crawler.kb.kb import KBProductCrawler
from src.preprocessing.crawling.crawler.kdb.KdbCrawler import KdbCrawler
from src.preprocessing.crawling.crawler.kyongnam.KyongNamBankCrawler import  KyongNamBankCrawler
from src.preprocessing.crawling.crawler.nh.nh import NHBankCrawler
from src.preprocessing.crawling.crawler.post.PostBankCrawler import PostBankCrawler
from src.preprocessing.crawling.crawler.sc.sc_bank_crawler import SCBankCleanCrawler
from src.preprocessing.crawling.crawler.sh.sh import SuhyupBankCategoryCrawler
from src.preprocessing.crawling.crawler.sinhan.SinHanBankCrawler import SinHanBankCrawler
from src.preprocessing.crawling.crawler.woori.woori import WooriBankCrawler
from src.preprocessing.db.bank.BankRepository import BankRepository
from src.preprocessing.db.product.productRepository import ProductRepository
from src.preprocessing.db.util.MysqlUtil import MysqlUtil
import dotenv
import os

from test.preprocessingTest.preprocessing.preprocessingTest import kyongNam


class App:
    def __init__(self):
        self.productRepository = ProductRepository()
        self.logger = logging.getLogger(__name__)
        self.mysqlUtil = MysqlUtil()
        self.llmUtil = LlmUtil()
        self.bankRepository = BankRepository()

    def read_json(self, file_name):
        directory = os.getenv("JSON_RESULT_PATH")

        file_path = directory + "/" + file_name + ".json"

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data

    def crawling(self, bank_name:str=""):
        before_preprocessed_products = []

        ######################## 정기주
        if bank_name == "BNK_GYEONGNAM":
            before_preprocessed_products.extend(KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_DEPOSIT_LINK.value).start())
        elif bank_name == "POST_OFFICE":
            before_preprocessed_products.extend(PostBankCrawler(base_url=BankLink.POST_BANK_LINK.value).start())
        elif bank_name == "SHINHAN":
            before_preprocessed_products.extend(SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_ONLINE_LINK.value).start())
            before_preprocessed_products.extend(SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_LUMP_LINK.value).start())
            before_preprocessed_products.extend(SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_LUMP_ROLL_LINK.value).start())
        elif bank_name == "KDB":
            before_preprocessed_products.extend(KdbCrawler(base_url=BankLink.KDB_LINK.value).start())
        ############################# 은주연
        elif bank_name == "BNK_BUSAN":
             BusanBankUnifiedCrawler(base_url=BankLink.BUSAN_BANK_LINK.value).start()
             data = self.read_json("BNK_BUSAN")
             for i in data:
                 before_preprocessed_products.append(i)

        elif bank_name == "SC_JEIL":
            SCBankCleanCrawler(base_url=BankLink.SC_BANK_LINK.value, detail_url_base=BankLink.SC_BANK_BASE_LINK.value).start()
            data = self.read_json("SC_JEIL")
            for i in data:
                before_preprocessed_products.append(i)

        elif bank_name == "GWANGJU":
            KJBankCompleteCrawler(base_url=BankLink.GWANGJU_BANK_LINK.value, deposit_list_url=BankLink.GWANGJU_BANK_DEPOSIT_LINK.value).start()
            data = self.read_json("GWANGJU")
            for i in data:
                before_preprocessed_products.append(i)

        elif bank_name == "JEJU":
            JejuBankDepositSavingsOnlyCrawler(base_url=BankLink.JEJU_BANK_BASE_LINK.value).start()
            data = self.read_json("JEJU")
            for i in data:
                before_preprocessed_products.append(i)

        ########################### 이수민
        elif bank_name == "HANA":
            HanaBankCrawler().start()
            data = self.read_json("HANA")
            for i in data:
                before_preprocessed_products.append(i)


        elif bank_name == "KB":
            KBProductCrawler().start()
            data = self.read_json("KB")
            for i in data:
                before_preprocessed_products.append(i)


        elif bank_name == "NH":
            NHBankCrawler().start()
            data = self.read_json("NH")
            for i in data:
                before_preprocessed_products.append(i)

        elif bank_name == "WOORI":
            WooriBankCrawler().start()
            data = self.read_json("WOORI")
            for i in data:
                before_preprocessed_products.append(i)

        ############################ 박연제
        elif bank_name == "IBK": # 안됨
            IBKFullCrawler().start()

            data = self.read_json("IBK")
            for i in data["products"]:
                before_preprocessed_products.append(i)

        elif bank_name == "SH_SUHYUP":
            SuhyupBankCategoryCrawler().start()
            data = self.read_json("SH_SUHYUP")
            for i in data:
                before_preprocessed_products.append(i)

        elif bank_name == "IM_BANK":
            IMBankCompleteCrawler().start()

            data = self.read_json("IM_BANK")
            for i in data["products"]:
                before_preprocessed_products.append(i)

        # 데이터 리턴
        return before_preprocessed_products

    def preprocessed(self, before_preprocessed_products):
        preprocessed_products = []
        for product in before_preprocessed_products:
            json = self.llmUtil.create_preferential_json(content=product)
            preprocessed_products.append(json)
        return preprocessed_products

    def saveToDB(self, after_preprocessed_products):
        connection = self.mysqlUtil.get_connection()

        try:
            connection.begin()
            for product in after_preprocessed_products:
                self.productRepository.save_one_product(product_data=product,
                                                        bank_name="BNK_GYEONGNAM",  # 이거 수정해야함
                                                        connection=connection)
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
            bank_name_list.append(bank["bank_name"])


        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"월 마다 진행: {current_time}")

        for bank_name in bank_name_list:
            self.logger.info("=====크롤링 시작=====")
            before_preprocessed_products = self.crawling(bank_name=bank_name)
            self.logger.info("=====크롤링 끝=====")

            #######
            self.logger.info("=====전처리 시작=====")
            after_preprocessed_products = self.preprocessed(before_preprocessed_products)
            self.logger.info("=====전처리 끝=====")

            #######
            self.logger.info("=====DB에 저장 시작=====")
            self.saveToDB(after_preprocessed_products)
            self.logger.info("=====DB에 끝=====")

        self.logger.info(f"월 마다 진행: {current_time}")


    def start(self):
        # 해야할 거: @자동화 해야함, url, 팀원들 크롤링 합쳐야함, @print 대신 로깅 처리, 사진도 넣어야함, 크롤링 테스트

        self.logger.info("=====은행 데이터 저장 시작=====")
        bank_repository = BankRepository()
        bank_repository.save_bank()
        self.logger.info("=====은행 데이터 저장 끝=====")

        # 아래 두 줄은 테스트를 위함
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

    app = App()
    app.start()

