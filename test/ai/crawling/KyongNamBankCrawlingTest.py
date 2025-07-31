from src.ai.preprocessing.LlmUtil import LlmUtil
from src.ai.crawling.crawler.kyongnam.KyongNamBankCrawler import KyongNamBankCrawler
from src.ai.crawling.crawler.BankLink import BankLink

if __name__ == '__main__':
    start = KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_DEPOSIT_LINK.value).start()

    util = LlmUtil()
    for i in start:
        json = util.create_preferential_json(content=i)
        print(json)
