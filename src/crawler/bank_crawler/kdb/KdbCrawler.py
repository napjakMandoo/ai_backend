
from __future__ import annotations

import time
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.crawler.util.crawlingUtil import CrawlingUtil


class KdbCrawler:
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
        self.logger.info("KDB산업은행 금융상품몰 크롤링 시작")
        products = []
        try:
            self.driver.get(self.base_url)
            time.sleep(7)  # 페이지 로딩 시간 증가
            try:
                self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                # 추가로 특정 요소가 로드될 때까지 대기
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                self.logger.info("금융상품몰 페이지 로딩 완료")
            except:
                self.logger.error("페이지 로딩 대기 중 타임아웃 발생, 계속 진행...")

            # 1단계: 금융상품몰 클릭
            self.logger.info("금융상품몰 메뉴 클릭 시도...")
            financial_product_clicked = False

            # 더 구체적인 선택자로 금융상품몰 링크 찾기
            financial_selectors = [
                "//nav[@id='gnb']//a[@href='javascript:_menu.goitbbm();']",
                "//ul[@class='menu']//a[@href='javascript:_menu.goitbbm();']",
                "//a[@href='javascript:_menu.goitbbm();']//span[text()='금융상품몰']/..",
                "//span[text()='금융상품몰']/parent::a",
                "//li//a[contains(@href, 'goitbbm')]"
            ]

            # 먼저 네비게이션이 로드될 때까지 대기
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, "gnb")))
                self.logger.info("네비게이션 메뉴 로드 완료")
            except:
                self.logger.error("네비게이션 메뉴 로드 실패")

            for i, selector in enumerate(financial_selectors, 1):
                try:
                    self.logger.info(f"금융상품몰 링크 찾기 시도 {i}...")
                    financial_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    self.logger.info(f"금융상품몰 링크 발견: {financial_link.get_attribute('href')}")

                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        financial_link
                    )
                    time.sleep(2)

                    # JavaScript 함수 직접 실행을 우선 시도
                    try:
                        self.logger.info("JavaScript 함수 직접 실행 시도...")
                        self.driver.execute_script("_menu.goitbbm();")
                        self.logger.info("JavaScript 함수로 금융상품몰 이동 성공")
                        financial_product_clicked = True
                        break
                    except Exception as js_err:
                        self.logger.error(f"JavaScript 함수 실행 실패: {js_err}")
                        # JavaScript 함수 실행 실패 시 클릭 시도
                        try:
                            self.logger.error("일반 클릭 시도...")
                            self.driver.execute_script("arguments[0].click();", financial_link)
                            self.logger.error("클릭으로 금융상품몰 이동 성공")
                            financial_product_clicked = True
                            break
                        except Exception as click_err:
                            self.logger.error(f"클릭도 실패: {click_err}")
                            continue

                except Exception as e:
                    self.logger.error(f"금융상품몰 링크 {i} 시도 실패: {str(e)[:100]}...")
                    continue

            if not financial_product_clicked:
                self.logger.info("금융상품몰 메뉴 클릭 실패")
                return products

            time.sleep(5)
            self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        except Exception as e:
            self.logger.info(e)