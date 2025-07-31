from src.ai.crawling.crawler.BankLink import BankLink
from src.ai.crawling.crawler.sinhan.SinHanBankCrawler import SinHanBankCrawler

if __name__ == '__main__':
    start = SinHanBankCrawler(base_url=BankLink.SINHAN_BANK_ONLINE_LINK.value).start()
    for i in start:
        print("===================")
        print(i)