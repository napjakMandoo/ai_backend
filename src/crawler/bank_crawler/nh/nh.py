import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import time
import json
from datetime import datetime
import os
import dotenv

from src.crawler.util.BankLink import BankLink


class NHBankCrawler:
    # 농협은행 예적금 상품 크롤러 초기화
    def __init__(self, headless=True):
        self.base_url = BankLink.NH_BANK_LINK.value
        self.driver = self.setup_driver(headless)
        self.all_products = []
        self.logger = logging.getLogger(__name__)

    # Chrome 브라우저 설정
    def setup_driver(self, headless=True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        driver = webdriver.Chrome(options=chrome_options)
        return driver

    # 현재 페이지 상태 디버깅
    def debug_current_page(self):
        try:
            self.logger.info("현재 페이지 디버깅")
            self.logger.info(f"URL: {self.driver.current_url}")
            self.logger.info(f"제목: {self.driver.title}")

            all_links = self.driver.find_elements(By.CSS_SELECTOR, "a")[:15]
            self.logger.info("주요 링크들:")
            for i, link in enumerate(all_links):
                try:
                    text = link.text.strip()
                    href = link.get_attribute('href') or ''
                    if text and len(text) < 30:
                        self.logger.info(f"  [{i}] '{text}' - {href[:50]}")
                except:
                    continue

            none_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="#none"]')
            self.logger.info(f"#none 링크: {len(none_links)}개")
            for i, link in enumerate(none_links[:10]):
                try:
                    text = link.text.strip()
                    if text:
                        self.logger.info(f"  [{i}] '{text}'")
                except:
                    continue

        except Exception as e:
            self.logger.info(f"디버깅 오류: {str(e)}")

    # 예금과 적금 모든 상품 크롤링
    def crawl_all_products(self):
        try:
            self.logger.info("농협은행 예금/적금 전체 크롤링 시작")

            self.driver.get(self.base_url)
            self.logger.info("페이지 로딩 중...")
            time.sleep(10)

            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='#none']"))
            )
            self.logger.info("페이지 로딩 완료")

            self.logger.info("예금 상품 수집 중...")
            deposit_products = self.crawl_product_type("예금")

            self.logger.info("적금 상품 수집 중...")
            savings_products = self.crawl_product_type("적금")

            self.all_products = deposit_products + savings_products

            self.logger.info(f"수집 완료 - 예금: {len(deposit_products)}개, 적금: {len(savings_products)}개, 총: {len(self.all_products)}개")

            return self.all_products

        except Exception as e:
            self.logger.info(f"전체 크롤링 오류: {str(e)}")
            return []

    # 특정 상품 타입(예금/적금) 크롤링
    def crawl_product_type(self, product_type):
        try:
            tab_moved = self.navigate_to_tab(product_type)

            if not tab_moved:
                self.logger.info(f"    {product_type} 탭 이동 실패 - 전체 상품에서 필터링 시도")
                return self.crawl_from_all_products(product_type)

            self.logger.info(f"    {product_type} 탭 이동 성공")

            time.sleep(3)

            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='#none']"))
                )
            except TimeoutException:
                self.logger.info(f"    {product_type} 상품 로딩 실패")
                return []

            total_pages = self.get_total_pages()
            self.logger.info(f"    {product_type} 총 페이지: {total_pages}페이지")

            all_products_data = []

            for page_num in range(1, total_pages + 1):
                try:
                    self.logger.info(f"    {page_num}페이지 처리 중...")

                    if not self.navigate_to_page(page_num):
                        self.logger.info(f"    오류: {page_num}페이지 이동 실패")
                        continue

                    page_success = self.process_page_products(product_type, page_num, all_products_data)

                    if not page_success:
                        self.logger.info(f"    오류: {page_num}페이지 처리 중 문제 발생")
                        self.navigate_to_tab(product_type)
                        time.sleep(3)

                except Exception as e:
                    self.logger.info(f"    오류: {page_num}페이지 오류: {str(e)}")
                    try:
                        self.navigate_to_tab(product_type)
                        time.sleep(3)
                    except:
                        pass
                    continue

            self.logger.info(f"    {product_type} 총 수집 상품: {len(all_products_data)}개")
            return all_products_data

        except Exception as e:
            self.logger.info(f"    {product_type} 크롤링 오류: {str(e)}")
            return []

