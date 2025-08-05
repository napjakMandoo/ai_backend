from __future__ import annotations

from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from src.crawler.util.crawlingUtil import CrawlingUtil
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

class PostBankCrawler:
    def __init__(self, headless: bool = True, timeout: int = 30, base_url:str=""):
        self.headless = headless
        self.timeout  = timeout
        self.driver   = self._create_driver()
        self.wait     = WebDriverWait(self.driver, timeout)
        self.base_url = base_url
        self.util = CrawlingUtil(self.driver)
        self.processed_products = set()
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
        self.logger.info("우체국 금융상품몰 크롤링 시작")
        products = []
        try:
            self.driver.get(self.base_url)
            time.sleep(5)
            self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

            tabs = ['예금', '적금']
            for tab_name in tabs:
                self.logger.info(f"=== {tab_name} 탭 처리 시작 ===")

                clicked = False
                tab_selectors = [
                    f"//div[@class='tab_menu_type1 first_section']//a[contains(text(), '{tab_name}')]",
                    f"//a[@data-tab_id and contains(text(), '{tab_name}')]",
                    f"//a[@id='dt' and contains(text(), '예금')]" if tab_name == '예금' else f"//a[@id='ct' and contains(text(), '적금')]",
                    f"//a[contains(text(), '{tab_name}')]",
                    f"//li/a[contains(text(), '{tab_name}')]"
                ]

                for selector in tab_selectors:
                    try:
                        tab_el = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        if 'current' in (tab_el.get_attribute('class') or ''):
                            clicked = True
                            break
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", tab_el
                        )
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", tab_el)
                        time.sleep(3)
                        if 'current' in (tab_el.get_attribute('class') or ''):
                            clicked = True
                            break
                    except Exception:
                        continue
                if not clicked:
                    self.logger.error(f"{tab_name} 탭 클릭 실패, 건너뜁니다")
                    continue

                time.sleep(3)
                try:
                    container = self.wait.until(
                        EC.presence_of_element_located((By.CLASS_NAME, "acco_inner"))
                    )
                except Exception:
                    self.logger.error(f"{tab_name} 탭의 상품 컨테이너 로드 실패")
                    continue

                elems = self.driver.find_elements(By.CSS_SELECTOR, ".ch_product.exist_prod")

                self.logger.info(f"{tab_name} 탭에서 {len(elems)}개 상품 발견")
                for idx, elem in enumerate(elems, start=1):
                    self.logger.info(f"상품 {idx} 처리 중...")

                    try:
                        original = self.driver.current_window_handle
                        # 상세보기 버튼 찾기
                        detail_btn = None
                        for sel in [
                            ".btnIPDGDI0000",
                            "xpath=.//a[contains(text(), '상세보기')]"
                        ]:
                            try:
                                if sel.startswith('xpath='):
                                    detail_btn = elem.find_element(By.XPATH, sel.replace('xpath=', ''))
                                else:
                                    detail_btn = elem.find_element(By.CSS_SELECTOR, sel)
                                if detail_btn.is_displayed():
                                    break
                            except:
                                continue

                        if detail_btn:
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", detail_btn
                            )
                            time.sleep(1)
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                from selenium.webdriver.common.keys import Keys
                                ActionChains(self.driver).key_down(Keys.CONTROL).click(detail_btn).key_up(
                                    Keys.CONTROL).perform()
                            except:
                                detail_btn.click()
                            time.sleep(3)

                            for win in self.driver.window_handles:
                                if win != original:
                                    self.driver.switch_to.window(win)
                                    break
                            self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                            time.sleep(2)

                            # extract_content_text를 사용해서 상품 정보를 추출하고 products 리스트에 추가
                            product_info = self.util.extract_content_text(self.driver.page_source)
                            products.append(product_info)
                            self.logger.info(f"상품 {idx} 정보 수집 완료")

                            if len(self.driver.window_handles) > 1:
                                self.driver.close()
                                self.driver.switch_to.window(original)
                            else:
                                self.driver.back()
                                time.sleep(2)
                    except Exception as detail_err:
                        self.logger.error(f"상품 {idx} 크롤링 실패: {detail_err}")
                        try:
                            if len(self.driver.window_handles) > 1:
                                self.driver.close()
                                self.driver.switch_to.window(original)
                        except:
                            pass

                self.logger.info(f"{tab_name} 탭 처리 완료")

            self.logger.info(f"전체 크롤링 완료: 총 {len(products)}개 상품 수집")
            return products

        except Exception as e:
            self.logger.error(f"크롤링 중 오류: {e}")
            return products

        finally:
            self.logger.info(f"[{datetime.now()}] 드라이버 종료")
            self.driver.quit()