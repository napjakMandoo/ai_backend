import time
from datetime import datetime
import logging
import schedule
import json
import os
from logging.handlers import RotatingFileHandler

from src.app.service.ai_service import ai_service
from src.crawler.ai.LlmUtil import LlmUtil
from src.crawler.bank_crawler.busan.busan_bank_crawler import BusanBankUnifiedCrawler
from src.crawler.bank_crawler.gwangju.gwangju_bank_crawler import KJBankCompleteCrawler
from src.crawler.bank_crawler.hana.hana import HanaBankCrawler
from src.crawler.bank_crawler.ibk.ibk_bank import IBKFullCrawler
from src.crawler.bank_crawler.im.IM import IMBankCompleteCrawler
from src.crawler.bank_crawler.jb.JBBankCrawler import JBBankCrawler
from src.crawler.bank_crawler.jeju.jeju_bank_crawler import JejuBankDepositSavingsOnlyCrawler
from src.crawler.bank_crawler.kb.kb import KBProductCrawler
from src.crawler.bank_crawler.kdb.KdbCrawler import KdbCrawler
from src.crawler.bank_crawler.nh.nh import NHBankCrawler
from src.crawler.bank_crawler.post.PostBankCrawler import PostBankCrawler
from src.crawler.bank_crawler.sc.sc_bank_crawler import SCBankCleanCrawler
from src.crawler.bank_crawler.sh.sh import SuhyupBankCategoryCrawler
from src.crawler.bank_crawler.sinhan.SinHanBankCrawler import SinHanBankCrawler
from src.crawler.bank_crawler.woori.woori import WooriBankCrawler
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

    def crawling(self, bank_name: str = ""):
        before_preprocessed_products = []

        if bank_name == "BNK_GYEONGNAM":
            before_preprocessed_products.extend(
                KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_DEPOSIT_LINK.value).start())
        if bank_name == "POST_OFFICE":
            before_preprocessed_products.extend(PostBankCrawler(base_url=BankLink.POST_BANK_LINK.value).start())
        if bank_name == "SHINHAN":
            before_preprocessed_products.extend(
                SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_ONLINE_LINK.value).start())
            before_preprocessed_products.extend(
                SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_LUMP_LINK.value).start())
            before_preprocessed_products.extend(
                SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_LUMP_ROLL_LINK.value).start())

        if bank_name == "KDB":
            before_preprocessed_products.extend(KdbCrawler(base_url=BankLink.KDB_LINK.value).start())

        if bank_name == "BNK_BUSAN":
            before_preprocessed_products.extend(BusanBankUnifiedCrawler(base_url=BankLink.BUSAN_BANK_LINK.value).start())

        if bank_name == "SC_JEIL":
            before_preprocessed_products.extend(SCBankCleanCrawler(base_url=BankLink.SC_BANK_LINK.value,detail_url_base=BankLink.SC_BANK_BASE_LINK.value).start())

        if bank_name == "GWANGJU":
            before_preprocessed_products.extend(KJBankCompleteCrawler(base_url=BankLink.GWANGJU_BANK_LINK.value,deposit_list_url=BankLink.GWANGJU_BANK_DEPOSIT_LINK.value).start())

        if bank_name == "JEJU":
            before_preprocessed_products.extend(JejuBankDepositSavingsOnlyCrawler(base_url=BankLink.JEJU_BANK_BASE_LINK.value).start())

        if bank_name == "HANA":
            before_preprocessed_products.extend(HanaBankCrawler().start())

        if bank_name == "JEONBUK":
            before_preprocessed_products.extend(JBBankCrawler(headless=True, timeout=10, base_url=BankLink.JB_BANK_LINK.value).start())

        if bank_name == "KB":
            before_preprocessed_products.extend(KBProductCrawler().start())

        if bank_name == "NH":
            before_preprocessed_products.extend(NHBankCrawler().start())

        if bank_name == "WOORI":
            before_preprocessed_products.extend(WooriBankCrawler().start())

        if bank_name == "IBK":  # 안됨
            before_preprocessed_products.extend(IBKFullCrawler().start())
        #
        if bank_name == "SH_SUHYUP":
            before_preprocessed_products.extend(SuhyupBankCategoryCrawler().start())

        if bank_name == "IM_BANK":
            before_preprocessed_products.extend(IMBankCompleteCrawler().start())
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

            self.productRepository.check_is_deleted(bank_name=bank_name, new_products_name=products_name_set,connection=connection)
            connection.commit()
        except Exception as e:
            self.logger.error(f"mysql 데이터 삽입 에러: {e}")
            connection.rollback()
        finally:
            connection.close()

    def month_task_distributed(self):
        """
        매달 첫째 주(1~7일)에 16개 은행을 7일 동안 분할 실행.
        1일(3개) / 2~6일(2개씩) / 7일(3개)
        """
        today = datetime.now()
        day = today.day

        if day > 7:
            self.logger.info(f"[SKIP] {today.strftime('%Y-%m-%d')} - 첫째 주 아님, 스킵")
            return

        bank_list = list(self.bankRepository.get_bank_data())
        total_banks = len(bank_list)

        # 16개 은행 기준 분배
        distribution = {
            1: (0, 3),
            2: (3, 5),
            3: (5, 7),
            4: (7, 9),
            5: (9, 11),
            6: (11, 13),
            7: (13, 16)
        }

        if day not in distribution:
            self.logger.info(f"[SKIP] {day}일 - 분배 설정 없음")
            return

        start_idx, end_idx = distribution[day]
        today_banks = bank_list[start_idx:end_idx]

        self.logger.info(f"===== [{today.strftime('%Y-%m-%d')}] 실행 은행 {len(today_banks)}개 =====")
        self.logger.info(f"대상 은행 목록: {today_banks}")

        for bank_name in today_banks:
            try:
                self.logger.info(f"===== [{bank_name}] 크롤링 시작 =====")
                before_preprocessed_products = self.crawling(bank_name=bank_name)

                if not before_preprocessed_products:
                    self.logger.info(f"[{bank_name}] 결과 없음, 건너뜀")
                    continue

                after_preprocessed_products = self.preprocessed(before_preprocessed_products)
                self.save_to_db(after_preprocessed_products, bank_name=bank_name)
                self.logger.info(f"===== [{bank_name}] 완료 =====")
            except Exception as e:
                self.logger.error(f"[{bank_name}] 처리 중 오류: {e}")

        self.logger.info("===== 오늘자 분할 크롤링 완료 =====")

    def start(self):
        self.logger.info("===== 상품 데이터 크롤링, 전처리, 삽입 시작 =====")

        try:
            self.logger.info("===== 은행 데이터 저장 시작 =====")
            bank_repository = BankRepository()
            bank_repository.save_bank()
            self.logger.info("===== 은행 데이터 저장 완료 =====")


            ################## 자동화 코드입니다. 주석을 풀면 됩니다.########################
            self.logger.info("===== 스케줄러 시작 - 매일 02:00 (1~7일만 실행) =====")
            schedule.every().day.at("02:00").do(self.month_task_distributed)

            while True:
                schedule.run_pending()
                time.sleep(3600)

        except Exception as e:
            self.logger.error(f"상품 데이터 크롤링, 전처리, 삽입 오류 발생: {e}")
            raise

if __name__ == "__main__":
    crawling = Crawling()
    crawling.setup_logging()
    crawling.start()
