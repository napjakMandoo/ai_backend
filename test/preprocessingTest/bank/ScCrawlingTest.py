from src.crawler.util.BankLink import BankLink
from src.crawler.bank_crawler.sc.sc_bank_crawler import SCBankCleanCrawler

if __name__ == "__main__":
    crawler = SCBankCleanCrawler(headless=True,base_url=BankLink.SC_BANK_LINK.value, detail_url_base=BankLink.SC_BANK_BASE_LINK.value)
    crawler.start()