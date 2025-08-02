import os

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import re
import dotenv

from src.preprocessing.crawling.BankLink import BankLink


class WooriBankCrawler:
    # 우리은행 예적금 상품 크롤러 초기화
    def __init__(self, headless=True):
        self.base_url = BankLink.WOORI_BANK_BASE_LINK.value
        self.deposit_url = BankLink.WOORI_BANK_DEPOSIT_LINK.value   # 목돈굴리기상품
        self.savings_url =   BankLink.WOORI_BANK_SAVINGS_LINK.value# 목돈모으기상품
        self.driver = self.setup_driver(headless)
        self.all_products = []
        
    # Chrome 브라우저 설정
    def setup_driver(self, headless=True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    
    # 예금과 적금 상품 목록 수집
    def collect_all_products(self):
        try:
            print("전체 상품 수집 시작")
            
            print("예금 상품 수집 중...")
            deposit_products = self.collect_products_by_type("예금", self.deposit_url)
            
            print("적금 상품 수집 중...")
            savings_products = self.collect_products_by_type("적금", self.savings_url)
            
            self.all_products = deposit_products + savings_products
            
            print(f"수집 완료 - 예금: {len(deposit_products)}개, 적금: {len(savings_products)}개, 총: {len(self.all_products)}개")
            
        except Exception as e:
            print(f"상품 수집 오류: {str(e)}")
    
    # 특정 타입 상품들 페이지별 수집
    def collect_products_by_type(self, product_type, url):
        products = []
        
        try:
            self.driver.get(url)
            time.sleep(3)
            
            page_num = 1
            while True:
                page_products = self.collect_products_from_current_page(product_type)
                if not page_products:
                    break
                
                products.extend(page_products)
                
                if not self.go_to_next_page():
                    break
                
                page_num += 1
                time.sleep(2)
            
        except Exception as e:
            print(f"{product_type} 수집 오류: {str(e)}")
        
        return products
    
    # 현재 페이지의 상품 목록 추출
    def collect_products_from_current_page(self, product_type):
        products = []
        
        try:
            product_links = self.driver.find_elements(By.CSS_SELECTOR, "a[onclick*='goDetails']")
            
            product_dict = {}
            
            for link in product_links:
                try:
                    onclick = link.get_attribute("onclick")
                    match = re.search(r"goDetails\([^,]+,\s*['\"]([^'\"]+)['\"]", onclick)
                    
                    if not match:
                        continue
                        
                    product_code = match.group(1)
                    text = link.text.strip()
                    
                    if product_code not in product_dict:
                        product_dict[product_code] = {
                            'product_type': product_type,
                            'product_code': product_code,
                            'name': '',
                            'interest_rate': '',
                            'description': '',
                            'detail_button_onclick': ''
                        }
                    
                    if text == '상세보기':
                        product_dict[product_code]['detail_button_onclick'] = onclick
                    elif text and len(text) > 2:
                        product_dict[product_code]['name'] = text
                        
                        rate, desc = self.extract_info_around_element(link)
                        if rate:
                            product_dict[product_code]['interest_rate'] = rate
                        if desc:
                            product_dict[product_code]['description'] = desc
                            
                except Exception as e:
                    continue
            
            for code, info in product_dict.items():
                if info['name'] and info['detail_button_onclick']:
                    products.append(info)
            
        except Exception as e:
            print(f"현재 페이지 상품 수집 오류: {str(e)}")
        
        return products
    
    # 링크 주변 요소에서 금리와 설명 정보 추출
    def extract_info_around_element(self, element):
        interest_rate = ""
        description = ""
        
        try:
            current = element
            for level in range(5):
                try:
                    current = current.find_element(By.XPATH, "..")
                    text = current.text
                    
                    if not interest_rate:
                        rate_patterns = [r'연\s*(\d+\.?\d*%)', r'(\d+\.?\d*%)']
                        for pattern in rate_patterns:
                            match = re.search(pattern, text)
                            if match:
                                interest_rate = match.group(1)
                                break
                    
                    if not description and len(text) > 20:
                        lines = text.split('\n')
                        desc_parts = []
                        for line in lines:
                            line = line.strip()
                            if (line and len(line) > 5 and line not in ['상세보기', interest_rate] 
                                and not line.startswith('P0') and '[' in line):
                                desc_parts.append(line)
                                if len(desc_parts) >= 3:
                                    break
                        
                        if desc_parts:
                            description = ' | '.join(desc_parts)[:200]
                    
                    if interest_rate and description:
                        break
                        
                except:
                    break
                    
        except Exception as e:
            pass
        
        return interest_rate, description
    
    # 다음 페이지로 이동
    def go_to_next_page(self):
        try:
            next_selectors = [
                "//a[contains(@class, 'next')]",
                "//button[contains(@class, 'next')]", 
                "//a[contains(text(), '다음')]",
                "//button[contains(text(), '다음')]",
                "//a[@title='다음페이지']",
                "//a[contains(@onclick, 'next')]",
                "//*[contains(@class, 'pagination')]//a[last()]",
                "//img[@alt='다음']/.."
            ]
            
            for selector in next_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            class_name = element.get_attribute("class") or ""
                            if "disabled" not in class_name.lower():
                                self.driver.execute_script("arguments[0].click();", element)
                                time.sleep(3)
                                return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            return False
    
    # 각 상품의 상세정보 수집
    def collect_all_detail_info(self):
        try:
            print("상품별 상세정보 수집 시작")
            
            for i, product in enumerate(self.all_products):
                try:
                    print(f"[{i+1}/{len(self.all_products)}] {product['name']} ({product['product_type']}) 처리 중...")
                    
                    if product['product_type'] == "예금":
                        self.driver.get(self.deposit_url)
                    else:
                        self.driver.get(self.savings_url)
                    time.sleep(2)
                    
                    detail_button = self.find_detail_button_by_onclick(product['detail_button_onclick'])
                    
                    if detail_button:
                        detail_info = self.get_detail_info_safe(detail_button, product['product_code'])
                        product['detail_info'] = detail_info
                        
                        # 수집된 필드 개수 확인
                        collected_fields = len([v for k, v in detail_info.items() 
                                              if k not in ['raw_data', 'url'] and v])
                        print(f"    수집 완료: {collected_fields}/7개 필드")
                    else:
                        print(f"    오류: 상세보기 버튼 찾기 실패")
                        product['detail_info'] = {'error': 'detail button not found'}
                        
                except Exception as e:
                    print(f"    오류: {str(e)}")
                    product['detail_info'] = {'error': str(e)}
                    continue
            
            print("모든 상품 상세정보 수집 완료")
            
        except Exception as e:
            print(f"상세정보 수집 오류: {str(e)}")
    
    # 특정 onclick 속성을 가진 상세보기 버튼 찾기
    def find_detail_button_by_onclick(self, target_onclick):
        try:
            all_links = self.driver.find_elements(By.CSS_SELECTOR, "a[onclick*='goDetails']")
            
            for link in all_links:
                onclick = link.get_attribute("onclick")
                text = link.text.strip()
                
                if onclick == target_onclick and text == '상세보기':
                    return link
            
            return None
            
        except Exception as e:
            return None
    
    # 안전하게 상세정보 수집 (창 관리 포함)
    def get_detail_info_safe(self, detail_button, product_code):
        detail_info = {}
        main_window = self.driver.current_window_handle
        
        try:
            print(f"    상세페이지 접근 중... (코드: {product_code})")
            self.driver.execute_script("arguments[0].click();", detail_button)
            time.sleep(3)
            
            windows = self.driver.window_handles
            
            if len(windows) > 1:
                print("    새 창에서 데이터 추출 중...")
                for window in windows:
                    if window != main_window:
                        self.driver.switch_to.window(window)
                        break
                
                detail_info = self.extract_required_detail_info()
                
                self.driver.close()
                self.driver.switch_to.window(main_window)
                
            else:
                print("    모달창에서 데이터 추출 중...")
                time.sleep(2)
                detail_info = self.extract_required_detail_info()
            
        except Exception as e:
            print(f"    추출 실패: {str(e)}")
            detail_info = {'error': str(e)}
            
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(main_window)
            except:
                pass
        
        return detail_info
    
    # 필수 항목 추출 메인 함수
    def extract_required_detail_info(self):
        detail_info = {
            'url': '',
            '상품종류': '',
            '가입대상': '',
            '가입금액': '',
            '가입기간': '',
            '기본금리': '',
            '우대금리': '',
            '세제혜택': '',
            '가입방법': '',
            'raw_data': {}
        }
        
        try:
            time.sleep(3)
            
            self.extract_product_type(detail_info)
            self.extract_from_tab_area_only(detail_info)
            self.extract_join_method_from_foot(detail_info)
            
            detail_info = self.clean_required_data(detail_info)
            
        except Exception as e:
            detail_info['extraction_error'] = str(e)
        
        return detail_info
    
    # 상품종류 추출
    def extract_product_type(self, detail_info):
        try:
            product_box_elements = self.driver.find_elements(By.CSS_SELECTOR, ".product-box .prd-info dt, .product-box .name")
            
            for element in product_box_elements:
                text = element.text.strip()
                if '상품종류' in text or '목돈굴리기상품' in text or '목돈모으기상품' in text:
                    try:
                        next_element = self.driver.execute_script("return arguments[0].nextElementSibling;", element)
                        if next_element:
                            detail_info['상품종류'] = next_element.text.strip()
                            detail_info['raw_data']['product_type_source'] = 'product_box'
                            return
                    except:
                        continue
            
            if not detail_info['상품종류']:
                try:
                    breadcrumb_elements = self.driver.find_elements(By.CSS_SELECTOR, ".breadcrumb, .location")
                    for element in breadcrumb_elements:
                        text = element.text
                        if '목돈굴리기상품' in text:
                            detail_info['상품종류'] = '목돈굴리기상품'
                            detail_info['raw_data']['product_type_source'] = 'breadcrumb'
                            return
                        elif '목돈모으기상품' in text:
                            detail_info['상품종류'] = '목돈모으기상품'
                            detail_info['raw_data']['product_type_source'] = 'breadcrumb'
                            return
                except:
                    pass
                    
        except Exception as e:
            detail_info['raw_data']['product_type_error'] = str(e)
    
    # 상품설명 탭 영역에서 정보 추출
    def extract_from_tab_area_only(self, detail_info):
        try:
            current_url = self.driver.current_url
            detail_info['url'] = current_url
            
            tab_area = None
            tab_selectors = [
                ".tab-content",
                "#product_func_tab", 
                ".product-functab-content",
                ".tab-area .tab-content",
                "[class*='tab'][class*='content']"
            ]
            
            for selector in tab_selectors:
                try:
                    tab_area = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if tab_area.is_displayed():
                        detail_info['raw_data']['tab_area_selector'] = selector
                        break
                except:
                    continue
            
            if tab_area:
                tab_dls = tab_area.find_elements(By.TAG_NAME, "dl")
                
                for dl_index, dl in enumerate(tab_dls):
                    if not dl.is_displayed():
                        continue
                        
                    dts = dl.find_elements(By.TAG_NAME, "dt")
                    dds = dl.find_elements(By.TAG_NAME, "dd")
                    
                    for i, dt in enumerate(dts):
                        if i < len(dds):
                            dt_text = dt.text.strip().replace(' ', '')
                            dd_text = dds[i].text.strip()
                            
                            if dt_text and dd_text:
                                if '가입대상' in dt_text and not detail_info['가입대상']:
                                    detail_info['가입대상'] = dd_text
                                    detail_info['raw_data']['가입대상_source'] = f'tab_dl_{dl_index}'
                                    
                                elif ('가입금액' in dt_text or '적립금액' in dt_text) and not detail_info['가입금액']:
                                    detail_info['가입금액'] = dd_text
                                    detail_info['raw_data']['가입금액_source'] = f'tab_dl_{dl_index}'
                                    
                                elif '가입기간' in dt_text and not detail_info['가입기간']:
                                    detail_info['가입기간'] = dd_text
                                    detail_info['raw_data']['가입기간_source'] = f'tab_dl_{dl_index}'
                                    
                                elif '기본금리' in dt_text and not detail_info['기본금리']:
                                    detail_info['기본금리'] = dd_text
                                    detail_info['raw_data']['기본금리_source'] = f'tab_dl_{dl_index}'
                                    
                                elif '우대금리' in dt_text and not detail_info['우대금리']:
                                    detail_info['우대금리'] = dd_text
                                    detail_info['raw_data']['우대금리_source'] = f'tab_dl_{dl_index}'
                                    
                                elif ('세제혜택' in dt_text or '세금' in dt_text or '과세' in dt_text) and not detail_info['세제혜택']:
                                    detail_info['세제혜택'] = dd_text
                                    detail_info['raw_data']['세제혜택_source'] = f'tab_dl_{dl_index}'
                                    
                                elif '가입방법' in dt_text and not detail_info['가입방법']:
                                    detail_info['가입방법'] = dd_text
                                    detail_info['raw_data']['가입방법_source'] = f'tab_dl_{dl_index}'
            else:
                self.extract_from_all_dl_structure(detail_info)
                
        except Exception as e:
            detail_info['raw_data']['tab_area_error'] = str(e)
    
    # 전체 페이지에서 DL 구조 추출 (대안 방법)
    def extract_from_all_dl_structure(self, detail_info):
        try:
            if not detail_info.get('url'):
                detail_info['url'] = self.driver.current_url
                
            dls = self.driver.find_elements(By.TAG_NAME, "dl")
            
            for dl_index, dl in enumerate(dls):
                if not dl.is_displayed():
                    continue
                    
                dts = dl.find_elements(By.TAG_NAME, "dt")
                dds = dl.find_elements(By.TAG_NAME, "dd")
                
                for i, dt in enumerate(dts):
                    if i < len(dds):
                        dt_text = dt.text.strip().replace(' ', '')
                        dd_text = dds[i].text.strip()
                        
                        if dt_text and dd_text:
                            mapped_key = self.map_to_required_field(dt_text)
                            if mapped_key and mapped_key in detail_info and not detail_info[mapped_key]:
                                detail_info[mapped_key] = dd_text
                                detail_info['raw_data'][f'{mapped_key}_source'] = f'all_dl_{dl_index}'
                                
        except Exception as e:
            detail_info['raw_data']['all_dl_error'] = str(e)
    
    # dd.foot 영역에서 가입방법 보완 추출
    def extract_join_method_from_foot(self, detail_info):
        try:
            if detail_info['가입방법']:
                return
                
            foot_elements = self.driver.find_elements(By.CSS_SELECTOR, "dd.foot")
            
            for foot in foot_elements:
                if foot.is_displayed():
                    text = foot.text.strip()
                    if text and len(text) > 10:
                        join_keywords = ['인터넷', '스마트폰', '전화', '영업점']
                        keyword_count = sum(1 for keyword in join_keywords if keyword in text)
                        
                        if keyword_count >= 2:
                            detail_info['가입방법'] = text
                            detail_info['raw_data']['가입방법_source'] = 'dd_foot'
                            break
                            
        except Exception as e:
            detail_info['raw_data']['foot_method_error'] = str(e)
    
    # 키워드를 필드명으로 매핑
    def map_to_required_field(self, keyword):
        keyword_clean = keyword.strip().replace(' ', '').replace(':', '')
        
        mapping = {
            '가입금액': '가입금액',
            '적립금액': '가입금액',
            '납입금액': '가입금액',
            '가입대상': '가입대상',
            '가입조건': '가입대상',
            '대상': '가입대상',
            '가입기간': '가입기간',
            '기간': '가입기간',
            '만기': '가입기간',
            '기본금리': '기본금리',
            '기본이율': '기본금리',
            '우대금리': '우대금리', 
            '우대이율': '우대금리',
            '세제혜택': '세제혜택',
            '세금': '세제혜택',
            '과세': '세제혜택',
            '비과세': '세제혜택',
            '가입방법': '가입방법'
        }
        
        return mapping.get(keyword_clean, None)
    
    # 추출된 데이터 정제
    def clean_required_data(self, detail_info):
        cleaned_data = {}
        
        for key, value in detail_info.items():
            if key == 'raw_data':
                cleaned_data[key] = value
                continue
                
            if isinstance(value, str):
                value = value.strip()
                value = re.sub(r'\n+', '\n', value)
                value = re.sub(r'\s+', ' ', value)
                
                if '금리보기' in value:
                    value = value.replace('금리보기', '').strip()
                    value = re.sub(r'\s+', ' ', value)
                
                if value:
                    cleaned_data[key] = value
            elif value:
                cleaned_data[key] = value
        
        return cleaned_data
    
    # JSON 파일 저장
    def save_data(self, filename="woori_bank_products.json"):
        dotenv.load_dotenv()
        directory_path = os.getenv("JSON_RESULT_PATH")

        os.makedirs(directory_path, exist_ok=True)

        full_path = os.path.join(directory_path, filename)


        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(self.all_products, f, ensure_ascii=False, indent=2)
            print(f"JSON 데이터가 {filename}에 저장되었습니다.")
        except Exception as e:
            print(f"JSON 저장 오류: {str(e)}")
    
    # 수집 결과 요약 출력
    def print_summary(self):
        print("수집 결과 요약")
        
        total_products = len(self.all_products)
        deposit_count = len([p for p in self.all_products if p['product_type'] == '예금'])
        savings_count = len([p for p in self.all_products if p['product_type'] == '적금'])
        
        print(f"전체 상품: {total_products}개")
        print(f"예금: {deposit_count}개")
        print(f"적금: {savings_count}개")
        
        successful_details = 0
        field_stats = {
            '상품종류': 0, '가입대상': 0, '가입금액': 0, '가입기간': 0, 
            '기본금리': 0, '우대금리': 0, '세제혜택': 0, '가입방법': 0
        }
        
        for product in self.all_products:
            detail_info = product.get('detail_info', {})
            if detail_info and not detail_info.get('error'):
                successful_details += 1
                for field in field_stats:
                    if detail_info.get(field):
                        field_stats[field] += 1
        
        print("상세정보 수집 현황:")
        print(f"성공: {successful_details}개 ({successful_details/total_products*100:.1f}%)")
        for field, count in field_stats.items():
            print(f"{field}: {count}개")
        
        url_count = len([p for p in self.all_products 
                        if p.get('detail_info', {}).get('url')])
        print(f"URL: {url_count}개")
    
    # 크롤링 실행
    def run(self):
        try:
            from datetime import datetime
            start_time = datetime.now()
            
            print("우리은행 예금/적금 크롤링 시작")
            print(f"실행 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            self.collect_all_products()
            
            if not self.all_products:
                print("상품 목록을 수집하지 못했습니다.")
                return None
            
            self.collect_all_detail_info()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print("크롤링 완료")
            print(f"소요 시간: {duration:.1f}초")
            
            self.print_summary()
            
            self.save_data()
            
            return {
                'timestamp': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_seconds': duration,
                'total_products': len(self.all_products),
                'deposit_count': len([p for p in self.all_products if p['product_type'] == '예금']),
                'savings_count': len([p for p in self.all_products if p['product_type'] == '적금'])
            }
            
        except Exception as e:
            print(f"크롤링 오류: {str(e)}")
            return None
        finally:
            self.driver.quit()

    def start(self):
        print("우리은행 예금/적금 크롤러 v2.0")
        print("예금(목돈굴리기) + 적금(목돈모으기) 전체 수집")
        print("7개 필수 항목 구조화 추출")

        result = self.run()

        if result:
            print("크롤링 성공")
            print(f"파일: woori_bank_products.json")
            print(f"예금 {result['deposit_count']}개 + 적금 {result['savings_count']}개 = 총 {result['total_products']}개")
        else:
            print("크롤링 실패")
