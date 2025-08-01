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


class App:
    def __init__(self):
        self.productRepository = ProductRepository()
        self.logger = logging.getLogger(__name__)
        self.mysqlUtil = MysqlUtil()
        self.llmUtil = LlmUtil()
        self.bankRepository = BankRepository()

    def crawling(self):
        before_preprocessed_products = []
        # 경남은행
        before_preprocessed_products.extend(KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_DEPOSIT_LINK.value).start())
        # before_preprocessed_products.extend(KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_SAVING_LINK.value).start())
        return before_preprocessed_products

    def preprocessed(self, before_preprocessed_products):
        preprocessed_products = []
        for product in before_preprocessed_products:
            json = self.llmUtil.create_preferential_json(content=product)
            preprocessed_products.append(json)
        return preprocessed_products

    # after_preprocessed_products는 전처리된 데이터들 묶음
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
        ####### 자동화 해야할 부분 ########

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"월 마다 진행: {current_time}")

        self.logger.info("=====크롤링 시작=====")
        crawling = self.crawling()
        self.logger.info("=====크롤링 끝=====")

        #######
        self.logger.info("=====전처리 시작=====")
        after_preprocessed_products = self.preprocessed(crawling)
        self.logger.info("=====전처리 끝=====")

        #######
        self.logger.info("=====DB에 저장 시작=====")
        self.saveToDB(after_preprocessed_products)

        #######
        self.logger.info("=====DB에 끝=====")
        self.logger.info(f"월 마다 진행: {current_time}")



    def start(self):
        # 해야할 거: @자동화 해야함, url, 팀원들 크롤링 합쳐야함, print 대신 로깅 처리, 사진도 넣어야함, 크롤링 테스트

        self.logger.info("=====은행 데이터 저장 시작=====")
        bank_repository = BankRepository()
        bank_repository.save_bank()
        self.logger.info("=====은행 데이터 저장 끝=====")

        schedule.every().day.at("02:00").do(self.month_task)

        while True:
            schedule.run_pending()
            time.sleep(3600)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )

    app = App()
    app.start()

    # before_preprocessed_products.extend(SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_ONLINE_LINK.value).start())
    # before_preprocessed_products.extend(SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_LUMP_LINK.value).start())
    # before_preprocessed_products.extend(SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_LUMP_ROLL_LINK.value).start())
