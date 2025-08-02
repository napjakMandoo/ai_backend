from src.preprocessing.crawling.BankLink import BankLink
from src.preprocessing.crawling.crawler.gwangju.gwangju_bank_crawler import KJBankCompleteCrawler

if __name__ == '__main__':
    crawler = KJBankCompleteCrawler(headless=True, base_url=BankLink.GWANGJU_BANK_LINK.value)
    crawler.start()
