from src.crawling.crawler.BankLink import BankLink
from src.crawling.crawler.kyongnam.KyongNamBankCrawler import  KyongNamBankCrawler
from src.crawling.crawler.sinhan.SinHanBankCrawler import SinHanBankCrawler

if __name__ == "__main__":
    before_preprocessed_products = []
    before_preprocessed_products.extend(KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_DEPOSIT_LINK.value).start())
    before_preprocessed_products.extend(KyongNamBankCrawler(base_url=BankLink.KYONGNAM_BANK_SAVING_LINK.value).start())
    before_preprocessed_products.extend(SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_ONLINE_LINK.value).start())
    before_preprocessed_products.extend(SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_LUMP_LINK.value).start())
    before_preprocessed_products.extend(SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_LUMP_ROLL_LINK.value).start())