# 한 페이지의 모든 상품 처리
    def process_page_products(self, product_type, page_num, all_products_data):
        try:
            page_products = self.get_page_product_links(product_type)
            self.logger.info(f"        {len(page_products)}개 상품 발견")

            if len(page_products) == 0:
                return True

            for i, product_info in enumerate(page_products):
                try:
                    product_name = product_info['name']

                    self.logger.info(f"    [{i+1}/{len(page_products)}] {product_name} ({product_type}) 처리 중...")

                    detailed_info = self.collect_product_details_enhanced(
                        product_name,
                        product_type,
                        len(all_products_data) + 1,
                        page_num
                    )

                    if detailed_info:
                        collected_fields = len([v for k, v in detailed_info.get('product_details', {}).items() if v])
                        collected_fields += len([v for k, v in detailed_info.get('rate_details', {}).items() if v])
                        all_products_data.append(detailed_info)
                        self.logger.info(f"        수집 완료: {collected_fields}/8개 필드")
                    else:
                        self.logger.info(f"        오류: 수집 실패")

                except Exception as e:
                    self.logger.info(f"        오류: {str(e)}")
                    continue

            return True

        except Exception as e:
            self.logger.info(f"    페이지 상품 처리 오류: {str(e)}")
            return False

    # 개별 상품 상세정보 수집
    def collect_product_details_enhanced(self, product_name, product_type, index, page_num):
        try:
            product_link = self.find_fresh_product_link(product_name)

            if not product_link:
                return None

            try:
                self.logger.info(f"        상세페이지 접근 중...")
                self.driver.execute_script("arguments[0].click();", product_link)
                time.sleep(3)
            except Exception as e:
                return None

            self.logger.info(f"        데이터 추출 중...")
            detailed_info = self.extract_complete_product_info(product_name, product_type, index)

            try:
                self.navigate_to_tab(product_type)
                time.sleep(2)

                if page_num > 1:
                    self.navigate_to_page(page_num)
                    time.sleep(2)

            except Exception as e:
                return detailed_info

            return detailed_info

        except Exception as e:
            try:
                self.navigate_to_tab(product_type)
                time.sleep(2)
                if page_num > 1:
                    self.navigate_to_page(page_num)
                    time.sleep(2)
            except:
                pass
            return None

    # 완전한 상품 정보 추출
    def extract_complete_product_info(self, product_name, product_type, index):
        try:
            product_info = {
                'index': index,
                'name': product_name,
                'product_type': product_type,
                'product_code': '',

                'product_details': {
                    '가입금액': '',
                    '가입대상': '',
                    '가입/해지안내': '',
                    '가입기간': '',
                    '세제혜택안내': '',
                    '우대금리': '',
                    '우대금리_테이블': None
                },

                'rate_details': {
                    '만기지급금리_테이블': None
                },

                'crawl_timestamp': datetime.now().isoformat()
            }

            self.extract_product_description_info(product_info)
            self.extract_rate_inquiry_info(product_info)

            return product_info

        except Exception as e:
            self.logger.info(f"        완전한 상품 정보 추출 오류: {str(e)}")
            return None

    # 상품설명 탭 정보 추출
    def extract_product_description_info(self, product_info):
        try:
            product_divs = self.driver.find_elements(By.CSS_SELECTOR, 'div.product_new')

            for div in product_divs:
                try:
                    strongs = div.find_elements(By.TAG_NAME, 'strong')

                    for strong in strongs:
                        try:
                            strong_text = strong.text.strip()
                            next_div = strong.find_element(By.XPATH, "./following-sibling::div[1]")

                            if next_div:
                                value = next_div.text.strip()

                                if strong_text == '가입대상':
                                    product_info['product_details']['가입대상'] = value
                                elif strong_text == '가입기간':
                                    product_info['product_details']['가입기간'] = value
                                elif strong_text == '가입금액':
                                    product_info['product_details']['가입금액'] = value
                                elif strong_text == '세제혜택안내':
                                    product_info['product_details']['세제혜택안내'] = value
                                elif strong_text == '가입/해지안내':
                                    product_info['product_details']['가입/해지안내'] = value
                                elif strong_text == '우대금리':
                                    product_info['product_details']['우대금리'] = value
                        except:
                            continue
                except:
                    continue

            try:
                preferential_tables = self.driver.find_elements(By.CSS_SELECTOR, 'table.tb_col.mt10.summary-done')

                if preferential_tables:
                    table = preferential_tables[0]
                    table_data = self.extract_table_data(table)
                    if table_data:
                        product_info['product_details']['우대금리_테이블'] = table_data
            except Exception as e:
                pass

        except Exception as e:
            self.logger.info(f"        상품설명 탭 추출 오류: {str(e)}")

    # 금리조회 탭으로 이동 후 만기지급금리 테이블 추출
    def extract_rate_inquiry_info(self, product_info):
        try:
            rate_tab_clicked = self.click_rate_inquiry_tab()

            if not rate_tab_clicked:
                return

            time.sleep(3)

            maturity_table = self.extract_maturity_rate_table()

            if maturity_table:
                product_info['rate_details']['만기지급금리_테이블'] = maturity_table
            else:
                product_info['rate_details']['만기지급금리_테이블'] = {
                    'headers': [],
                    'rows': [],
                    'error': '테이블 추출 실패'
                }

        except Exception as e:
            product_info['rate_details']['만기지급금리_테이블'] = {
                'headers': [],
                'rows': [],
                'error': str(e)
            }

