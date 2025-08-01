from src.preprocessing.crawling.BankLink import BankLink
from src.preprocessing.crawling.crawler.sinhan.SinHanBankCrawler import SinHanBankCrawler

if __name__ == '__main__':
    start = SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_ONLINE_LINK.value).start()
    for i in start:
        print("===================")
        print(i)