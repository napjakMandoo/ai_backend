from src.crawler.util.BankLink import BankLink
from src.crawler.bank_crawler.post.PostBankCrawler import PostBankCrawler

if __name__ == '__main__':
    start = PostBankCrawler(base_url=BankLink.POST_BANK_LINK.value).start()
    for i in start:
        print("===================")
        print(i)
        print("d")