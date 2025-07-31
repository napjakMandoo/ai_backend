from src.ai.crawling.crawler.BankLink import BankLink
from src.ai.crawling.crawler.post.PostBankCrawler import PostBankCrawler

if __name__ == '__main__':
    start = PostBankCrawler(base_url=BankLink.POST_BANK_LINK.value).start()
    for i in start:
        print("===================")
        print(i)