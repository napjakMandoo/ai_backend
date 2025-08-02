from __future__ import annotations

import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback

from src.preprocessing.crawling.util.crawlingUtil import CrawlingUtil
import logging

class KyongNamBankCrawler:
    def __init__(self, headless: bool = True, timeout: int = 30, base_url:str=""):
        self.headless = headless
        self.timeout  = timeout
        self.driver   = self._create_driver()
        self.wait     = WebDriverWait(self.driver, timeout)
        self.base_url = base_url
        self.util = CrawlingUtil(self.driver)
        self.logger = logging.getLogger(__name__)

    def _create_driver(self) -> webdriver.Chrome:
        opts = Options()
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
            " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        )
        return webdriver.Chrome(options=opts)

    def start(self):
        self.logger.info(f"{self.base_url} 시작")
        product = []
        try:
            self.driver.get(self.base_url)
            self.wait.until(EC.presence_of_element_located((By.ID, "prdListArea")))

            last_page = self.util.get_last_page()

            for i in range(1, last_page+1):
                self.logger.info(f"현재 페이지 : {i}")

                if i >= 2:
                    xpath_num = f"//div[contains(@class,'paginate')]//a[normalize-space(text())='{i}']"
                    page_a = self.driver.find_element(By.XPATH, xpath_num)
                    self.driver.execute_script("arguments[0].click();", page_a)
                    self.wait.until(EC.staleness_of(page_a))
                    self.wait.until(EC.presence_of_element_located((By.ID, "prdListArea")))

                crawling = self.current_page_crawling()
                product.extend(crawling)
                self.driver.get(self.base_url)
                time.sleep(3)

        except Exception as e:
            self.logger.error(f"크롤링 중 오류 발생: {e}")
            self.logger.error(traceback.format_exc())

        finally:
            self.logger.info(f"[{datetime.now()}] 크롤링 완료")
            self.driver.quit()

        return product

    def current_page_crawling(self):
        saving_products = []

        initial_links = self.wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pro-intlist-in dt a"))
        )
        total_products = len(initial_links)
        self.logger.info(f"총 {total_products}개의 상품을 발견했습니다.")

        for i in range(total_products):
            try:
                self.logger.info(f"[{i + 1}/{total_products}] 상품 처리 중...")

                current_links = self.wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pro-intlist-in dt a"))
                )

                product_link = current_links[i]
                product_name = product_link.text.strip()
                self.logger.info(f"상품명: {product_name}")

                self.driver.execute_script("arguments[0].click();", product_link)
                time.sleep(3)

                html_content = self.driver.page_source
                product_info = self.util.extract_content_text(html_content, self.base_url)
                self.logger.info("상품 상세 정보 추출 완료")
                saving_products.append(product_info)

                self.driver.get(self.base_url)
                time.sleep(3)

                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.pro-intlist-in dt a"))
                )
                self.logger.info("원래 페이지로 복귀 완료")

            except Exception as e:
                self.logger.error(f"상품 {i + 1} 처리 중 오류: {e}")
                try:
                    self.driver.get(self.base_url)
                    time.sleep(3)
                    self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.pro-intlist-in dt a"))
                    )
                    self.logger.info("오류 후 원래 페이지 복구 완료")
                except Exception as e2:
                    self.logger.error(f"페이지 복구 실패: {e2}")
                    break
                continue

        self.logger.info(f"총 {len(saving_products)}개 상품 크롤링 완료")
        return saving_products