# 금리조회 탭 클릭
    def click_rate_inquiry_tab(self):
        try:
            rate_links = self.driver.find_elements(By.TAG_NAME, 'a')

            for link in rate_links:
                try:
                    onclick = link.get_attribute('onclick')
                    text = link.text.strip()

                    if onclick and "lfSetTab('2')" in onclick and text == '금리조회':
                        link.click()
                        return True
                except:
                    continue

            try:
                self.driver.execute_script("lfSetTab('2');")
                return True
            except:
                pass

            return False

        except Exception as e:
            return False

    # 만기지급금리 테이블 추출
    def extract_maturity_rate_table(self):
        try:
            js_code = """
            function isElementVisible(element) {
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                
                return (
                    rect.width > 0 && 
                    rect.height > 0 && 
                    style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    style.opacity !== '0'
                );
            }
            
            const allTables = document.querySelectorAll('table');
            let targetTable = null;
            
            for (let i = 0; i < allTables.length; i++) {
                let table = allTables[i];
                const isVisible = isElementVisible(table);
                const text = table.textContent.trim();
                const rowCount = table.querySelectorAll('tr').length;
                const cellCount = table.querySelectorAll('td, th').length;
                
                if (isVisible && text.length > 0) {
                    const hasRateKeywords = text.includes('이자지급방식') || 
                                           text.includes('가입기간') || 
                                           text.includes('인터넷') ||
                                           text.includes('기본금리') ||
                                           text.includes('만기일시') ||
                                           text.includes('%');
                    
                    const isNotAfterMaturity = !text.includes('만기후이자') && !text.includes('만기 후');
                    const isReasonableSize = cellCount > 0 && rowCount > 0 && cellCount < 100;
                    
                    if (hasRateKeywords && isNotAfterMaturity && isReasonableSize) {
                        if (!targetTable || cellCount < targetTable.querySelectorAll('td, th').length) {
                            targetTable = table;
                        }
                    }
                }
            }
            
            return targetTable;
            """

            target_table_element = self.driver.execute_script(js_code)

            if target_table_element:
                table_data = self.extract_table_data(target_table_element)
                if table_data and (table_data['headers'] or table_data['rows']):
                    return table_data

            all_tables = self.driver.find_elements(By.TAG_NAME, 'table')

            for i, table in enumerate(all_tables):
                try:
                    if not table.is_displayed():
                        continue

                    table_text = table.text.strip()
                    if not table_text:
                        continue

                    row_count = len(table.find_elements(By.TAG_NAME, 'tr'))
                    cell_count = len(table.find_elements(By.CSS_SELECTOR, 'td, th'))

                    has_basic_keywords = any(keyword in table_text for keyword in
                                           ['이자지급방식', '가입기간', '인터넷', '기본금리', '만기일시', '%', '금리'])

                    is_not_after_maturity = '만기후이자' not in table_text and '만기 후' not in table_text
                    has_content = row_count > 0 and cell_count > 0

                    if has_basic_keywords and is_not_after_maturity and has_content:
                        table_data = self.extract_table_data(table)
                        if table_data and (table_data['headers'] or table_data['rows']):
                            return table_data

                except Exception as e:
                    continue

            for i, table in enumerate(all_tables):
                try:
                    if table.is_displayed():
                        table_text = table.text.strip()
                        if table_text and len(table_text) > 10:
                            table_data = self.extract_table_data(table)
                            if table_data:
                                return table_data
                except:
                    continue

            return None

        except Exception as e:
            return None

    # 테이블 데이터 추출
    def extract_table_data(self, table):
        try:
            table_data = {'headers': [], 'rows': []}

            first_row = table.find_element(By.TAG_NAME, 'tr')
            header_cells = first_row.find_elements(By.CSS_SELECTOR, 'th, td')

            for cell in header_cells:
                text = cell.text.strip()
                if text:
                    table_data['headers'].append(text)

            all_rows = table.find_elements(By.TAG_NAME, 'tr')

            for i, row in enumerate(all_rows[1:], 1):
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                    row_data = []

                    for cell in cells:
                        row_data.append(cell.text.strip())

                    if any(cell for cell in row_data if cell):
                        table_data['rows'].append(row_data)

                except Exception as e:
                    continue

            return table_data if (table_data['headers'] or table_data['rows']) else None

        except Exception as e:
            return None

    # 상품명으로 새로운 링크 찾기
    def find_fresh_product_link(self, product_name):
        try:
            product_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="#none"]')

            for link in product_links:
                try:
                    if link.text.strip() == product_name:
                        return link
                except:
                    continue

            return None

        except Exception as e:
            return None

    # 현재 페이지의 상품명과 링크를 함께 수집
    def get_page_product_links(self, product_type):
        try:
            products = []
            product_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="#none"]')

            for link in product_links:
                try:
                    text = link.text.strip()

                    exclude_texts = ['비교하기', '가입하기', '검색', '초기화', '더보기', '상세검색', '전체보기']

                    if any(exclude in text for exclude in exclude_texts):
                        continue

                    if len(text) < 3 or len(text) > 50:
                        continue

                    if text.isdigit():
                        continue

                    product_keywords = ['NH', '농협', '예금', '적금', '저축', '통장', '입출금', '청약', '펀드', '정기']
                    has_product_keyword = any(keyword in text for keyword in product_keywords)

                    if has_product_keyword:
                        products.append({
                            'name': text,
                            'link': link
                        })

                except Exception as e:
                    continue

            seen_names = set()
            unique_products = []
            for product in products:
                if product['name'] not in seen_names:
                    unique_products.append(product)
                    seen_names.add(product['name'])

            return unique_products

        except Exception as e:
            self.logger.info(f"상품 링크 수집 오류: {str(e)}")
            return []

    # 전체 상품에서 특정 타입만 필터링하여 크롤링
    def crawl_from_all_products(self, product_type):
        try:
            all_products = self.get_page_product_names(product_type)

            type_keywords = {
                '예금': ['예금', '통장', '입출금'],
                '적금': ['적금', '저축', '청약']
            }

            filtered_products = []
            for product in all_products:
                if any(keyword in product for keyword in type_keywords.get(product_type, [])):
                    filtered_products.append(product)

            products_data = []
            for index, product_name in enumerate(filtered_products):
                product_info = {
                    'index': index + 1,
                    'name': product_name,
                    'product_type': product_type,
                    'product_code': '',
                    'product_details': {
                        '가입금액': '',
                        '가입대상': '',
                        '가입/해지안내': '',
                        '가입기간': '',
                        '세제혜택안내': '',
                        '우대금리': '',
                        '우대금리_테이블': None
                    },
                    'rate_details': {
                        '만기지급금리_테이블': None
                    },
                    'crawl_timestamp': datetime.now().isoformat()
                }

                products_data.append(product_info)

            return products_data

        except Exception as e:
            self.logger.info(f"    전체 상품 필터링 오류: {str(e)}")
            return []

