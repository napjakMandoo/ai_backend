from src.preprocessing.crawling.BankLink import BankLink
from src.preprocessing.crawling.crawler.jeju.jeju_bank_crawler import JejuBankDepositSavingsOnlyCrawler

if __name__ == '__main__':
    crawler = JejuBankDepositSavingsOnlyCrawler(headless=True ,base_url=BankLink.JEJU_BANK_BASE_LINK.value)
    crawler.start()
