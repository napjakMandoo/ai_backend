from src.preprocessing.crawling.BankLink import BankLink
from src.preprocessing.crawling.crawler.busan.busan_bank_crawler import BusanBankUnifiedCrawler

if __name__ == "__main__":
    crawler = BusanBankUnifiedCrawler(headless=True, base_url=BankLink.BUSAN_BANK_LINK.value)
    crawler.start()