# 예금/적금 탭으로 이동
    def navigate_to_tab(self, product_type):
        try:
            tab_element = None

            all_clickables = self.driver.find_elements(By.CSS_SELECTOR, "a, button, [onclick]")

            for element in all_clickables:
                try:
                    text = element.text.strip()
                    if text == product_type:
                        tab_element = element
                        break
                except:
                    continue

            if not tab_element:
                try:
                    xpath_selector = f"//a[text()='{product_type}'] | //button[text()='{product_type}']"
                    tab_elements = self.driver.find_elements(By.XPATH, xpath_selector)

                    if tab_elements:
                        tab_element = tab_elements[0]
                except:
                    pass

            if not tab_element:
                return False

            try:
                self.driver.execute_script("arguments[0].click();", tab_element)
            except:
                tab_element.click()

            time.sleep(5)
            return True

        except Exception as e:
            return False

    # 전체 페이지 수 확인
    def get_total_pages(self):
        try:
            page_numbers = []
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, "*")

            for element in all_elements:
                text = element.text.strip()
                if (text.isdigit() and len(text) <= 2 and
                    (element.tag_name == 'a' or element.tag_name == 'button' or
                     element.get_attribute('onclick') or element.get_attribute('href'))):
                    page_numbers.append(int(text))

            if page_numbers:
                total_pages = max(page_numbers)
                return min(total_pages, 10)
            else:
                return 1

        except Exception as e:
            return 1

    # 특정 페이지로 이동
    def navigate_to_page(self, page_num):
        try:
            if page_num == 1:
                return True

            page_link = None
            all_links = self.driver.find_elements(By.CSS_SELECTOR, "a, button, [onclick]")

            for link in all_links:
                if link.text.strip() == str(page_num):
                    page_link = link
                    break

            if page_link:
                self.driver.execute_script("arguments[0].click();", page_link)
                time.sleep(3)
                return True
            else:
                return False

        except Exception as e:
            return False

    # 현재 페이지의 상품명들 수집
    def get_page_product_names(self, product_type):
        try:
            product_names = []
            product_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="#none"]')

            for link in product_links:
                try:
                    text = link.text.strip()

                    exclude_texts = ['비교하기', '가입하기', '검색', '초기화', '더보기', '상세검색', '전체보기']

                    if any(exclude in text for exclude in exclude_texts):
                        continue

                    if len(text) < 3 or len(text) > 50:
                        continue

                    if text.isdigit():
                        continue

                    product_keywords = ['NH', '농협', '예금', '적금', '저축', '통장', '입출금', '청약', '펀드', '정기']
                    has_product_keyword = any(keyword in text for keyword in product_keywords)

                    if has_product_keyword:
                        product_names.append(text)

                except Exception as e:
                    continue

            unique_products = list(dict.fromkeys(product_names))

            return unique_products

        except Exception as e:
            self.logger.info(f"상품명 수집 오류: {str(e)}")
            return []



    # 수집 결과 요약 출력
    def print_summary(self):
        self.logger.info("수집 결과 요약")

        total_products = len(self.all_products)
        deposit_count = len([p for p in self.all_products if p['product_type'] == '예금'])
        savings_count = len([p for p in self.all_products if p['product_type'] == '적금'])

        self.logger.info(f"전체 상품: {total_products}개")
        self.logger.info(f"예금: {deposit_count}개")
        self.logger.info(f"적금: {savings_count}개")

        successful_details = 0
        field_stats = {
            '가입금액': 0, '가입대상': 0, '가입/해지안내': 0, '가입기간': 0,
            '세제혜택안내': 0, '우대금리': 0, '우대금리_테이블': 0, '만기지급금리_테이블': 0
        }

        for product in self.all_products:
            detail_info = product.get('product_details', {})
            rate_info = product.get('rate_details', {})
            if detail_info or rate_info:
                successful_details += 1
                for field in ['가입금액', '가입대상', '가입/해지안내', '가입기간', '세제혜택안내', '우대금리']:
                    if detail_info.get(field):
                        field_stats[field] += 1
                if detail_info.get('우대금리_테이블'):
                    field_stats['우대금리_테이블'] += 1
                if rate_info.get('만기지급금리_테이블'):
                    field_stats['만기지급금리_테이블'] += 1

        self.logger.info("상세정보 수집 현황:")
        self.logger.info(f"성공: {successful_details}개 ({successful_details/total_products*100:.1f}%)")
        for field, count in field_stats.items():
            self.logger.info(f"{field}: {count}개")

        url_count = len([p for p in self.all_products])
        self.logger.info(f"URL: {url_count}개")

    # 크롤링 실행
    def run(self):
        try:
            start_time = datetime.now()

            self.logger.info("농협은행 예금/적금 크롤링 시작")
            self.logger.info(f"실행 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            self.crawl_all_products()

            if not self.all_products:
                self.logger.info("상품 목록을 수집하지 못했습니다.")
                return None

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.logger.info("크롤링 완료")
            self.logger.info(f"소요 시간: {duration:.1f}초")

            self.print_summary()


            return {
                'timestamp': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_seconds': duration,
                'total_products': len(self.all_products),
                'deposit_count': len([p for p in self.all_products if p['product_type'] == '예금']),
                'savings_count': len([p for p in self.all_products if p['product_type'] == '적금'])
            }

        except Exception as e:
            self.logger.info(f"크롤링 오류: {str(e)}")
            return None
        finally:
            self.driver.quit()

    def start(self):
        self.logger.info("농협은행 예금/적금 크롤러 v2.0")
        self.logger.info("예금 + 적금 전체 수집")
        self.logger.info("8개 필수 항목 구조화 추출")

        result = self.run()

        if result:
            self.logger.info("크롤링 성공")
            self.logger.info(f"파일: nh_bank_products.json")
            self.logger.info(f"예금 {result['deposit_count']}개 + 적금 {result['savings_count']}개 = 총 {result['total_products']}개")
            return self.all_products
        else:
            self.logger.info("크롤링 실패")

