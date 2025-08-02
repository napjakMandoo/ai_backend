import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import warnings
import os
import dotenv
import os
from src.preprocessing.crawling.BankLink import BankLink

warnings.filterwarnings('ignore')

class IBKFullCrawler:
    def __init__(self):
        self.base_url = BankLink.IBK_BANK_LINK.value
        
        # 적금 상품 (목돈모으기) - 3페이지, 28개 상품
        self.savings_url = BankLink.IBK_BANK_SAVINGS_LINK.value
        self.savings_pages = 3
        
        # 예금 상품 (목돈굴리기) - 2페이지, 17개 상품
        self.deposits_url = BankLink.IBK_BANK_DEPOSIT_LINK.value
        self.deposits_pages = 2
        
        self.driver = None
        self.all_products = []
        
    def setup_driver(self):
        """WebDriver 설정"""
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        # 안정성을 위해 헤드리스 모드 활성화
        options.add_argument('--headless')
        
        try:
            possible_paths = [
                '/opt/homebrew/bin/chromedriver',
                '/usr/local/bin/chromedriver',
            ]
            
            driver_created = False
            for path in possible_paths:
                try:
                    if os.path.exists(path):
                        service = Service(path)
                        self.driver = webdriver.Chrome(service=service, options=options)
                        driver_created = True
                        break
                except:
                    continue
            
            if not driver_created:
                self.driver = webdriver.Chrome(options=options)
            
            self.driver.implicitly_wait(5)
            
            print("✅ WebDriver 설정 완료")
            return True
            
        except Exception as e:
            print(f"❌ WebDriver 설정 실패: {e}")
            return False

    def crawl_all_products(self):
        """적금과 예금 상품 모두 크롤링"""
        print("🚀 === ibk 적금/예금 전체 크롤러 (기간별 금리 포함) ===")
        print("📋 목돈모으기(적금) 28개 + 목돈굴리기(예금) 17개 = 총 45개")
        print("🎯 수집 정보: 가입금액, 가입대상, 가입방법, 가입기간, 금리, 우대조건, 기간별금리 등\n")
        
        if not self.setup_driver():
            return {}
        
        try:
            results = {
                'crawl_info': {
                    'crawl_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'target_pages': {
                        'savings': self.savings_pages,
                        'deposits': self.deposits_pages
                    },
                    'total_expected': 45  # 28 + 17
                },
                'products': []  # 통합된 상품 리스트
            }
            
            # 1. 적금 상품 크롤링 (목돈모으기)
            print("💰 === 적금 상품 크롤링 시작 ===")
            savings_products = self.crawl_product_category(
                category_name="적금",
                base_url=self.savings_url,
                max_pages=self.savings_pages
            )
            
            # 2. 예금 상품 크롤링 (목돈굴리기)
            print("\n🏦 === 예금 상품 크롤링 시작 ===")
            deposits_products = self.crawl_product_category(
                category_name="예금",
                base_url=self.deposits_url,
                max_pages=self.deposits_pages
            )
            
            # 3. 통합 결과 구성
            all_products = savings_products + deposits_products
            results['products'] = all_products
            results['crawl_info']['actual_collected'] = len(all_products)
            results['crawl_info']['savings_count'] = len(savings_products)
            results['crawl_info']['deposits_count'] = len(deposits_products)
            
            print(f"\n🎉 전체 크롤링 완료!")
            print(f"📊 적금 상품: {len(savings_products)}개")
            print(f"📊 예금 상품: {len(deposits_products)}개")
            print(f"📊 총합: {len(all_products)}개")
            
            return results
            
        except Exception as e:
            print(f"❌ 크롤링 중 오류: {e}")
            return {}
        finally:
            if self.driver:
                self.driver.quit()

    def crawl_product_category(self, category_name, base_url, max_pages):
        """특정 카테고리의 모든 페이지 크롤링"""
        category_products = []
        seen_products = set()
        
        for page_num in range(1, max_pages + 1):
            print(f"\n{'='*60}")
            print(f"📄 {category_name} 페이지 {page_num}/{max_pages}")
            print(f"{'='*60}")
            
            # 페이지 이동
            success = self.navigate_to_page(category_name, base_url, page_num)
            
            if not success:
                print(f"❌ 페이지 {page_num} 이동 실패")
                continue
            
            # 페이지 로딩 완료 대기
            time.sleep(3)
            
            try:
                # 상품 목록 추출
                page_products = self.extract_products_from_current_page()
                
                if not page_products:
                    print(f"❌ 페이지 {page_num}에서 상품을 찾을 수 없습니다")
                    continue
                
                print(f"📦 페이지 {page_num}에서 {len(page_products)}개 상품 발견")
                
                # 중복 상품 필터링
                new_products = []
                for product in page_products:
                    product_key = product['name']
                    if product_key not in seen_products:
                        seen_products.add(product_key)
                        new_products.append(product)
                    else:
                        print(f"    ⚠️ 중복 상품 스킵: {product_key}")
                
                if not new_products:
                    print(f"⚠️ 페이지 {page_num}에 새로운 상품이 없습니다!")
                
                # 각 상품의 상세 정보 수집
                for i, product in enumerate(new_products, 1):
                    global_index = len(category_products) + 1
                    print(f"\n[{category_name} {global_index}] {product['name']}")
                    
                    # 상품 간 대기 (첫 번째 제외)
                    if i > 1:
                        print(f"    ⏳ 상품 간 대기...")
                        time.sleep(2)
                    
                    # 상세 정보 수집
                    detail_info = self.get_product_detail(product, category_name)
                    
                    if detail_info:
                        category_products.append(detail_info)
                        print(f"    ✅ 상세 정보 수집 완료")
                        
                        # 기간별 금리 수집 결과 요약
                        if detail_info.get('기간별금리'):
                            print(f"    📊 기간별금리 {len(detail_info['기간별금리'])}개 수집")
                        else:
                            print(f"    📋 기간별금리: 없음")
                            
                        # 우대조건 수집 결과 요약
                        if detail_info.get('우대조건'):
                            print(f"    🎯 우대조건 {len(detail_info['우대조건'])}개 수집")
                        else:
                            print(f"    📝 우대조건: 없음")
                    else:
                        print(f"    ❌ 상세 정보 수집 실패")
                
                print(f"✅ {category_name} 페이지 {page_num} 완료: {len(new_products)}개 신규 상품")
                time.sleep(2)  # 페이지 간 대기
                
            except Exception as e:
                print(f"❌ {category_name} 페이지 {page_num} 처리 실패: {e}")
                continue
        
        return category_products

    def navigate_to_page(self, category_name, base_url, page_num):
        """페이지네이션을 사용하여 특정 페이지로 이동"""
        try:
            if page_num == 1:
                # 첫 페이지는 직접 접속
                page_url = self.base_url + base_url
                print(f"🌐 첫 페이지 접속: {page_url}")
                self.driver.get(page_url)
                time.sleep(3)
                return True
            
            # 2페이지 이상일 경우 페이지네이션 버튼 클릭
            print(f"🔍 페이지 {page_num} 버튼 찾는 중...")
            
            # 페이지네이션 버튼 찾기
            pagination_selectors = [
                f"//a[text()='{page_num}']",
                f"//button[text()='{page_num}']",
                f"//span[text()='{page_num}']/parent::a",
                f"//li/a[text()='{page_num}']",
                f"//*[contains(@class, 'page') and text()='{page_num}']",
            ]
            
            page_button = None
            
            for i, selector in enumerate(pagination_selectors, 1):
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            page_button = element
                            print(f"      ✅ 페이지 {page_num} 버튼 발견!")
                            break
                    
                    if page_button:
                        break
                        
                except Exception as e:
                    continue
            
            # 페이지 버튼을 찾지 못한 경우 JavaScript로 페이지 이동 시도
            if not page_button:
                print(f"      🔍 JavaScript 페이지 이동 시도...")
                
                js_functions = [
                    f"goPage({page_num})",
                    f"movePage({page_num})",
                    f"pageMove({page_num})",
                    f"fn_goPage({page_num})",
                ]
                
                for js_func in js_functions:
                    try:
                        self.driver.execute_script(js_func)
                        time.sleep(3)
                        
                        if self.verify_page_change(page_num):
                            print(f"      ✅ JavaScript로 페이지 {page_num} 이동 성공!")
                            return True
                            
                    except Exception as e:
                        continue
                
                print(f"      ❌ 페이지 {page_num} 이동 실패")
                return False
            
            # 페이지 버튼 클릭
            try:
                print(f"      🖱️ 페이지 {page_num} 버튼 클릭...")
                page_button.click()
                time.sleep(3)
                
                if self.verify_page_change(page_num):
                    print(f"      ✅ 페이지 {page_num} 이동 성공!")
                    return True
                else:
                    print(f"      ❌ 페이지 {page_num} 이동 실패")
                    return False
                
            except Exception as e:
                print(f"      ❌ 페이지 버튼 클릭 오류: {e}")
                return False
                
        except Exception as e:
            print(f"❌ 페이지 {page_num} 이동 전체 오류: {e}")
            return False

    def verify_page_change(self, expected_page):
        """페이지 변경 확인"""
        try:
            time.sleep(2)
            
            # 현재 상품 목록 확인
            try:
                products = self.driver.find_elements(By.CSS_SELECTOR, "a.stit")
                if len(products) > 0:
                    first_product = products[0].get_attribute('textContent').strip()
                    if hasattr(self, 'last_first_product'):
                        if first_product != self.last_first_product:
                            print(f"      ✅ 상품 목록 변화 확인: '{first_product}'")
                            self.last_first_product = first_product
                            return True
                        else:
                            print(f"      ⚠️ 동일한 첫 상품: '{first_product}'")
                            return False
                    else:
                        self.last_first_product = first_product
                        return True
            except:
                pass
            
            return True
            
        except Exception as e:
            print(f"      ❌ 페이지 변경 확인 오류: {e}")
            return True

    def extract_products_from_current_page(self):
        """현재 페이지에서 상품 목록 추출"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            products = []
            
            # 상품 링크 찾기
            product_links = soup.find_all('a', class_='stit')
            
            for link in product_links:
                product_name = link.get_text(strip=True)
                onclick = link.get('onclick', '')
                
                if product_name and 'uf_showDetail' in onclick:
                    params = self.parse_onclick_params(onclick)
                    if params:
                        products.append({
                            'name': product_name,
                            'params': params
                        })
            
            return products
            
        except Exception as e:
            print(f"❌ 상품 추출 오류: {e}")
            return []

    def parse_onclick_params(self, onclick_str):
        """onclick에서 파라미터 추출"""
        pattern = r"uf_showDetail\s*\(\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\s*\)"
        match = re.search(pattern, onclick_str)
        
        if match:
            return {
                'param1': match.group(1),
                'param2': match.group(2),
                'param3': match.group(3),
                'param4': match.group(4),
                'param5': match.group(5),
                'param6': match.group(6)
            }
        return None

    def get_product_detail(self, product, category_name):
        """상품 상세 정보 수집"""
        try:
            params = product['params']
            original_url = self.driver.current_url
            
            print(f"    🔍 상세 정보 수집 중...")
            
            # JavaScript 실행하여 상세 페이지 접속
            script = f"""
            try {{
                uf_showDetail('{params['param1']}', '{params['param2']}', '{params['param3']}', 
                             '{params['param4']}', '{params['param5']}', '{params['param6']}');
                return true;
            }} catch(e) {{
                console.error('상세페이지 오류:', e);
                return false;
            }}
            """
            
            js_result = self.driver.execute_script(script)
            
            if not js_result:
                print(f"    ❌ JavaScript 실행 실패")
                return None
            
            # 페이지 변화 대기
            time.sleep(4)
            
            # 상세 정보 추출
            detail_info = self.extract_detail_info(product['name'], category_name, original_url)
            
            # 원래 페이지로 복귀
            self.return_to_original_page(original_url)
            
            return detail_info
                
        except Exception as e:
            print(f"    ❌ 상세 정보 수집 오류: {str(e)[:50]}...")
            return None

    def extract_detail_info(self, product_name, category_name, original_url):
        """상세 정보 추출 (기간별 금리 포함)"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 기본 정보 구성
            product_info = {
                "은행명": "기업은행",
                "상품명": product_name,
                "상품유형": category_name,
                "상품상세URL": self.driver.current_url,
                "크롤링일시": datetime.now().strftime("%Y-%m-%d")
            }
            
            # 가입금액 추출
            가입금액 = self.find_info_by_keywords(soup, ['가입금액', '가입한도', '예치금액', '납입금액', '최소금액', '최대금액'])
            product_info['가입금액'] = 가입금액 if 가입금액 else "정보 없음"
            
            # 가입대상 추출
            가입대상 = self.find_info_by_keywords(soup, ['가입대상', '가입자격', '가입조건', '고객구분', '대상고객'])
            product_info['가입대상'] = 가입대상 if 가입대상 else "정보 없음"
            
            # 가입방법 추출
            가입방법 = self.find_info_by_keywords(soup, ['가입방법', '가입경로', '신청방법', '접수방법', '가입채널'])
            product_info['가입방법'] = 가입방법 if 가입방법 else "정보 없음"
            
            # 계약기간 추출
            계약기간 = self.find_info_by_keywords(soup, ['계약기간', '예치기간', '상품기간', '계약만기', '예치만기'])
            product_info['계약기간'] = 계약기간 if 계약기간 else "정보 없음"
            
            # 기본/최대 금리 추출
            기본금리, 최고금리 = self.extract_rates_correctly(soup)
            product_info['기본금리'] = 기본금리
            product_info['최대금리'] = 최고금리
            
            # 세제혜택 추출
            세제혜택 = self.find_info_by_keywords(soup, ['세제혜택', '비과세', '세금우대', '소득공제', '세액공제'])
            product_info['세제혜택'] = 세제혜택 if 세제혜택 and '없음' not in 세제혜택 else None
            
            # 예금자보호 추출
            예금자보호 = self.find_info_by_keywords(soup, ['예금자보호', '예금보험', '보호한도', '예보'])
            product_info['예금자보호'] = 예금자보호 if 예금자보호 else "5천만원 한도 보호"
            
            # 우대조건 추출
            우대조건 = self.extract_preferential_rates_fixed(soup)
            product_info['우대조건'] = 우대조건
            
            # 금리계산방식 추출
            금리계산방식 = self.find_info_by_keywords(soup, ['복리', '단리', '금리계산', '이자계산'])
            if 금리계산방식:
                if '복리' in 금리계산방식:
                    product_info['금리계산방식'] = "복리"
                elif '단리' in 금리계산방식:
                    product_info['금리계산방식'] = "단리"
                else:
                    product_info['금리계산방식'] = "복리"  # 기본값
            else:
                product_info['금리계산방식'] = "복리"  # 기본값
            
            # 기간별 금리 추출 (새로 추가)
            기간별금리 = self.extract_period_rates_with_popup(soup)
            product_info['기간별금리'] = 기간별금리
            
            return product_info
            
        except Exception as e:
            print(f"    ❌ 정보 추출 실패: {e}")
            return None

    def extract_period_rates_with_popup(self, soup):
        """기간별 금리 추출 (팝업 처리)"""
        try:
            # 1. 금리보기 버튼 찾기
            rate_button = self.find_rate_button()
            
            if not rate_button:
                return None
            
            # 2. 금리보기 버튼 클릭
            try:
                self.driver.execute_script("arguments[0].click();", rate_button)
                time.sleep(3)
            except:
                return None
            
            # 3. 기간별 금리 추출
            period_rates = self.parse_period_rates_safe()
            
            # 4. 팝업 닫기
            self.close_rate_popup()
            
            return period_rates
            
        except Exception as e:
            return None

    def find_rate_button(self):
        """금리보기 버튼 찾기"""
        try:
            button_selectors = [
                "//button[contains(text(), '금리보기')]",
                "//a[contains(text(), '금리보기')]",
                "//span[contains(text(), '금리보기')]/parent::a",
                "//span[contains(text(), '금리보기')]/parent::button",
            ]
            
            for selector in button_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            return element
                except:
                    continue
            
            return None
            
        except Exception as e:
            return None

    def parse_period_rates_safe(self):
        """안전한 기간별 금리 파싱 (위치 기반 중복 제거)"""
        try:
            time.sleep(2)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            period_rates = []
            
            # 페이지 전체 텍스트
            page_text = soup.get_text()
            
            # 먼저 범위 패턴들을 찾아서 해당 부분을 제거한 후 단일 패턴 검색
            used_positions = set()  # 이미 사용된 텍스트 위치 추적
            
            # 1단계: 범위 패턴들 먼저 처리
            range_patterns = [
                ('1개월이상 6개월미만', r'1개월이상\s*6개월미만\s+(\d\.\d+)'),
                ('6개월이상 12개월미만', r'6개월이상\s*12개월미만\s+(\d\.\d+)'),
                ('12개월이상 24개월미만', r'12개월이상\s*24개월미만\s+(\d\.\d+)'),
                ('24개월이상 36개월미만', r'24개월이상\s*36개월미만\s+(\d\.\d+)'),
                ('36개월초과 60개월이하', r'36개월초과\s*60개월이하\s+(\d\.\d+)'),
                
                # 년 범위들
                ('1년이상 2년미만', r'1년이상\s*2년미만\s+(\d\.\d+)'),
                ('2년이상 3년미만', r'2년이상\s*3년미만\s+(\d\.\d+)'),
                ('3년이상 4년미만', r'3년이상\s*4년미만\s+(\d\.\d+)'),
                ('4년이상 5년미만', r'4년이상\s*5년미만\s+(\d\.\d+)'),
            ]
            
            # 범위 패턴 처리 및 사용된 위치 기록
            for period_name, pattern in range_patterns:
                try:
                    for match in re.finditer(pattern, page_text, re.IGNORECASE):
                        rate = float(match.group(1))
                        if 1.0 <= rate <= 5.0:
                            # 중복 체크
                            if not any(pr['기간'] == period_name for pr in period_rates):
                                period_rates.append({
                                    '기간': period_name,
                                    '금리': rate
                                })
                                
                                # 사용된 위치 기록
                                used_positions.update(range(match.start(), match.end()))
                except Exception as regex_error:
                    continue
            
            # 2단계: 단일 패턴들 처리 (사용된 위치 제외)
            single_patterns = [
                ('12개월', r'12개월\s+(\d\.\d+)'),
                ('24개월', r'24개월\s+(\d\.\d+)'),
                ('36개월', r'36개월\s+(\d\.\d+)'),
                ('6개월', r'6개월\s+(\d\.\d+)'),
                ('18개월', r'18개월\s+(\d\.\d+)'),
                ('60개월', r'60개월\s+(\d\.\d+)'),
                
                # 년 단위
                ('1년', r'1년\s+(\d\.\d+)'),
                ('2년', r'2년\s+(\d\.\d+)'),
                ('3년', r'3년\s+(\d\.\d+)'),
                ('4년', r'4년\s+(\d\.\d+)'),
                ('5년', r'5년\s+(\d\.\d+)'),
                
                # 기타
                ('36개월이하', r'36개월이하\s+(\d\.\d+)'),
                ('12개월이상', r'12개월이상\s+(\d\.\d+)'),
            ]
            
            # 단일 패턴 처리 (사용된 위치와 겹치지 않는 것만)
            for period_name, pattern in single_patterns:
                try:
                    for match in re.finditer(pattern, page_text, re.IGNORECASE):
                        # 이미 사용된 위치와 겹치는지 확인
                        match_positions = set(range(match.start(), match.end()))
                        if not match_positions.intersection(used_positions):
                            rate = float(match.group(1))
                            if 1.0 <= rate <= 5.0:
                                # 중복 체크
                                if not any(pr['기간'] == period_name for pr in period_rates):
                                    period_rates.append({
                                        '기간': period_name,
                                        '금리': rate
                                    })
                                    
                                    # 사용된 위치 기록
                                    used_positions.update(match_positions)
                except Exception as regex_error:
                    continue
            
            # 3단계: 테이블에서 직접 추출 (백업)
            if not period_rates:
                period_rates = self.extract_period_rates_from_tables(soup)
            
            return period_rates if period_rates else None
            
        except Exception as e:
            return None

    def extract_period_rates_from_tables(self, soup):
        """테이블에서 기간별 금리 직접 추출"""
        try:
            period_rates = []
            tables = soup.find_all('table')
            
            for table in tables:
                table_text = table.get_text()
                
                # 금리 관련 테이블인지 확인
                if any(keyword in table_text for keyword in ['예금이율표', '금리구분', '약정이율']):
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all(['th', 'td'])
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        
                        # 각 행에서 기간과 금리 찾기
                        if len(cell_texts) >= 2:
                            for i, cell in enumerate(cell_texts):
                                # 기간인지 확인
                                if ('개월' in cell or '년' in cell) and ('이상' in cell or '미만' in cell or '이하' in cell or '초과' in cell or cell.endswith('개월') or cell.endswith('년')):
                                    # 같은 행에서 금리 찾기
                                    for j, other_cell in enumerate(cell_texts):
                                        if i != j:
                                            try:
                                                if '.' in other_cell and len(other_cell) <= 5:
                                                    rate_val = float(other_cell)
                                                    if 1.0 <= rate_val <= 5.0:
                                                        if not any(pr['기간'] == cell for pr in period_rates):
                                                            period_rates.append({
                                                                '기간': cell,
                                                                '금리': rate_val
                                                            })
                                            except:
                                                continue
                    
                    if period_rates:
                        break
            
            return period_rates
            
        except Exception as e:
            return []

    def close_rate_popup(self):
        """금리 팝업 닫기"""
        try:
            # 확인 버튼 찾기
            close_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '확인')]")
            if close_buttons:
                close_buttons[0].click()
                time.sleep(1)
                return
            
            # ESC 키
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
        except:
            pass

    def find_info_by_keywords(self, soup, keywords):
        """키워드로 정보 찾기"""
        for keyword in keywords:
            # 방법 1: 테이블 구조 (th-td)
            th_elements = soup.find_all('th')
            for th in th_elements:
                if keyword in th.get_text():
                    tr = th.find_parent('tr')
                    if tr:
                        td = tr.find('td')
                        if td:
                            text = self.clean_text(td.get_text())
                            if text and len(text) > 3:
                                return text
            
            # 방법 2: dt-dd 구조
            dt_elements = soup.find_all('dt')
            for dt in dt_elements:
                if keyword in dt.get_text():
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        text = self.clean_text(dd.get_text())
                        if text and len(text) > 3:
                            return text
            
            # 방법 3: 텍스트 패턴
            page_text = soup.get_text()
            pattern = rf'{re.escape(keyword)}\s*[:：]\s*([^\n]{{10,150}})'
            match = re.search(pattern, page_text)
            if match:
                text = self.clean_text(match.group(1))
                if text:
                    return text
        
        return None

    def extract_rates_correctly(self, soup):
        """금리를 올바르게 추출"""
        try:
            page_text = soup.get_text()
            
            # "기본 2.85%" 패턴 찾기
            basic_pattern = r'기본\s*([0-9]\.[0-9]+)%'
            basic_match = re.search(basic_pattern, page_text)
            basic_rate = float(basic_match.group(1)) if basic_match else None
            
            # "최고 4.35" 패턴 찾기  
            max_patterns = [
                r'최고\s*([0-9]\.[0-9]+)',
                r'최대\s*([0-9]\.[0-9]+)%',
                r'최고금리\s*([0-9]\.[0-9]+)%'
            ]
            
            max_rate = None
            for pattern in max_patterns:
                match = re.search(pattern, page_text)
                if match:
                    max_rate = float(match.group(1))
                    break
            
            return basic_rate, max_rate
            
        except Exception as e:
            return None, None

    def extract_preferential_rates_fixed(self, soup):
        """우대조건을 정확하게 추출"""
        try:
            conditions = []
            
            # 전체 페이지 텍스트 확인
            page_text = soup.get_text()
            has_preferential = any(keyword in page_text for keyword in ['우대금리', '우대조건', '%p'])
            
            if not has_preferential:
                return None
            
            # 1. 전체 HTML에서 우대금리 관련 섹션들 모두 찾기
            preferential_sections = self.find_all_preferential_sections(soup)
            
            for i, section in enumerate(preferential_sections, 1):
                # 각 섹션에서 우대조건 추출
                section_conditions = self.extract_conditions_from_section(section)
                if section_conditions:
                    for condition in section_conditions:
                        # 중복 방지
                        condition_key = (condition['조건'], condition['추가금리'])
                        if not any((c['조건'], c['추가금리']) == condition_key for c in conditions):
                            conditions.append(condition)
            
            # 2. 전체 텍스트에서 직접 패턴 매칭 (보조 방법)
            if not conditions:
                text_conditions = self.extract_from_full_text(page_text)
                if text_conditions:
                    conditions.extend(text_conditions)
            
            return conditions if conditions else None
            
        except Exception as e:
            return None

    def find_all_preferential_sections(self, soup):
        """우대금리 관련 섹션들 모두 찾기"""
        try:
            sections = []
            
            # 1. 테이블에서 찾기
            tables = soup.find_all('table')
            for table in tables:
                table_text = table.get_text()
                if any(keyword in table_text for keyword in ['우대금리', '우대조건', '추가금리']):
                    if re.search(r'[0-9]\.[0-9]+%?p?', table_text):
                        sections.append(table)
            
            # 2. div, section 등에서 찾기
            for tag in ['div', 'section', 'td', 'th', 'p']:
                elements = soup.find_all(tag)
                for element in elements:
                    element_text = element.get_text()
                    if len(element_text) > 20:
                        if any(keyword in element_text for keyword in ['우대금리', '우대조건']):
                            if re.search(r'[0-9]\.[0-9]+%?p?', element_text):
                                # 이미 포함된 상위 요소가 있는지 확인
                                is_duplicate = False
                                for existing_section in sections:
                                    if existing_section in element.parents or element in existing_section.parents:
                                        is_duplicate = True
                                        break
                                
                                if not is_duplicate:
                                    sections.append(element)
            
            return sections
            
        except:
            return []

    def extract_conditions_from_section(self, section):
        """특정 섹션에서 우대조건 추출"""
        try:
            conditions = []
            section_text = section.get_text()
            
            # 1. 번호가 매겨진 조건들 찾기
            numbered_conditions = self.extract_numbered_conditions(section_text)
            if numbered_conditions:
                conditions.extend(numbered_conditions)
            
            # 2. 테이블 구조에서 찾기
            if section.name == 'table':
                table_conditions = self.extract_from_table_rows(section)
                if table_conditions:
                    # 중복 제거
                    existing_keys = {(c['조건'], c['추가금리']) for c in conditions}
                    for condition in table_conditions:
                        condition_key = (condition['조건'], condition['추가금리'])
                        if condition_key not in existing_keys:
                            conditions.append(condition)
            
            # 3. 일반 텍스트 패턴 매칭
            if not conditions:
                text_conditions = self.extract_from_text_patterns(section_text)
                if text_conditions:
                    conditions.extend(text_conditions)
            
            return conditions
            
        except:
            return []

    def extract_numbered_conditions(self, text):
        """번호가 매겨진 우대조건 추출"""
        try:
            conditions = []
            
            # 다양한 번호 형태의 패턴들
            number_patterns = [
                r'[①②③④⑤⑥⑦⑧⑨⑩]',
                r'\([1-9]\)',
                r'[1-9]\.',
                r'[1-9]\)',
            ]
            
            # 각 번호 패턴별로 우대조건 찾기
            for pattern in number_patterns:
                numbered_sections = re.split(f'({pattern})', text)
                
                if len(numbered_sections) > 2:
                    for i in range(1, len(numbered_sections), 2):
                        if i + 1 < len(numbered_sections):
                            number = numbered_sections[i].strip()
                            content = numbered_sections[i + 1].strip()
                            
                            # 해당 섹션에서 우대조건과 금리 추출
                            condition_info = self.parse_numbered_condition(number, content)
                            if condition_info:
                                conditions.append(condition_info)
                    
                    break
            
            return conditions
            
        except Exception as e:
            return []

    def parse_numbered_condition(self, number, content):
        """번호가 매겨진 각 조건 파싱"""
        try:
            # 금리 패턴 찾기
            rate_patterns = [
                r'최고\s*연\s*([0-9]\.[0-9]+)%p',
                r'연\s*([0-9]\.[0-9]+)%p',
                r'([0-9]\.[0-9]+)%p',
            ]
            
            rate_value = None
            for pattern in rate_patterns:
                match = re.search(pattern, content)
                if match:
                    rate_value = float(match.group(1))
                    break
            
            if not rate_value:
                return None
            
            # 조건명 추출
            condition_name = self.extract_condition_name_from_content(content)
            
            if condition_name:
                return {
                    "조건": condition_name,
                    "추가금리": rate_value
                }
            
            return None
            
        except:
            return None

    def extract_condition_name_from_content(self, content):
        """조건 내용에서 조건명 추출"""
        try:
            # 조건명 패턴들
            condition_patterns = [
                (r'가입시점.*?복무기간.*?우대금리', '복무기간별 우대금리'),
                (r'군\s*급여이체.*?우대금리', '군 급여이체'),
                (r'신용.*?체크카드.*?이용.*?우대금리', '신용체크카드 이용'),
                (r'급여이체.*?우대금리', '급여이체'),
                (r'자동이체.*?우대금리', '자동이체'),
                (r'카드.*?이용.*?우대금리', '카드이용'),
                (r'복무달성.*?축하금리', '복무달성 축하금리'),
                (r'최초.*?거래.*?우대금리', '최초거래'),
                (r'급여이체', '급여이체'),
                (r'자동이체', '자동이체'),
                (r'카드.*?이용', '카드이용'),
                (r'복무기간', '복무기간별'),
                (r'군.*?급여', '군 급여이체'),
                (r'체크카드', '체크카드 이용'),
                (r'복무달성', '복무달성 축하금리'),
                (r'최초.*?거래', '최초거래고객 우대금리'),
            ]
            
            for pattern, condition_name in condition_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return condition_name
            
            # 패턴에 매칭되지 않으면 첫 번째 의미있는 단어들 추출
            words = content.split()
            meaningful_words = []
            for word in words[:5]:
                cleaned_word = re.sub(r'[^\w가-힣]', '', word)
                if len(cleaned_word) > 1 and '우대' not in cleaned_word and '금리' not in cleaned_word:
                    meaningful_words.append(cleaned_word)
                    if len(meaningful_words) >= 2:
                        break
            
            if meaningful_words:
                return ' '.join(meaningful_words)[:15]
            
            return None
            
        except:
            return None

    def extract_from_table_rows(self, table):
        """테이블 행에서 우대조건 추출"""
        try:
            conditions = []
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 2:
                    for i in range(len(cells) - 1):
                        condition_text = self.clean_text(cells[i].get_text())
                        rate_text = self.clean_text(cells[i + 1].get_text())
                        
                        if condition_text and rate_text:
                            rate_match = re.search(r'([0-9]\.[0-9]+)%?p?', rate_text)
                            
                            if rate_match and self.is_meaningful_condition(condition_text):
                                clean_condition = self.clean_condition_name(condition_text)
                                
                                if clean_condition:
                                    rate_value = float(rate_match.group(1))
                                    conditions.append({
                                        "조건": clean_condition,
                                        "추가금리": rate_value
                                    })
            
            return conditions
            
        except:
            return []

    def extract_from_text_patterns(self, text):
        """텍스트에서 직접 패턴 매칭"""
        try:
            conditions = []
            
            patterns = [
                (r'복무달성.*?축하금리[^0-9]*?연\s*([0-9]\.[0-9]+)%p', "복무달성 축하금리"),
                (r'최초.*?거래.*?고객.*?우대금리[^0-9]*?연\s*([0-9]\.[0-9]+)%p', "최초거래고객 우대금리"),
                (r'급여이체.*?우대금리[^0-9]*?연\s*([0-9]\.[0-9]+)%p', "급여이체"),
                (r'자동이체.*?우대금리[^0-9]*?연\s*([0-9]\.[0-9]+)%p', "자동이체"),
                (r'카드.*?이용.*?우대금리[^0-9]*?연\s*([0-9]\.[0-9]+)%p', "카드이용"),
                (r'군\s*급여이체.*?우대금리[^0-9]*?연\s*([0-9]\.[0-9]+)%p', "군 급여이체"),
                (r'복무기간.*?우대금리[^0-9]*?최고.*?연\s*([0-9]\.[0-9]+)%p', "복무기간별 우대금리"),
                (r'신용.*?체크카드.*?우대금리[^0-9]*?연\s*([0-9]\.[0-9]+)%p', "신용체크카드 이용"),
            ]
            
            for pattern, default_name in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    rate_value = float(match.group(1))
                    
                    match_start = max(0, match.start() - 50)
                    context = text[match_start:match.end()]
                    condition_name = self.extract_condition_from_context(context) or default_name
                    
                    conditions.append({
                        "조건": condition_name,
                        "추가금리": rate_value
                    })
            
            return conditions
            
        except:
            return []

    def extract_from_full_text(self, text):
        """전체 텍스트에서 우대조건 추출"""
        try:
            conditions = []
            
            sentences = re.split(r'[.!?]', text)
            
            for sentence in sentences:
                if '%p' in sentence and any(keyword in sentence for keyword in ['우대', '축하', '추가']):
                    rate_matches = re.findall(r'([0-9]\.[0-9]+)%p', sentence)
                    
                    for rate_str in rate_matches:
                        rate_value = float(rate_str)
                        
                        condition_name = self.extract_condition_from_sentence(sentence)
                        if condition_name:
                            conditions.append({
                                "조건": condition_name,
                                "추가금리": rate_value
                            })
            
            return conditions
            
        except:
            return []

    def extract_condition_from_context(self, context):
        """문맥에서 조건명 추출"""
        condition_keywords = {
            '복무달성': '복무달성 축하금리',
            '최초': '최초거래고객 우대금리', 
            '급여이체': '급여이체',
            '자동이체': '자동이체',
            '카드': '카드이용',
            '복무기간': '복무기간별 우대금리'
        }
        
        for keyword, condition_name in condition_keywords.items():
            if keyword in context:
                return condition_name
        
        return None

    def extract_condition_from_sentence(self, sentence):
        """문장에서 조건명 추출"""
        if '복무달성' in sentence:
            return '복무달성 축하금리'
        elif '최초' in sentence and '거래' in sentence:
            return '최초거래고객 우대금리'
        elif '급여이체' in sentence:
            return '급여이체'
        elif '자동이체' in sentence:
            return '자동이체'
        elif '카드' in sentence:
            return '카드이용'
        elif '복무기간' in sentence:
            return '복무기간별 우대금리'
        else:
            return '우대금리'

    def is_meaningful_condition(self, text):
        """의미있는 조건인지 확인"""
        if not text or len(text.strip()) < 2:
            return False
        
        meaningless = ['구분', '금리', '%', '연', '우대조건', '최고', '합계', '총']
        if text.strip() in meaningless:
            return False
        
        meaningful_keywords = [
            '복무', '달성', '축하', '최초', '거래', '급여', '이체', '자동', 
            '카드', '이용', '신용', '체크', '군', '펀드', '보험', '인터넷', '모바일'
        ]
        
        return any(keyword in text for keyword in meaningful_keywords)

    def clean_condition_name(self, condition_text):
        """조건명 정리"""
        try:
            cleaned = condition_text.strip()
            
            patterns_to_clean = [
                (r'^\s*-\s*', ''),
                (r'\s*\([^)]*\)\s*', ''),
                (r'\s*\*.*', ''),
                (r'\s+', ' '),
            ]
            
            for pattern, replacement in patterns_to_clean:
                cleaned = re.sub(pattern, replacement, cleaned)
            
            cleaned = cleaned.strip()
            
            if len(cleaned) > 20:
                if '급여이체' in cleaned:
                    return '급여이체'
                elif '자동이체' in cleaned:
                    return '자동이체'
                elif '카드' in cleaned:
                    return '카드이용'
                elif '최초' in cleaned:
                    return '최초거래'
                elif '재예치' in cleaned:
                    return '재예치'
                else:
                    return cleaned[:15] + '...'
            
            return cleaned if len(cleaned) > 2 else None
            
        except:
            return condition_text.strip() if condition_text else None

    def return_to_original_page(self, original_url):
        """원래 페이지로 안전하게 복귀"""
        try:
            current_url = self.driver.current_url
            
            if current_url != original_url:
                self.driver.back()
                time.sleep(2)
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.stit"))
            )
            
        except Exception as e:
            self.driver.get(original_url)
            time.sleep(3)

    def clean_text(self, text):
        """텍스트 정리"""
        if not text:
            return None
        
        text = re.sub(r'\s+', ' ', text.strip())
        
        if len(text) < 1:
            return None
        
        return text

    def save_results(self, results, filename=None):
        """결과 저장"""
        dotenv.load_dotenv()
        directory_path = os.getenv("JSON_RESULT_PATH")
        os.makedirs(directory_path, exist_ok=True)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"IBK.json"

        file_path = os.path.join(directory_path, filename)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 저장 완료: {filename}")
            
            products = results.get('products', [])
            crawl_info = results.get('crawl_info', {})
            
            print(f"\n📊 === 최종 크롤링 통계 ===")
            print(f"크롤링 일시: {crawl_info.get('crawl_date', 'N/A')}")
            print(f"총 수집 상품: {len(products)}개")
            print(f"  • 적금 상품: {crawl_info.get('savings_count', 0)}개")
            print(f"  • 예금 상품: {crawl_info.get('deposits_count', 0)}개")
            print(f"목표 대비: {len(products)}/{crawl_info.get('total_expected', 45)}개")
            
            products_with_conditions = [p for p in products if p.get('우대조건')]
            products_with_period_rates = [p for p in products if p.get('기간별금리')]
            
            print(f"우대조건 보유 상품: {len(products_with_conditions)}개")
            print(f"기간별금리 보유 상품: {len(products_with_period_rates)}개")
            
            if products:
                print(f"\n📋 === 첫 3개 상품 샘플 ===")
                for i, product in enumerate(products[:3], 1):
                    print(f"{i}. {product['상품명']} ({product['상품유형']})")
                    print(f"   기본금리: {product.get('기본금리', 'N/A')}%, 최대금리: {product.get('최대금리', 'N/A')}%")
                    print(f"   계약기간: {product.get('계약기간', 'N/A')}")
                    
                    if product.get('기간별금리'):
                        print(f"   기간별금리: {len(product['기간별금리'])}개")
                        for rate in product['기간별금리'][:2]:
                            print(f"     - {rate['기간']}: {rate['금리']}%")
                    else:
                        print(f"   기간별금리: 없음")
                        
                    if product.get('우대조건'):
                        print(f"   우대조건: {len(product['우대조건'])}개")
                        for condition in product['우대조건'][:2]:
                            print(f"     - {condition['조건']}: +{condition['추가금리']}%p")
                    else:
                        print(f"   우대조건: 없음")
            
            return True
            
        except Exception as e:
            print(f"❌ 저장 실패: {e}")
            return False

    def start(self):
        print("🚀 ibk 적금/예금 전체 크롤러 (기간별 금리 포함)")
        print("📋 목돈모으기(적금) 28개 + 목돈굴리기(예금) 17개 = 총 45개 상품")
        print("🎯 기간별 금리, 우대조건 등 모든 정보 포함 크롤링\n")

        try:
            results = self.crawl_all_products()

            if results and len(results.get('products', [])) > 0:
                success = self.save_results(results)

                if success:
                    print(f"\n🎉 전체 크롤링 및 저장 완료!")
                    print(f"📄 JSON 파일에 {len(results['products'])}개 상품 정보가 저장되었습니다.")
                    print(f"📊 기간별 금리 정보도 포함되어 있습니다.")
            else:
                print("❌ 크롤링 실패 - 수집된 상품이 없습니다")

        except KeyboardInterrupt:
            print("\n⏹️ 사용자가 중단했습니다")
        except Exception as e:
            print(f"\n💥 오류 발생: {e}")

