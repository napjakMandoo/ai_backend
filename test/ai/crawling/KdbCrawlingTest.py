from src.ai.crawling.crawler.kdb.KdbCrawler import KdbCrawler
from src.ai.crawling.crawler.BankLink import BankLink

if __name__ == '__main__':
    start = KdbCrawler(base_url=BankLink.KDB_LINK.value).start()

    for i in start:
        print(i)
