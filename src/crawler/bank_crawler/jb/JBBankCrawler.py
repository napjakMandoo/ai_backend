from __future__ import annotations

from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import logging
import sys
import os
import re

# crawlingUtil import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from crawlingUtil import CrawlingUtil
except ImportError:
    print("Warning: crawlingUtil을 찾을 수 없습니다. 기본 기능만 사용합니다.")
    CrawlingUtil = None


class JBBankCrawler:
    def __init__(self, headless: bool = True, timeout: int = 10, base_url: str = ""):
        self.headless = headless
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

        self.driver = self._create_driver()
        self.wait = WebDriverWait(self.driver, timeout)
        self.base_url = base_url

        if CrawlingUtil:
            self.util = CrawlingUtil(self.driver)
        else:
            self.util = None

        self.processed_products = set()

        self.tab_mapping = {
            '입출금': 'P_M_IOMN_MALL',
            '예금': 'P_M_SID_MALL',
            '적금': 'P_M_SVMN_MALL'
        }

    def _create_driver(self) -> webdriver.Chrome:
        """Chrome 드라이버 생성"""
        opts = Options()

        if self.headless:
            opts.add_argument("--headless=new")

        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )

        try:
            driver = webdriver.Chrome(options=opts)
            self.logger.info("Chrome 드라이버 생성 완료")
            return driver
        except Exception as e:
            self.logger.error(f"Chrome 드라이버 생성 실패: {e}")
            raise

    def extract_deposit_info(self, html_content: str) -> dict:
        """예금 상품 HTML에서 정보를 추출합니다."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. JavaScript TASK.DATA 객체에서 기본 정보 추출
        script_tags = soup.find_all('script', type='text/javascript')
        task_data = {}

        for script in script_tags:
            script_text = script.string
            if script_text and 'TASK = {' in script_text:
                # 정규식으로 개별 추출
                patterns = {
                    'GDS_NM': r'"GDS_NM":"([^"]+)"',
                    'ITEM0033': r'"ITEM0033":"([^"]+)"',
                    'ITEM0004': r'"ITEM0004":"([^"]+)"',
                    'ITEM0005': r'"ITEM0005":"([^"]+)"',
                    'ITEM0088': r'"ITEM0088":"([^"]+)"',
                    'ITEM0090': r'"ITEM0090":"([^"]+)"',
                    'ITEM0092': r'"ITEM0092":"([^"]+)"',
                    'ITEM0093': r'"ITEM0093":"([^"]+)"',
                    'ITEM0094': r'"ITEM0094":"([^"]+)"',
                    'ITEM0095': r'"ITEM0095":"([^"]+)"',
                }

                for key, pattern in patterns.items():
                    match = re.search(pattern, script_text)
                    if match:
                        task_data[key] = match.group(1)
                break

        # 2. 상품 정보 구조
        product_info = {
            'product_name': '',
            'product_subtitle': '',
            'base_rate': '',
            'max_rate': '',
            'period': '',
            'min_amount': '',
            'max_amount': '',
            'target': '',
            'features': [],
            'special_services': [],
            'interest_payment': '',
            'crawled_at': datetime.now().isoformat(),
        }

        # TASK.DATA에서 기본 정보
        if task_data:
            product_info['product_name'] = task_data.get('GDS_NM', '') or task_data.get('ITEM0033', '')
            product_info['base_rate'] = task_data.get('ITEM0094', '') or task_data.get('ITEM0004', '')

            # 최고금리
            base = task_data.get('ITEM0094', '') or task_data.get('ITEM0004', '')
            prime = task_data.get('ITEM0095', '')
            if base and prime:
                try:
                    max_rate = float(base) + float(prime)
                    product_info['max_rate'] = str(max_rate)
                except:
                    product_info['max_rate'] = task_data.get('ITEM0005', '')
            else:
                product_info['max_rate'] = task_data.get('ITEM0005', '')

            product_info['period'] = task_data.get('ITEM0088', '')
            product_info['min_amount'] = task_data.get('ITEM0092', '')
            product_info['max_amount'] = task_data.get('ITEM0093', '')

        # 3. 메인 제목과 부제목
        visual_tit = soup.find('span', class_='onPdCatalInfoVisual_tit')
        if visual_tit:
            product_info['product_subtitle'] = visual_tit.get_text(strip=True).replace('\n', ' ')

        # 4. 상품정보 섹션
        prod_desc_items = soup.find_all('li', class_='prodDescCont_item')

        for item in prod_desc_items:
            tit_elem = item.find('span', class_='prodDescCont_tit')
            if not tit_elem:
                continue

            title = tit_elem.get_text(strip=True)
            content_elem = item.find('div', class_='prodDescCont_content')

            if not content_elem:
                continue

            text_elems = content_elem.find_all('span', class_='prodDescCont_text')
            texts = [elem.get_text(strip=True) for elem in text_elems]

            if title == '가입대상':
                product_info['target'] = '\n'.join(texts) if texts else content_elem.get_text(strip=True)
            elif title == '가입기간':
                product_info['period'] = texts[0] if texts else content_elem.get_text(strip=True)
            elif title == '가입금액':
                product_info['min_amount'] = texts[0] if texts else content_elem.get_text(strip=True)
            elif title == '이자지급시기':
                product_info['interest_payment'] = texts[0] if texts else content_elem.get_text(strip=True)
            elif title == '우대서비스':
                product_info['special_services'] = texts if texts else [content_elem.get_text(strip=True)]
            elif title == '상품특징' or title == '특징':
                product_info['features'] = texts if texts else [content_elem.get_text(strip=True)]

        # 5. 특징 메시지
        visual_subtits = soup.find_all('span', class_='onPdCatalInfoVisual_subTit')
        for subtit in visual_subtits[:3]:
            text = subtit.get_text(strip=True).replace('\n', ' ')
            if text and len(text) > 10 and len(text) < 300:
                if text not in product_info['features']:
                    product_info['features'].append(text)

        # 빈 리스트/값 제거
        for key in list(product_info.keys()):
            if isinstance(product_info[key], list) and not product_info[key]:
                del product_info[key]
            elif isinstance(product_info[key], str) and not product_info[key]:
                del product_info[key]

        return product_info

    def extract_product_info(self, html_content: str, tab: str) -> dict:
        """탭에 따라 적절한 추출 방법 선택"""
        if tab == '예금':
            return self.extract_deposit_info(html_content)
        elif tab == '적금':
            # 적금도 예금과 유사한 구조
            return self.extract_deposit_info(html_content)
        elif tab == '입출금':
            # 입출금도 예금과 유사한 구조
            return self.extract_deposit_info(html_content)
        else:
            return {}

    def go_to_tab_page(self, tab_name: str) -> bool:
        """탭 페이지로 직접 이동"""
        target_url = self.tab_mapping.get(tab_name)
        if not target_url:
            return False

        try:
            full_url = f"https://m.jbbank.co.kr/JBN/{target_url}"
            self.driver.get(full_url)
            time.sleep(3)
            self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            return True
        except:
            return False

    def click_tab(self, tab_name: str, max_retries: int = 3) -> bool:
        """탭 클릭"""
        target_url = self.tab_mapping.get(tab_name)
        if not target_url:
            return False

        for attempt in range(max_retries):
            try:
                xpath = f"//label[@role='tab']//span[@class='base' and text()='{tab_name}']"
                label_span = self.driver.find_element(By.XPATH, xpath)
                label = label_span.find_element(By.XPATH, "..")

                if label.get_attribute('aria-selected') == 'true':
                    self.logger.info(f"'{tab_name}' 탭이 이미 활성화되어 있습니다")
                    return True

                input_elem = label.find_element(By.XPATH, f".//input[@targeturl='{target_url}']")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", input_elem)
                time.sleep(3)
                return True
            except:
                if attempt < max_retries - 1:
                    if self.go_to_tab_page(tab_name):
                        return True
                    time.sleep(2)

        return False

    def scroll_to_load_all_products(self):
        """페이지 스크롤"""
        try:
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
        except:
            pass

    def get_all_product_ids(self) -> list:
        """모든 상품 ID 반환"""
        try:
            elems = self.driver.find_elements(By.CSS_SELECTOR, "button.mallList")
            return [elem.get_attribute('id') for elem in elems if elem.get_attribute('id')]
        except:
            return []

    def get_product_by_id(self, product_id: str):
        """ID로 상품 요소 가져오기"""
        try:
            return self.driver.find_element(By.CSS_SELECTOR, f"button.mallList[id='{product_id}']")
        except:
            return None

    def start(self):
        """크롤링 시작 - 상품 정보 리스트 반환"""
        self.logger.info("전북은행 금융상품몰 크롤링 시작")
        products = []

        try:
            self.logger.info(f"페이지 접속 중: {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(5)
            self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

            tabs = ['입출금', '예금', '적금']

            for tab_name in tabs:
                self.logger.info(f"=== {tab_name} 탭 처리 시작 ===")

                # 탭 클릭
                clicked = self.click_tab(tab_name, max_retries=3)
                if not clicked:
                    self.logger.error(f"{tab_name} 탭 접근 실패, 건너뜁니다")
                    continue

                time.sleep(3)
                self.scroll_to_load_all_products()

                # 상품 ID 목록 가져오기
                product_ids = self.get_all_product_ids()
                if not product_ids:
                    self.logger.error(f"{tab_name} 탭에서 상품을 찾을 수 없습니다")
                    continue

                self.logger.info(f"{tab_name} 탭에서 {len(product_ids)}개 상품 발견")

                processed_count = 0
                failed_count = 0

                for idx, product_id in enumerate(product_ids, start=1):
                    self.logger.info(f"상품 {idx}/{len(product_ids)} (ID: {product_id}) 처리 중...")

                    # 이미 처리한 상품인지 확인
                    if product_id in self.processed_products:
                        self.logger.info(f"상품 {product_id}는 이미 처리됨, 건너뜁니다")
                        continue

                    try:
                        # 페이지 재로드 (연속 실패 시)
                        if failed_count >= 2:
                            self.logger.warning(f"연속 {failed_count}번 실패, 페이지 재로드...")
                            self.go_to_tab_page(tab_name)
                            time.sleep(2)
                            self.scroll_to_load_all_products()
                            failed_count = 0

                        # ID로 요소 찾기
                        elem = self.get_product_by_id(product_id)
                        if elem is None:
                            self.logger.warning(f"상품 {product_id}를 찾을 수 없습니다")
                            failed_count += 1
                            continue

                        failed_count = 0
                        original = self.driver.current_window_handle

                        # 상품 버튼 클릭
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                            elem
                        )
                        time.sleep(0.5)

                        # 새 탭으로 열기
                        try:
                            ActionChains(self.driver).key_down(Keys.CONTROL).click(
                                elem
                            ).key_up(Keys.CONTROL).perform()
                            time.sleep(1.5)
                        except:
                            self.driver.execute_script("arguments[0].click();", elem)
                            time.sleep(1.5)

                        # 새 창으로 전환
                        if len(self.driver.window_handles) > 1:
                            for win in self.driver.window_handles:
                                if win != original:
                                    self.driver.switch_to.window(win)
                                    break

                        self.wait.until(
                            lambda d: d.execute_script("return document.readyState") == "complete"
                        )
                        time.sleep(1)

                        # 상품 정보 추출
                        product_info = self.extract_product_info(self.driver.page_source, tab_name)

                        # 추가 메타 정보
                        product_info['tab'] = tab_name
                        product_info['product_id'] = product_id
                        product_info['url'] = self.driver.current_url

                        # 리스트에 추가
                        products.append(product_info)
                        self.processed_products.add(product_id)
                        processed_count += 1

                        self.logger.info(f"상품 {idx} 정보 수집 완료")

                        # 창 닫기
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                            self.driver.switch_to.window(original)
                            time.sleep(0.5)
                        else:
                            self.driver.back()
                            time.sleep(1.5)

                        self.wait.until(
                            lambda d: d.execute_script("return document.readyState") == "complete"
                        )
                        time.sleep(0.5)
                        self.scroll_to_load_all_products()

                    except Exception as detail_err:
                        self.logger.error(f"상품 {product_id} 크롤링 실패: {detail_err}")
                        failed_count += 1
                        try:
                            if len(self.driver.window_handles) > 1:
                                self.driver.close()
                                self.driver.switch_to.window(original)
                        except:
                            pass

                self.logger.info(f"{tab_name} 탭 처리 완료 ({processed_count}개 수집)")

            self.logger.info(f"전체 크롤링 완료: 총 {len(products)}개 상품 수집")
            return products

        except Exception as e:
            self.logger.error(f"크롤링 중 오류: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return products

        finally:
            self.logger.info(f"[{datetime.now()}] 드라이버 종료")
            try:
                self.driver.quit()
            except:
                pass


if __name__ == "__main__":
    import json

    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('jbbank_crawler.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    print("=" * 60)
    print("전북은행 크롤러 시작")
    print("=" * 60)

    base_url = "https://m.jbbank.co.kr/JBN/P_M_IOMN_MALL"

    try:
        crawler = JBBankCrawler(headless=True, timeout=10, base_url=base_url)
        products = crawler.start()

        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"jbbank_products_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 60}")
        print(f"크롤링 완료!")
        print(f"총 {len(products)}개 상품 수집")
        print(f"결과 파일: {output_file}")
        print('=' * 60)

        # 탭별 통계
        from collections import Counter

        tab_counts = Counter(p['tab'] for p in products)
        print("\n탭별 수집 현황:")
        for tab, count in tab_counts.items():
            print(f"  {tab}: {count}개")

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()