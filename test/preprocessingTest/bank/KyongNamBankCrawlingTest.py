from src.preprocessing.crawling.ai.LlmUtil import LlmUtil
from src.preprocessing.crawling.crawler.kyongnam.KyongNamBankCrawler import KyongNamBankCrawler
from src.preprocessing.crawling.BankLink import BankLink
import logging

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    start = KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_DEPOSIT_LINK.value).start()

    util = LlmUtil()
    for i in start:
        json = util.create_preferential_json(content=i)
        print(json)
