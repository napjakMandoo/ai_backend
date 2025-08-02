"""
IM은행 완전 크롤러 - 3단계 포함 최종 버전
JavaScript 콘솔 코드와 정확히 동일한 3단계 플로우 구현
im.py 수정 코드 파일.
"""

import time
import re
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd

class IMBankCompleteCrawler:
    def __init__(self):
        self.products = []
        self.current_category = ""
        self.errors = []
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Chrome 드라이버 설정"""
        print("🔧 Chrome 드라이버 설정 중...")
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_window_size(1920, 1080)
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10) 
            self.wait = WebDriverWait(self.driver, 30)
            
            print("✅ Chrome 드라이버 설정 완료")
            
        except Exception as e:
            print(f"❌ Chrome 드라이버 설정 실패: {e}")
            raise
    
    def clean_text(self, text):
        """텍스트 정리"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())
    
    def extract_number(self, text):
        """숫자 추출"""
        if not text:
            return None
        numbers = re.findall(r'\d+\.?\d*', text.replace(',', ''))
        return float(numbers[0]) if numbers else None
    
    def extract_rate_number(self, text):
        """금리 전용 숫자 추출"""
        if not text:
            return None
            
        clean_text = text.strip()
        if not clean_text or clean_text in ['-', '', 'N/A']:
            return None
            
        # %가 포함된 경우 우선 처리
        if '%' in text:
            percent_match = re.search(r'(\d+\.?\d*)\s*%', text)
            if percent_match:
                rate = float(percent_match.group(1))
                return rate if 0 < rate <= 50 else None
        
        # 소수점이 포함된 숫자
        decimal_match = re.search(r'\d+\.\d+', text)
        if decimal_match:
            rate = float(decimal_match.group(0))
            return rate if 0 < rate <= 50 else None
        
        # 일반 정수이지만 금리 범위에 있는 경우
        number_match = re.match(r'^\s*(\d+)\s*$', text)
        if number_match:
            rate = float(number_match.group(1))
            if 1 <= rate <= 10 and rate not in [6, 12, 24, 36, 60]:
                return rate
        
        return None
    
    def go_to_main_page_and_find_iframe(self):
        """메인 페이지로 이동하고 iframe 찾기"""
        print("🔄 메인 페이지로 이동하고 iframe 찾는 중...")
        
        main_url = "https://www.imbank.co.kr/com_ebz_fpm_main.act"
        print(f"📍 메인 페이지 이동: {main_url}")
        
        self.driver.get(main_url)
        
        # 페이지 로딩 대기
        WebDriverWait(self.driver, 30).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        time.sleep(5)
        
        # iframe 찾기
        print("🔍 iframe (#ifr) 찾는 중...")
        
        try:
            iframe = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "ifr"))
            )
            print("✅ iframe 발견!")
            
            iframe_src = iframe.get_attribute('src')
            print(f"📍 초기 iframe src: '{iframe_src}'")
            
            # iframe이 비어있는 것이 정상 상태
            if not iframe_src or iframe_src.strip() == '':
                print("✅ iframe이 비어있음 - 이것이 정상 상태입니다")
                return True
                
        except Exception as e:
            print(f"❌ iframe 찾기 실패: {e}")
            return False
    
    def navigate_to_category_in_iframe(self, category, url_code):
        """iframe에 카테고리 URL 설정"""
        print(f"🔄 iframe에 {category} URL 설정 중...")
        
        category_url = f"https://www.imbank.co.kr/fnp_ebz_{url_code}_depo.act"
        print(f"📍 설정할 URL: {category_url}")
        
        try:
            # 메인 프레임으로 확실히 돌아가기
            self.driver.switch_to.default_content()
            
            # iframe 존재 확인
            iframe_exists = self.driver.execute_script("return document.getElementById('ifr') !== null;")
            if not iframe_exists:
                print("⚠️ iframe이 존재하지 않음 - 페이지 새로고침 시도")
                main_url = "https://www.imbank.co.kr/com_ebz_fpm_main.act"
                self.driver.get(main_url)
                WebDriverWait(self.driver, 30).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                time.sleep(3)
            
            # iframe src 속성 설정
            self.driver.execute_script(f"document.getElementById('ifr').src = '{category_url}';")
            print(f"✅ iframe URL 설정 완료")
            
            # iframe 로딩 대기
            time.sleep(8)
            
            # iframe으로 전환
            iframe = self.driver.find_element(By.ID, "ifr")
            self.driver.switch_to.frame(iframe)
            print("✅ iframe 내부로 전환 완료")
            
            # 카테고리 페이지 로딩 확인
            return self.wait_for_iframe_complete()
            
        except Exception as e:
            print(f"❌ iframe URL 설정 실패: {e}")
            return False
    
    def wait_for_iframe_complete(self):
        """iframe 완전 로딩 대기"""
        print("🔄 iframe 완전 로딩 대기 중...")
        
        for attempt in range(1, 21):
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body_text = body.text
                body_html = body.get_attribute('innerHTML')
                
                text_sufficient = len(body_text) > 500
                html_sufficient = len(body_html) > 2000
                has_content = '적금' in body_text or '예금' in body_text or 'im' in body_text
                
                print(f"⏳ 시도 {attempt}/20: 텍스트 {len(body_text)}자, HTML {len(body_html)}자, 상품키워드: {has_content}")
                
                if text_sufficient or html_sufficient or (len(body_text) > 200 and has_content):
                    print(f"✅ iframe 완전 로딩 완료 ({attempt}회 시도)")
                    time.sleep(2)
                    return True
                    
            except Exception as e:
                print(f"⏳ iframe 로딩 대기 중... ({attempt}/20) - 오류: {e}")
            
            time.sleep(3)
        
        print("❌ iframe 로딩 시간 초과")
        return False
    
    def show_all_products_in_one_page(self):
        """한 페이지에 모든 상품 표시"""
        try:
            print("📋 한 페이지에 모든 상품 표시 시도...")
            
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            total_match = re.search(r'총\s*(\d+)\s*건', body_text)
            expected_total = int(total_match.group(1)) if total_match else 50
            
            print(f"📊 예상 총 상품 수: {expected_total}개")
            
            show_count = max(expected_total, 50)
            print(f"🔧 reDrawTable({show_count}) 호출...")
            
            try:
                self.driver.execute_script(f"reDrawTable({show_count});")
                print(f"✅ reDrawTable({show_count}) 호출 완료")
                time.sleep(5)
                
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                if len(tables) >= 2:
                    product_table = tables[1]
                    product_links = product_table.find_elements(By.CSS_SELECTOR, 'a[href*="goDetailPageCom"]')
                    print(f"🔍 발견된 상품 링크: {len(product_links)}개")
                    
                    if len(product_links) > 5:
                        print(f"✅ 성공: {len(product_links)}개 상품이 한 페이지에 표시됨")
                        return True
                        
            except Exception as e:
                print(f"⚠️ reDrawTable 함수 호출 실패: {e}")
            
            return False
            
        except Exception as e:
            print(f"❌ 전체 상품 표시 실패: {e}")
            return False
    
    def extract_all_products_from_page(self):
        """현재 페이지의 모든 상품 정보 추출"""
        products = []
        
        try:
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            print(f"📋 테이블 {len(tables)}개 발견")
            
            if len(tables) >= 2:
                product_table = tables[1]
                rows = product_table.find_elements(By.TAG_NAME, "tr")
                
                print(f"📋 상품 테이블에서 {len(rows)}개 행 검사")
                
                for index, row in enumerate(rows):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) >= 3:
                        product_cell = cells[1]
                        product_links = []
                        
                        # 다양한 패턴으로 상품 링크 찾기
                        links_pattern1 = product_cell.find_elements(By.CSS_SELECTOR, 'a[href*="goDetailPageCom"]')
                        if links_pattern1:
                            product_links.extend(links_pattern1)
                        
                        links_pattern2 = product_cell.find_elements(By.CSS_SELECTOR, 'a[onclick*="goDetailPageCom"]')
                        if links_pattern2:
                            product_links.extend(links_pattern2)
                        
                        if product_links:
                            product_link = product_links[0]
                            product_name = self.clean_text(product_link.text)
                            
                            href = product_link.get_attribute('href') or ''
                            onclick = product_link.get_attribute('onclick') or ''
                            
                            combined_attr = href + ' ' + onclick
                            match = re.search(r"goDetailPageCom\('([^']+)','([^']+)','([^']+)'\)", combined_attr)
                            
                            if match:
                                code, encoded_name, page_type = match.groups()
                                rate_text = cells[2].text
                                rates = self.parse_rate_text(rate_text)
                                
                                products.append({
                                    'name': product_name,
                                    'code': code,
                                    'encoded_name': encoded_name,
                                    'page_type': page_type,
                                    'basic_rate': rates['basic'],
                                    'max_rate': rates['max'],
                                    'rate_text': rate_text
                                })
                                
                                print(f"🔍 상품 발견: {product_name}")
        
        except Exception as e:
            print(f"❌ 상품 추출 중 오류: {e}")
        
        print(f"📊 총 {len(products)}개 상품 추출 완료")
        return products
    
    def parse_rate_text(self, text):
        """금리 텍스트 파싱"""
        rates = {'basic': None, 'max': None}
        
        max_match = re.search(r'최고[^0-9]*?(\d+\.?\d*)%', text)
        basic_match = re.search(r'기본[^0-9]*?(\d+\.?\d*)%', text)
        
        if max_match:
            rates['max'] = float(max_match.group(1))
        if basic_match:
            rates['basic'] = float(basic_match.group(1))
        
        return rates
    
    def extract_detailed_product_info(self, product_info):
        """상세 페이지 정보 추출"""
        try:
            print(f"🔍 {product_info['name']} 상세 정보 수집...")
            
            try:
                self.driver.execute_script("setPageSession();")
                time.sleep(1)
            except:
                pass
            
            self.driver.execute_script(
                f"goDetailPageCom('{product_info['code']}', '{product_info['encoded_name']}', '{product_info['page_type']}');"
            )
            time.sleep(6)
            
            detailed_product = self.parse_detail_page_improved(product_info)
            
            try:
                self.driver.execute_script("history.back();")
                time.sleep(4)
            except:
                pass
            
            print(f"✅ {product_info['name']} 완료")
            return detailed_product
            
        except Exception as e:
            print(f"❌ {product_info['name']} 실패: {e}")
            return self.create_basic_product(product_info)
    
    def parse_detail_page_improved(self, product_info):
        """상세 페이지 파싱"""
        product = self.create_basic_product(product_info)
        
        print(f"📝 {product_info['name']} 상세 정보 파싱 중...")
        
        try:
            detail_info = self.extract_structured_info()
            
            if detail_info.get('join_target'):
                product["가입대상"] = detail_info['join_target']
            if detail_info.get('join_period'):
                product["계약기간"] = detail_info['join_period']
            if detail_info.get('join_amount'):
                product["가입금액"] = detail_info['join_amount']
            if detail_info.get('join_method'):
                product["가입방법"] = detail_info['join_method']
            if detail_info.get('tax_benefit'):
                product["세제혜택"] = detail_info['tax_benefit']
            if detail_info.get('deposit_protection'):
                product["예금자보호"] = detail_info['deposit_protection']
            
            product["우대조건"] = self.extract_preferential_conditions()
            product["기간별금리"] = self.extract_period_rates()
            
        except Exception as e:
            print(f"상세 정보 파싱 중 오류: {e}")
        
        return product
    
    def extract_structured_info(self):
        """구조화된 정보 추출 - 강화된 다중 전략 접근법"""
        info = {
            'join_target': "",
            'join_period': "",
            'join_amount': "",
            'join_method': "",
            'tax_benefit': None,
            'deposit_protection': ""
        }
        
        try:
            print("🔍 상세 정보 추출 시작 (강화된 다중 전략 접근법)...")
            
            # 전략 1: JavaScript와 동일한 기본 방법
            elements = self.driver.find_elements(By.CSS_SELECTOR, 'li, div, span, td')
            
            for element in elements:
                text = self.clean_text(element.text)
                
                if '가입대상' in text and len(text) < 100:
                    match = re.search(r'가입대상[:\s]*(.+?)(?=가입기간|가입금액|가입방법|$)', text)
                    if match and not info['join_target']:
                        target = self.clean_text(match.group(1))
                        if len(target) > 2 and target not in [':', '-', ')', '(']:
                            info['join_target'] = target
                            print(f"✅ 기본방법 - 가입대상: {target}")

                if '가입기간' in text and len(text) < 100:
                    match = re.search(r'가입기간[:\s]*(.+?)(?=가입대상|가입금액|가입방법|$)', text)
                    if match and not info['join_period']:
                        period = self.clean_text(match.group(1))
                        if len(period) > 2 and period not in [':', '-', ')', '(']:
                            info['join_period'] = period
                            print(f"✅ 기본방법 - 계약기간: {period}")

                if '가입금액' in text and len(text) < 100:
                    match = re.search(r'가입금액[:\s]*(.+?)(?=가입대상|가입기간|가입방법|$)', text)
                    if match and not info['join_amount']:
                        amount = self.clean_text(match.group(1))
                        if len(amount) > 2 and amount not in [':', '-', ')', '(']:
                            info['join_amount'] = amount
                            print(f"✅ 기본방법 - 가입금액: {amount}")

                if '가입방법' in text and len(text) < 100:
                    match = re.search(r'가입방법[:\s]*(.+?)(?=가입대상|가입기간|가입금액|과세우대|$)', text)
                    if match and not info['join_method']:
                        method = self.clean_text(match.group(1))
                        if len(method) > 2:
                            info['join_method'] = method
                            print(f"✅ 기본방법 - 가입방법: {method}")

                if '과세우대' in text and len(text) < 100:
                    match = re.search(r'과세우대[:\s]*(.+?)(?=가입대상|가입기간|예금자보호|$)', text)
                    if match and not info['tax_benefit']:
                        tax_text = self.clean_text(match.group(1))
                        if tax_text and '해당없음' not in tax_text and '없음' not in tax_text:
                            info['tax_benefit'] = tax_text
                            print(f"✅ 기본방법 - 세제혜택: {tax_text}")

                if '예금자보호' in text and len(text) < 100:
                    match = re.search(r'예금자보호[:\s]*(.+?)(?=가입대상|가입기간|$)', text)
                    if match and not info['deposit_protection']:
                        protection = self.clean_text(match.group(1))
                        if len(protection) > 2:
                            info['deposit_protection'] = protection
                            print(f"✅ 기본방법 - 예금자보호: {protection}")

            # 전략 2: 테이블 방법
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                    if len(cells) >= 2:
                        label = self.clean_text(cells[0].text)
                        value = self.clean_text(cells[1].text)
                        
                        if '가입대상' in label and not info['join_target'] and len(value) > 2:
                            info['join_target'] = value
                            print(f"✅ 테이블방법 - 가입대상: {value}")
                        if '가입기간' in label and not info['join_period'] and len(value) > 2:
                            info['join_period'] = value
                            print(f"✅ 테이블방법 - 계약기간: {value}")
                        if '가입금액' in label and not info['join_amount'] and len(value) > 2:
                            info['join_amount'] = value
                            print(f"✅ 테이블방법 - 가입금액: {value}")
                        if '가입방법' in label and not info['join_method'] and len(value) > 2:
                            info['join_method'] = value
                            print(f"✅ 테이블방법 - 가입방법: {value}")
                        if '과세우대' in label and not info['tax_benefit']:
                            if value and '해당없음' not in value and '없음' not in value:
                                info['tax_benefit'] = value
                                print(f"✅ 테이블방법 - 세제혜택: {value}")
                        if '예금자보호' in label and not info['deposit_protection'] and len(value) > 2:
                            info['deposit_protection'] = value
                            print(f"✅ 테이블방법 - 예금자보호: {value}")

            # 전략 3: 전체 페이지 텍스트에서 강력한 패턴 매칭
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                print(f"🔍 전체 페이지 텍스트 분석 ({len(body_text)}자)")
                
                # 더 유연한 정규식 패턴들
                patterns = {
                    'join_target': [
                        r'가입\s*대상[:\s]*([^\n\r가입기간가입금액가입방법]{3,80})',
                        r'가입\s*자격[:\s]*([^\n\r가입기간가입금액가입방법]{3,80})',
                        r'대상[:\s]*([^\n\r가입기간가입금액가입방법]{3,80})',
                    ],
                    'join_period': [
                        r'가입\s*기간[:\s]*([^\n\r가입대상가입금액가입방법]{3,80})',
                        r'계약\s*기간[:\s]*([^\n\r가입대상가입금액가입방법]{3,80})',
                        r'기간[:\s]*([^\n\r가입대상가입금액가입방법]{3,80})',
                    ],
                    'join_amount': [
                        r'가입\s*금액[:\s]*([^\n\r가입대상가입기간가입방법]{3,80})',
                        r'예치\s*금액[:\s]*([^\n\r가입대상가입기간가입방법]{3,80})',
                        r'최소\s*금액[:\s]*([^\n\r가입대상가입기간가입방법]{3,80})',
                    ],
                    'join_method': [
                        r'가입\s*방법[:\s]*([^\n\r가입대상가입기간가입금액]{3,80})',
                        r'가입\s*경로[:\s]*([^\n\r가입대상가입기간가입금액]{3,80})',
                    ],
                    'tax_benefit': [
                        r'과세\s*우대[:\s]*([^\n\r가입대상가입기간가입금액]{3,80})',
                        r'세제\s*혜택[:\s]*([^\n\r가입대상가입기간가입금액]{3,80})',
                    ],
                    'deposit_protection': [
                        r'예금자\s*보호[:\s]*([^\n\r가입대상가입기간가입금액]{3,80})',
                    ]
                }
                
                for field, pattern_list in patterns.items():
                    if info[field]:  # 이미 찾았으면 스킵
                        continue
                        
                    for pattern in pattern_list:
                        matches = re.findall(pattern, body_text, re.IGNORECASE)
                        for match in matches:
                            clean_match = self.clean_text(match)
                            
                            # 유효성 검증
                            if len(clean_match) > 2 and clean_match not in [':', '-', ')', '(', '※']:
                                # 세제혜택 특별 처리
                                if field == 'tax_benefit':
                                    if '해당없음' not in clean_match and '없음' not in clean_match:
                                        info[field] = clean_match
                                        print(f"✅ 정규식방법 - {field}: {clean_match}")
                                        break
                                else:
                                    info[field] = clean_match
                                    print(f"✅ 정규식방법 - {field}: {clean_match}")
                                    break
                        
                        if info[field]:  # 찾았으면 다음 필드로
                            break
                            
            except Exception as e:
                print(f"전체 페이지 텍스트 분석 중 오류: {e}")

            # 전략 4: 더 넓은 범위의 요소 검색
            print("🔍 확장된 요소 검색...")
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, '*')
            
            keywords = {
                'join_target': ['가입대상', '가입자격', '대상'],
                'join_period': ['가입기간', '계약기간', '기간'],
                'join_amount': ['가입금액', '예치금액', '최소금액'],
                'join_method': ['가입방법', '가입경로'],
                'tax_benefit': ['과세우대', '세제혜택'],
                'deposit_protection': ['예금자보호']
            }
            
            for element in all_elements:
                try:
                    element_text = self.clean_text(element.text)
                    if not element_text or len(element_text) > 200:
                        continue
                        
                    for field, keyword_list in keywords.items():
                        if info[field]:  # 이미 찾았으면 스킵
                            continue
                            
                        for keyword in keyword_list:
                            if keyword in element_text:
                                # 콜론이나 공백으로 분리해서 값 추출
                                parts = element_text.split(keyword)
                                if len(parts) > 1:
                                    potential_value = parts[1].strip()
                                    
                                    # 첫 번째 문장이나 줄만 추출
                                    if ':' in potential_value:
                                        potential_value = potential_value.split(':', 1)[1].strip()
                                    
                                    potential_value = potential_value.split('\n')[0].strip()
                                    potential_value = potential_value.split('.')[0].strip()
                                    
                                    if len(potential_value) > 2 and potential_value not in [':', '-', ')', '(']:
                                        if field == 'tax_benefit':
                                            if '해당없음' not in potential_value and '없음' not in potential_value:
                                                info[field] = potential_value
                                                print(f"✅ 확장검색 - {field}: {potential_value}")
                                                break
                                        else:
                                            info[field] = potential_value
                                            print(f"✅ 확장검색 - {field}: {potential_value}")
                                            break
                except:
                    continue

            # 전략 5: 특정 속성이나 클래스명으로 찾기
            print("🔍 속성/클래스 기반 검색...")
            special_selectors = [
                'div[class*="info"]',
                'div[class*="detail"]',
                'span[class*="content"]',
                'td[class*="value"]',
                'p[class*="text"]'
            ]
            
            for selector in special_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements[:20]:  # 최대 20개만 검사
                        text = self.clean_text(element.text)
                        if not text or len(text) > 100:
                            continue
                            
                        # 각 필드에 대해 키워드 매칭
                        for field, keyword_list in keywords.items():
                            if info[field]:  # 이미 찾았으면 스킵
                                continue
                                
                            for keyword in keyword_list:
                                if keyword in text:
                                    # 간단한 분리 로직
                                    if ':' in text:
                                        parts = text.split(':', 1)
                                        if len(parts) > 1:
                                            value = self.clean_text(parts[1])
                                            if len(value) > 2:
                                                if field == 'tax_benefit':
                                                    if '해당없음' not in value and '없음' not in value:
                                                        info[field] = value
                                                        print(f"✅ 속성검색 - {field}: {value}")
                                                        break
                                                else:
                                                    info[field] = value
                                                    print(f"✅ 속성검색 - {field}: {value}")
                                                    break
                except:
                    continue
                            
        except Exception as e:
            print(f"구조화된 정보 추출 중 오류: {e}")
        
        # 최종 결과 요약
        valid_info_count = sum(1 for value in info.values() if value)
        if valid_info_count > 0:
            print(f"📊 구조화된 정보 추출 완료 ({valid_info_count}개 항목):")
            korean_names = {
                'join_target': '가입대상',
                'join_period': '계약기간', 
                'join_amount': '가입금액',
                'join_method': '가입방법',
                'tax_benefit': '세제혜택',
                'deposit_protection': '예금자보호'
            }
            for key, value in info.items():
                if value:
                    print(f"  {korean_names.get(key, key)}: {value}")
        else:
            print("📊 구조화된 정보 추출 완료 (0개 항목)")
            
            # 상세한 디버깅 정보
            try:
                current_url = self.driver.current_url
                page_title = self.driver.title
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                
                print(f"🔍 디버깅 정보:")
                print(f"  현재 URL: {current_url}")
                print(f"  페이지 제목: {page_title}")
                print(f"  페이지 텍스트 길이: {len(body_text)}자")
                
                # 키워드 존재 여부 확인
                all_keywords = ['가입대상', '가입기간', '가입금액', '가입방법', '과세우대', '예금자보호',
                              '가입자격', '계약기간', '예치금액', '세제혜택']
                found_keywords = [kw for kw in all_keywords if kw in body_text]
                print(f"  발견된 키워드: {found_keywords}")
                
                # 페이지 샘플 텍스트
                print(f"  페이지 샘플 (처음 300자): {body_text[:300]}...")
                
                # HTML 구조 간단 분석
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                divs = self.driver.find_elements(By.TAG_NAME, "div")
                spans = self.driver.find_elements(By.TAG_NAME, "span")
                
                print(f"  HTML 구조: 테이블 {len(tables)}개, div {len(divs)}개, span {len(spans)}개")
                
            except Exception as debug_error:
                print(f"  디버깅 정보 수집 실패: {debug_error}")
        
        return info
    
    def extract_preferential_conditions(self):
        """우대조건 추출"""
        conditions = []
        
        try:
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                first_row = table.find_elements(By.TAG_NAME, "tr")
                if first_row:
                    header_text = first_row[0].text
                    if '우대' in header_text or '추가' in header_text:
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        
                        for i in range(1, len(rows)):
                            cells = rows[i].find_elements(By.CSS_SELECTOR, "td, th")
                            if len(cells) >= 2:
                                condition = self.clean_text(cells[0].text)
                                detail = self.clean_text(cells[1].text) if len(cells) > 1 else condition
                                rate = 0
                                
                                if len(cells) > 2:
                                    rate_text = cells[2].text
                                    extracted_rate = self.extract_number(rate_text)
                                    if extracted_rate is not None:
                                        rate = extracted_rate
                                
                                if condition and len(condition) > 1:
                                    conditions.append({
                                        "조건": condition,
                                        "상세내용": detail or condition,
                                        "추가금리": rate or 0
                                    })
        
        except Exception as e:
            print(f"우대조건 추출 중 오류: {e}")
        
        return conditions
    
    def extract_period_rates(self):
        """기간별금리 추출"""
        rates = []
        
        try:
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                    if len(cells) >= 2:
                        period_text = cells[0].text
                        rate_text = cells[1].text
                        
                        if re.search(r'\d+.*?[개월년]', period_text) and re.search(r'\d+\.?\d*%?', rate_text):
                            period = self.clean_text(period_text)
                            rate = self.extract_number(rate_text)
                            
                            if period and rate:
                                rates.append({
                                    "기간": period,
                                    "기본금리": rate
                                })
        
        except Exception as e:
            print(f"기간별금리 추출 중 오류: {e}")
        
        return rates
    
    def create_basic_product(self, product_info):
        """기본 상품 객체 생성"""
        return {
            "은행명": "아이엠뱅크",
            "상품명": product_info['name'],
            "상품유형": "적금" if self.current_category == "목돈만들기" else "예금",
            "상품카테고리": self.current_category,
            "상품상세URL": f"https://www.imbank.co.kr/fnp_ebz_22010_depo.act?productCode={product_info['code']}",
            "크롤링일시": datetime.now().strftime('%Y-%m-%d'),
            "가입금액": "",
            "가입대상": "",
            "가입방법": "",
            "계약기간": "",
            "기본금리": product_info['basic_rate'],
            "최대금리": product_info['max_rate'],
            "세제혜택": None,
            "예금자보호": "5천만원 한도 보호",
            "우대조건": [],
            "금리계산방식": "단리",
            "기간별금리": []
        }
    
    def crawl_category(self, category, url_code):
        """카테고리별 크롤링"""
        print(f"\n🎯 === {category} 크롤링 시작 ===")
        self.current_category = category
        
        try:
            if not self.navigate_to_category_in_iframe(category, url_code):
                raise Exception("카테고리 페이지 로딩 실패")
            
            time.sleep(3)
            
            show_all_success = self.show_all_products_in_one_page()
            if not show_all_success:
                print("⚠️ 전체 상품 표시 실패, 현재 페이지 상품만 크롤링")
            
            all_products = self.extract_all_products_from_page()
            print(f"📋 {category}에서 총 {len(all_products)}개 상품 발견")
            
            if len(all_products) == 0:
                print(f"❌ {category}에서 상품을 찾을 수 없습니다")
                return []
            
            category_products = []
            
            for i, product_info in enumerate(all_products):
                print(f"\n[{i + 1}/{len(all_products)}] {product_info['name']} 처리 시작")
                
                try:
                    detailed_product = self.extract_detailed_product_info(product_info)
                    category_products.append(detailed_product)
                    print(f"✅ [{i + 1}/{len(all_products)}] {product_info['name']} 완료")
                    
                except Exception as product_error:
                    print(f"❌ [{i + 1}/{len(all_products)}] {product_info['name']} 실패: {product_error}")
                    basic_product = self.create_basic_product(product_info)
                    category_products.append(basic_product)
                
                time.sleep(1.5)
            
            print(f"🎉 {category} 크롤링 완료!")
            print(f"📊 수집 결과: {len(category_products)}개 상품")
            
            return category_products
            
        except Exception as e:
            print(f"❌ {category} 크롤링 중 치명적 오류: {e}")
            self.errors.append(f"{category}: {str(e)}")
            return []
    
    def crawl_period_rates(self, category, deop_dv):
        """기간별 금리 페이지에서 모든 상품의 금리 정보 추출"""
        try:
            print(f"\n📊 === {category} 기간별 금리 정보 추출 시작 ===")
            
            # 메인 프레임으로 돌아가기
            self.driver.switch_to.default_content()
            
            # 기간별 금리 페이지로 이동
            if category == "목돈만들기":
                pd_cd = "10521001000598001"
            else:
                pd_cd = "10511008000996000"
            
            rate_url = f"https://www.imbank.co.kr/fnp_ebz_31010_depo.act?deopDv={deop_dv}&pdCd={pd_cd}"
            print(f"🔄 기간별 금리 페이지로 이동: {rate_url}")
            
            # iframe에 기간별 금리 URL 설정
            self.driver.execute_script(f"document.getElementById('ifr').src = '{rate_url}';")
            time.sleep(8)
            
            # iframe으로 전환
            iframe = self.driver.find_element(By.ID, "ifr")
            self.driver.switch_to.frame(iframe)
            
            # 페이지 로딩 대기
            if not self.wait_for_iframe_complete():
                print("❌ 기간별 금리 페이지 로딩 실패")
                return {}
            
            print("🔍 페이지 전체 구조 분석 중...")
            
            # 상품 선택 드롭다운 찾기
            select_element = None
            
            selectors = [
                'select[name*="상품"]',
                'select[name*="product"]',
                'select[id*="상품"]',
                'select[id*="product"]',
                'select'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        select_element = elements[0]
                        print(f"✅ 상품 선택 요소 발견 ({selector})")
                        break
                except:
                    continue
            
            if not select_element:
                all_selects = self.driver.find_elements(By.TAG_NAME, "select")
                print(f"📋 페이지 내 모든 select 요소: {len(all_selects)}개")
                
                for i, select in enumerate(all_selects):
                    options = select.find_elements(By.TAG_NAME, "option")
                    if len(options) > 3:
                        select_element = select
                        print(f"🎯 상품 선택으로 추정되는 select 요소 선택")
                        break
            
            if not select_element:
                print("❌ 상품 선택 드롭다운을 찾을 수 없습니다")
                return {}
            
            options = select_element.find_elements(By.TAG_NAME, "option")
            print(f"📋 {len(options)}개 상품 옵션 발견")
            
            period_rates_data = {}
            
            # 각 상품 옵션을 순회하며 금리 정보 추출
            for i, option in enumerate(options):
                product_code = option.get_attribute('value')
                product_name = self.clean_text(option.text)
                
                if not product_code or product_code == '' or product_name in ['선택하세요', '']:
                    print(f"⏭️ 건너뛰기: \"{product_name}\" (값: \"{product_code}\")")
                    continue
                
                print(f"\n[{i + 1}/{len(options)}] {product_name} 기간별 금리 추출 중...")
                
                try:
                    # 상품 선택
                    print(f"🔄 상품 선택: {product_code}")
                    Select(select_element).select_by_value(product_code)
                    time.sleep(1)
                    
                    # 조회 버튼 찾기 및 클릭
                    search_button_clicked = False
                    
                    try:
                        form = select_element.find_element(By.XPATH, "./ancestor::form")
                        buttons = form.find_elements(By.CSS_SELECTOR, "button, input[type='submit'], input[type='button']")
                        
                        for button in buttons:
                            button_text = button.text or button.get_attribute('value') or ''
                            if any(keyword in button_text for keyword in ['조회', '검색', '확인']):
                                print(f"🔘 {button_text} 버튼 클릭")
                                button.click()
                                search_button_clicked = True
                                break
                    except:
                        pass
                    
                    if not search_button_clicked:
                        all_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button, input[type='submit'], input[type='button']")
                        for button in all_buttons:
                            button_text = button.text or button.get_attribute('value') or ''
                            if any(keyword in button_text for keyword in ['조회', '검색', '확인']):
                                print(f"🔘 {button_text} 버튼 클릭")
                                button.click()
                                search_button_clicked = True
                                break
                    
                    print("⏳ 조회 후 테이블 업데이트 대기 중...")
                    time.sleep(6)
                    
                    # 기간별 금리 테이블 추출
                    rate_table = self.extract_rate_table_from_page(product_name)
                    
                    if rate_table:
                        period_rates_data[product_name] = rate_table
                        print(f"✅ {product_name}: {len(rate_table)}개 기간별 금리 추출 완료")
                    else:
                        print(f"⚠️ {product_name}: 기간별 금리 데이터 없음")
                        
                except Exception as e:
                    print(f"❌ {product_name} 기간별 금리 추출 실패: {e}")
                
                time.sleep(2)
            
            print(f"🎉 {category} 기간별 금리 추출 완료: {len(period_rates_data)}개 상품")
            return period_rates_data
            
        except Exception as e:
            print(f"❌ {category} 기간별 금리 추출 중 오류: {e}")
            return {}
    
    def extract_rate_table_from_page(self, product_name):
        """페이지에서 기간별 금리 테이블 추출 - 전체 테이블 정보 누락 없이 추출"""
        print(f"🔍 {product_name} 금리 테이블 전체 추출 시작")
        
        tables = self.driver.find_elements(By.TAG_NAME, "table")
        print(f"📊 총 {len(tables)}개 테이블 발견")
        
        rate_table_data = []
        
        for table_index, table in enumerate(tables):
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            if len(rows) < 2:
                print(f"  Table {table_index}: 행이 부족함 (건너뛰기)")
                continue
            
            table_text = table.text
            
            # 기본 금리 테이블 여부 확인
            has_rate_terms = bool(re.search(r'기간|개월|년|이자율|금리|%', table_text))
            
            if not has_rate_terms:
                print(f"  Table {table_index}: 금리 관련 키워드 없음 (건너뛰기)")
                continue
            
            # 테이블 데이터 전체 추출 (정보 누락 없이)
            table_data = []
            
            for row_index, row in enumerate(rows):
                cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                row_data = []
                
                for cell in cells:
                    cell_text = self.clean_text(cell.text)
                    row_data.append(cell_text)
                
                # 빈 행도 포함 (테이블 구조 유지)
                table_data.append(row_data)
            
            if not table_data or len(table_data) < 2:
                print(f"  Table {table_index}: 유효한 데이터 없음 (건너뛰기)")
                continue
            
            # 헤더 분석을 통한 테이블 유형 판별
            header = table_data[0] if table_data else []
            header_text = ' '.join(header).lower()
            
            print(f"  Table {table_index}: 헤더 분석 - {header}")
            
            # 불필요한 테이블 제외 조건들 (최소한만)
            exclude_conditions = [
                # 상품 선택 드롭다운 테이블
                any(keyword in header_text for keyword in ['조회일자', '상품선택', '전체']) and len(table_data) < 3,
                # 내용이 상품 목록인 경우 (매우 긴 텍스트)
                any('적금' in str(cell) and len(str(cell)) > 200 for row in table_data for cell in row),
                # 헤더가 1개 미만인 경우
                len([h for h in header if h.strip()]) < 1
            ]
            
            if any(exclude_conditions):
                print(f"  Table {table_index}: 제외 조건에 해당함 (불필요한 테이블)")
                continue
            
            # 기간이나 금리 정보가 하나라도 있으면 유효한 테이블로 판단
            has_period_or_rate = False
            
            for row in table_data:
                row_text = ' '.join(row)
                if (re.search(r'\d+\s*(?:개월|년|일)', row_text) or 
                    re.search(r'\d+\.\d+|[0-9]+%', row_text)):
                    has_period_or_rate = True
                    break
            
            if not has_period_or_rate:
                print(f"  Table {table_index}: 기간/금리 데이터 없음 (건너뛰기)")
                continue
            
            # 유효한 금리 테이블로 판단 - 전체 정보 보존
            print(f"  Table {table_index}: ✅ 유효한 금리 테이블로 판정!")
            
            # 테이블 메타 정보
            non_empty_rows = [row for row in table_data if any(cell.strip() for cell in row)]
            max_columns = max(len(row) for row in table_data) if table_data else 0
            
            table_info = {
                "상품명": product_name,
                "테이블인덱스": table_index,
                "총행수": len(table_data),
                "비어있지않은행수": len(non_empty_rows),
                "최대열수": max_columns,
                "헤더": table_data[0] if table_data else [],
                "전체테이블데이터": table_data,  # 모든 행의 모든 데이터
                "원본테이블텍스트": table_text.strip(),
                "테이블HTML": table.get_attribute('outerHTML')  # 추가: HTML 구조도 보존
            }
            
            rate_table_data.append(table_info)
            
            print(f"  ✅ Table {table_index} 전체 추출 완료:")
            print(f"    - 총 행수: {len(table_data)}개")
            print(f"    - 데이터 행수: {len(non_empty_rows)}개") 
            print(f"    - 최대 열수: {max_columns}개")
            
            # 전체 테이블 구조 출력 (모든 행)
            print(f"  📋 전체 테이블 구조:")
            for i, row_data in enumerate(table_data):
                if i < 10:  # 처음 10행만 출력
                    formatted_cells = [f'"{cell}"' for cell in row_data]
                    print(f"    Row {i}: {formatted_cells}")
                elif i == 10 and len(table_data) > 10:
                    print(f"    ... (총 {len(table_data)}개 행)")
                    break
        
        if rate_table_data:
            total_rows = sum(table['총행수'] for table in rate_table_data)
            total_data_rows = sum(table['비어있지않은행수'] for table in rate_table_data)
            print(f"🎉 {product_name} 유효한 금리 테이블 {len(rate_table_data)}개 추출 성공!")
            print(f"📊 전체 {total_rows}개 행 (데이터 {total_data_rows}개 행) 완전 보존")
        else:
            print(f"⚠️ {product_name}: 유효한 금리 테이블을 찾을 수 없음")
        
        return rate_table_data
    
    def find_matching_product(self, target_name, product_list):
        """상품명 매칭"""
        # 정확한 매칭 시도
        for product in product_list:
            if product["상품명"] == target_name:
                return product
        
        # 부분 매칭 시도
        clean_target_name = re.sub(r'[\s\(\)]', '', target_name)
        
        for product in product_list:
            clean_product_name = re.sub(r'[\s\(\)]', '', product["상품명"])
            
            if clean_target_name in clean_product_name or clean_product_name in clean_target_name:
                return product
        
        return None
    
    def merge_period_rates(self, products, period_rates_data):
        """기간별 금리 정보를 기존 상품 데이터에 병합"""
        print("\n🔗 기간별 금리 정보 병합 중...")
        
        merge_success_count = 0
        
        for rate_name, rate_data in period_rates_data.items():
            matched_product = self.find_matching_product(rate_name, products)
            
            if matched_product:
                matched_product["기간별금리"] = rate_data
                merge_success_count += 1
                print(f"✅ {matched_product['상품명']} ← {rate_name} ({len(rate_data)}개 기간)")
            else:
                print(f"⚠️ 매칭 실패: {rate_name}")
        
        print(f"🎯 기간별 금리 병합 완료: {merge_success_count}/{len(period_rates_data)}개 성공")
        return merge_success_count
    
    def save_to_csv(self, products, filename):
        """CSV 파일로 저장"""
        if not products:
            print("저장할 데이터가 없습니다.")
            return
        
        try:
            df = pd.DataFrame(products)
            
            for column in df.columns:
                df[column] = df[column].apply(
                    lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x
                )
            
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"💾 CSV 파일 저장: {filename}")
            
        except Exception as e:
            print(f"❌ CSV 저장 실패: {e}")
    
    def crawl_all_complete(self):
        """완전한 3단계 크롤링 실행"""
        print("🚀 === 아이엠뱅크 완전 크롤링 시작 (기간별 금리 포함) ===")
        print("📋 1단계: 상품 기본정보 + 상세정보 수집")
        print("📊 2단계: 기간별 금리 페이지에서 금리 테이블 수집")
        print("🔗 3단계: 기간별 금리 정보 병합")
        print("⏱️ 예상 소요 시간: 25-35분")
        
        self.products = []
        self.errors = []
        
        try:
            # 드라이버 설정
            self.setup_driver()
            
            # 메인 페이지로 이동하고 iframe 찾기
            if not self.go_to_main_page_and_find_iframe():
                raise Exception("메인 페이지에서 iframe을 찾을 수 없습니다")
            
            print("✅ iframe 발견 완료 - 이제 3단계 크롤링을 시작합니다")
            
            # 1단계: 기본 상품 정보 크롤링
            print("\n🎯 === 1단계: 목돈만들기 기본정보 크롤링 ===")
            mokdon_making = self.crawl_category("목돈만들기", "22010")
            self.products.extend(mokdon_making)
            print(f"\n📊 1-1단계 완료: {len(mokdon_making)}개 상품 수집")
            
            print("\n🎯 === 1단계: 목돈굴리기 기본정보 크롤링 ===")
            mokdon_rolling = self.crawl_category("목돈굴리기", "23010")
            self.products.extend(mokdon_rolling)
            print(f"\n📊 1-2단계 완료: {len(mokdon_rolling)}개 상품 수집")
            
            # 2단계: 기간별 금리 정보 수집
            print("\n📊 === 2단계: 기간별 금리 정보 수집 ===")
            
            print("\n🔢 목돈만들기 기간별 금리 수집...")
            mokdon_making_rates = self.crawl_period_rates("목돈만들기", 1)
            
            print("\n🔢 목돈굴리기 기간별 금리 수집...")
            mokdon_rolling_rates = self.crawl_period_rates("목돈굴리기", 2)
            
            # 3단계: 기간별 금리 정보 병합
            print("\n🔗 === 3단계: 기간별 금리 정보 병합 ===")
            
            mokdon_making_products = [p for p in self.products if p["상품카테고리"] == "목돈만들기"]
            mokdon_rolling_products = [p for p in self.products if p["상품카테고리"] == "목돈굴리기"]
            
            making_merge_count = self.merge_period_rates(mokdon_making_products, mokdon_making_rates)
            rolling_merge_count = self.merge_period_rates(mokdon_rolling_products, mokdon_rolling_rates)
            
            # 최종 결과
            result = {
                "크롤링일시": datetime.now().isoformat(),
                "총상품수": len(self.products),
                "목돈만들기": len(mokdon_making),
                "목돈굴리기": len(mokdon_rolling),
                "기간별금리병합": {
                    "목돈만들기": making_merge_count,
                    "목돈굴리기": rolling_merge_count,
                    "총병합수": making_merge_count + rolling_merge_count
                },
                "목표달성률": f"{round((len(self.products) / 57) * 100)}%",
                "오류목록": self.errors,
                "products": self.products
            }
            
            print(f"\n🎉 === 완전 크롤링 최종 완료 (기간별 금리 포함) ===")
            print(f"📊 총 수집 상품: {len(self.products)}개")
            print(f"💰 목돈만들기: {len(mokdon_making)}개")
            print(f"💰 목돈굴리기: {len(mokdon_rolling)}개")
            print(f"📈 목표 달성률: {round((len(self.products) / 57) * 100)}%")
            print(f"🔢 기간별 금리 병합: {making_merge_count + rolling_merge_count}개 상품")
            print(f"⚠️ 오류 발생: {len(self.errors)}건")
            
            if self.errors:
                print("❌ 오류 목록:", self.errors)
            
            # 상세 정보 추출 성공률 확인
            detail_success_count = 0
            period_rate_success_count = 0
            
            if len(self.products) > 0:
                for product in self.products:
                    if any([product.get("가입대상"), product.get("가입금액"), product.get("가입방법"), product.get("계약기간")]):
                        detail_success_count += 1
                    if product.get("기간별금리"):
                        period_rate_success_count += 1
                
                print(f"📝 상세 정보 추출 성공률: {round((detail_success_count / len(self.products)) * 100)}% ({detail_success_count}/{len(self.products)})")
                print(f"📊 기간별 금리 추출 성공률: {round((period_rate_success_count / len(self.products)) * 100)}% ({period_rate_success_count}/{len(self.products)})")
            
            # CSV 파일 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f"아이엠뱅크_완전크롤링_기간별금리포함_{timestamp}.csv"
            self.save_to_csv(self.products, csv_filename)
            
            # JSON 파일 저장
            json_filename = f"아이엠뱅크_완전크롤링결과_{timestamp}.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"💾 JSON 파일 저장: {json_filename}")
            
            print(f"\n💾 CSV 파일 다운로드: {csv_filename}")
            print("📋 결과가 완전히 저장되었습니다")
            
            return result
            
        except Exception as e:
            print(f"❌ 전체 크롤링 중 치명적 오류: {e}")
            return None
        finally:
            if self.driver:
                print("🔄 브라우저 종료...")
                self.driver.quit()

    def start(self):
        """메인 실행 함수"""
        print("🎯 IM은행 완전 크롤러 - 3단계 포함 최종 버전")
        print("JavaScript 콘솔 코드와 정확히 동일한 3단계 플로우를 구현합니다")

        result = self.crawl_all_complete()
        if result:
            print(f"🎉 완전 크롤링 성공! 총 {result['총상품수']}개 상품 수집")
            print(f"🔢 기간별 금리 병합: {result['기간별금리병합']['총병합수']}개 상품")

