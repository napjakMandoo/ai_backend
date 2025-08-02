from src.preprocessing.crawling.crawler.nh.nh import NHBankCrawler

# start로 시작하기 통일
# 저장 경로 변경

if "__main__" == __name__:
    crawler = NHBankCrawler()
    crawler.start()