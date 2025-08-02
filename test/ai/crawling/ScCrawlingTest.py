from src.preprocessing.crawling.crawler.sc.sc_bank_crawler import SCBankCleanCrawler

if __name__ == "__main__":
    crawler = SCBankCleanCrawler()
    crawler.start()