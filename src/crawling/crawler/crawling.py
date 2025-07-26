from src.crawling.crawler.BankLink import BankLink
from src.crawling.crawler.kyongnam.KyongNamBankCrawler import  KyongNamBankCrawler

if __name__ == "__main__":
    before_preprocessed_products = []
    before_preprocessed_products.extend(KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_DEPOSIT_LINK.value).start())
    before_preprocessed_products.extend(KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_SAVING_LINK.value).start())
