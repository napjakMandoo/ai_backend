from src.crawler.bank_crawler.sh.sh import SuhyupBankCategoryCrawler
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('suhyup_category_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


test = SuhyupBankCategoryCrawler()
test.start()
