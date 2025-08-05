from src.crawler.util.BankLink import BankLink
from src.crawler.bank_crawler.sinhan.SinHanBankCrawler import SinHanBankCrawler

if __name__ == '__main__':
    start = SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_ONLINE_LINK.value).start()
    for i in start:
        print("===================")
        print(i)