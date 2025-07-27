
from __future__ import annotations

import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback
import re

from src.crawling.crawler.util.crawlingUtil import CrawlingUtil


class SinHanBankCrawler:
    def __init__(self, headless: bool = True, timeout: int = 30, base_url:str=""):
        self.headless = headless
        self.timeout  = timeout
        self.driver   = self._create_driver()
        self.wait     = WebDriverWait(self.driver, timeout)
        self.base_url = base_url
        self.util = CrawlingUtil(self.driver)
        self.processed_products = set()

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
        print(f"{self.base_url} 시작")
        products: list[dict] = []
        try:
            self.driver.get(self.base_url)
            time.sleep(5)
            self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            self.wait.until(EC.presence_of_element_located((By.ID, "gen_prod_list")))
            self.wait.until(EC.presence_of_element_located((By.ID, "pgl_gen_list")))

            labels = self.driver.find_elements(By.CSS_SELECTOR, "a[id^='pgl_gen_list_page_']")
            page_indices = [int(a.get_attribute("index")) for a in labels if a.get_attribute("index") and a.get_attribute("index").isdigit()]
            last_page = max(page_indices) if page_indices else 1
            print("last page:", last_page)

            for page in range(1, last_page + 1):
                print(f"\n--- {page} 페이지 처리 중 ---")
                if page > 1:
                    page_link = self.driver.find_elements(By.CSS_SELECTOR, f"a[id='pgl_gen_list_page_{page}']")
                    if page_link:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                            page_link[0]
                        )
                        time.sleep(2)
                        self.driver.execute_script("arguments[0].click();", page_link[0])
                        time.sleep(8)
                        self.wait.until(EC.presence_of_element_located((By.ID, "gen_prod_list")))
                        time.sleep(3)

                product_info_list = []
                time.sleep(2)
                links = self.driver.find_elements(By.CSS_SELECTOR, "a[id*='gen_prod_list'][id*='_tbx_상품명']")
                for idx, link in enumerate(links):
                    try:
                        name = link.text.strip()
                        pid = link.get_attribute('id')
                        product_info_list.append({'name': name, 'id': pid})
                    except Exception as e:
                        print(f"상품 정보 수집 오류: {e}")

                print(f"페이지 {page}에서 {len(product_info_list)}개 상품 발견")

                for info in product_info_list:
                    name = info['name']
                    if name in self.processed_products:
                        print(f"중복 상품 건너뛰기: {name}")
                        continue
                    print(f"\n상품 처리 시작: {name}")
                    self.processed_products.add(name)

                    try:
                        target = next((e for e in self.driver.find_elements(By.CSS_SELECTOR, "a[id*='gen_prod_list'][id*='_tbx_상품명']") if e.text.strip() == name), None)
                        if not target:
                            print(f"상품 링크 찾기 실패: {name}")
                            continue
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                            target
                        )
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", target)
                        time.sleep(3)
                        self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

                        product_data = self.util.extract_content_text(self.driver.page_source)
                        products.append(product_data)
                        print(f"상품 '{name}' 처리 완료")

                    except Exception as e:
                        print(f"상품 처리 중 오류: {e}")

                    self.driver.get(self.base_url)
                    time.sleep(5)
                    self.wait.until(EC.presence_of_element_located((By.ID, "gen_prod_list")))

                    if page > 1:
                        nav = self.driver.find_elements(By.CSS_SELECTOR, f"a[id='pgl_gen_list_page_{page}']")
                        if nav:
                            self.driver.execute_script("arguments[0].click();", nav[0])
                            time.sleep(8)
                            self.wait.until(EC.presence_of_element_located((By.ID, "gen_prod_list")))
                            time.sleep(3)

            print(f"\n총 {len(products)}개 상품 수집 완료")
            return products

        except Exception as e:
            print(f"전체 처리 중 오류 발생: {e}")
            return products

        finally:
            print(f"[{datetime.now()}] 크롤링 완료, 드라이버 종료")
            self.driver.quit()

