from src.crawler.bank_crawler.ibk.ibk_bank import IBKFullCrawler

if __name__ == '__main__':
    crawler = IBKFullCrawler()
    crawler.start()