from src.preprocessing.crawling.crawler.kdb.KdbCrawler import KdbCrawler
from src.preprocessing.crawling.BankLink import BankLink

if __name__ == '__main__':
    start = KdbCrawler(base_url=BankLink.KDB_LINK.value).start()

    for i in start:
        print(i)
