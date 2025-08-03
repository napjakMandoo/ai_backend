"""
국민은행 예적금 상품 크롤링 - 기본이율/우대이율 수집
"""
import logging
import time
import json
from datetime import datetime

from poetry.utils.helpers import directory
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import dotenv
import os

from src.preprocessing.crawling.BankLink import BankLink

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

class KBProductCrawler:
    # 국민은행 예적금 상품 크롤러 초기화
    def __init__(self, headless=True):
        self.base_url = BankLink.KB_BANK_LINK.value
        self.savings_url = BankLink.KB_SAVINGS_LINK.value
        self.driver = self.setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 15)
        self.all_products = []
        self.logger = logging.getLogger(__name__)
        
    # Chrome 브라우저 설정
    def setup_driver(self, headless):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        try:
            if WEBDRIVER_MANAGER_AVAILABLE:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            raise Exception(f"ChromeDriver 설정 실패: {e}")
            
        return driver
    
    # 페이지네이션 확인 및 이동
    def check_pagination(self, tab_name):
        try:
            self.logger.info(f"    다음 페이지 확인 중...")
            
            has_gopage = self.driver.execute_script("return typeof window.goPage === 'function';")
            
            if not has_gopage:
                self.logger.info(f"    goPage 함수 없음 - 페이지네이션 없음")
                return False
            
            before_products = []
            try:
                product_elements = self.driver.find_elements(By.XPATH, "//a[@title='상세정보' or contains(@onclick, 'dtlDeposit')]")
                for elem in product_elements[:3]:
                    try:
                        li_parent = elem.find_element(By.XPATH, "./ancestor::li[1]")
                        text = li_parent.text.strip().split('\n')[0]
                        before_products.append(text)
                    except:
                        pass
            except:
                pass
            
            try:
                current_page = 1
                current_url = self.driver.current_url
                if '#CP' in current_url:
                    next_page = 2
                else:
                    next_page = 2
                
                self.logger.info(f"    goPage({next_page}) 시도 중...")
                
                self.driver.execute_script(f"window.goPage({next_page});")
                time.sleep(4)
                
                after_products = []
                try:
                    product_elements_after = self.driver.find_elements(By.XPATH, "//a[@title='상세정보' or contains(@onclick, 'dtlDeposit')]")
                    for elem in product_elements_after[:3]:
                        try:
                            li_parent = elem.find_element(By.XPATH, "./ancestor::li[1]")
                            text = li_parent.text.strip().split('\n')[0]
                            after_products.append(text)
                        except:
                            pass
                except:
                    pass
                
                if len(after_products) > 0 and after_products != before_products:
                    self.logger.info(f"    {next_page}페이지로 이동 성공")
                    return True
                else:
                    self.logger.info(f"    {next_page}페이지 없음 또는 동일한 상품")
                    self.driver.execute_script("window.goPage(1);")
                    time.sleep(3)
                    return False
                    
            except Exception as e:
                self.logger.info(f"    오류: goPage 이동 실패: {e}")
                return False
            
        except Exception as e:
            self.logger.info(f"    오류: 페이지네이션 오류: {e}")
            return False
    
    # 페이지에서 상품 수집
    def get_products_from_page(self, tab_name, page_num=1):
        all_products = []
        
        try:
            self.logger.info(f"{tab_name} 상품 수집 (페이지 {page_num})")
            
            time.sleep(3)
            
            detail_buttons = self.driver.find_elements(By.XPATH, "//a[@title='상세정보' or contains(@onclick, 'dtlDeposit')]")
            
            if not detail_buttons:
                detail_buttons = self.driver.find_elements(By.CSS_SELECTOR, "a[onclick*='dtlDeposit']")
            
            self.logger.info(f"상품 버튼 {len(detail_buttons)}개 발견")
            
            products = []
            for i, button in enumerate(detail_buttons):
                try:
                    li_parent = button.find_element(By.XPATH, "./ancestor::li[1]")
                    all_text = li_parent.text.strip()
                    lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                    
                    product_name = None
                    for line in lines:
                        if (len(line) > 3 and 
                            line not in ['상세정보', '가입하기'] and
                            ('KB' in line or '적금' in line or '예금' in line or '정기' in line)):
                            product_name = line
                            break
                    
                    if not product_name and lines:
                        product_name = lines[0]
                    
                    if product_name:
                        clean_name = product_name.replace('상세정보', '').replace('가입하기', '').strip()
                        
                        if clean_name.upper().endswith('NEW'):
                            clean_name = clean_name[:-3].strip()
                        
                        onclick_value = button.get_attribute('onclick')
                        
                        if len(clean_name) > 2:
                            products.append({
                                'category': tab_name,
                                'page': page_num,
                                'index': len(products) + 1,
                                'name': clean_name,
                                'url': onclick_value,
                                'button_element': button
                            })
                            self.logger.info(f"    {len(products)}. {clean_name}")
                
                except Exception as e:
                    continue
            
            all_products.extend(products)
            
            if self.check_pagination(tab_name):
                next_page_products = self.get_products_from_page(tab_name, page_num + 1)
                all_products.extend(next_page_products)
            
            return all_products
            
        except Exception as e:
            self.logger.info(f"오류: {tab_name} 상품 수집 오류: {e}")
            return all_products
        
# 상품 상세정보 추출 - 기본이율/우대이율 추가
    def extract_detail_info(self, product_url, product_name, button_element):
        detail_info = {}
        main_window = self.driver.current_window_handle
        
        try:
            self.logger.info(f"    상세페이지 접근 중... (상품: {product_name})")
            
            # 실제 상품 상세 URL 추출 부분 추가
            actual_detail_url = None
            try:
                current_url = self.driver.current_url
                
                # 상세 페이지로 이동
                if product_url and 'dtlDeposit' in str(product_url):
                    self.driver.execute_script(product_url)
                elif button_element:
                    try:
                        button_element.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", button_element)
                
                time.sleep(3)  # 페이지 로딩 대기
                
                # 현재 URL이 상세 페이지 URL인지 확인
                new_url = self.driver.current_url
                if new_url != current_url and len(new_url) > 50:  # URL이 변경되고 충분히 긴 경우
                    actual_detail_url = new_url
                    self.logger.info(f"    실제 상품 URL 수집 완료")
                
            except Exception as e:
                self.logger.info(f"    오류: 실제 URL 수집 실패: {e}")
            
            # detail_url을 detail_info에 추가
            if actual_detail_url:
                detail_info['detail_url'] = actual_detail_url
            
            time.sleep(5)  # 페이지 로딩 대기 시간 증가
            
            # 상품안내 탭 정보 수집
            product_info = self.extract_product_guide_info_improved()
            detail_info.update(product_info)
            
            # 유의사항 탭으로 이동 후 정보 수집
            notice_info = self.extract_notice_info_improved()
            detail_info.update(notice_info)
            
            # 기본이율/우대이율 정보 수집 (대안 방식 포함)
            interest_rate_info = self.extract_interest_rate_info()
            detail_info.update(interest_rate_info)
            
            # 메인 창으로 복귀
            current_windows = self.driver.window_handles
            if len(current_windows) > 1:
                self.driver.close()
            self.driver.switch_to.window(main_window)
            
            self.logger.info(f"    수집 완료: {len(detail_info)}개 항목 추출 완료")
            
        except Exception as e:
            self.logger.info(f"    오류: 상세정보 추출 오류: {e}")
            try:
                self.driver.switch_to.window(main_window)
            except:
                pass
        
        return detail_info
    
    # 기본이율/우대이율 정보 추출 - 개선된 로직
    def extract_interest_rate_info(self):
        info = {}
        
        try:
            self.logger.info("        기본이율/우대이율 정보 추출 중...")
            
            # 1단계: 금리 및 이율 탭으로 이동
            if not self.go_to_interest_rate_tab():
                self.logger.info("        오류: 금리 및 이율 탭을 찾을 수 없음")
                return info
            
            time.sleep(3)
            
            # 2단계: '금리' 항목이 있는지 확인 (정확히 '금리' 텍스트만)
            interest_item_found = self.check_interest_item_exists()
            
            if interest_item_found:
                self.logger.info("        금리 항목 존재 확인 - 자세히보기 버튼 찾기")
                # 금리 항목이 있으면 무조건 자세히보기 버튼이 있다고 가정하고 찾기
                detail_button_found = self.find_and_click_detail_button_aggressive()
                
                if detail_button_found:
                    self.logger.info("        자세히보기 버튼 클릭 성공")
                    # 기존 팝업 처리 로직
                    info = self.handle_interest_rate_popup()
                else:
                    self.logger.info("        오류: 자세히보기 버튼을 찾을 수 없음 - 대안 방식 시도")
                    # 대안 방식: '계약기간 중 금리' 정확 매칭으로 테이블 추출
                    info = self.extract_interest_rate_tables_alternative()
            else:
                self.logger.info("        오류: 금리 항목 없음 - 대안 방식 시도")
                # 대안 방식: '계약기간 중 금리' 정확 매칭으로 테이블 추출
                info = self.extract_interest_rate_tables_alternative()
            
            self.logger.info(f"        이율 정보 추출 완료: {list(info.keys())}")
            
        except Exception as e:
            self.logger.info(f"        오류: 기본이율/우대이율 추출 실패: {e}")
        
        return info
    
    # '금리' 텍스트와 완전 일치하는 항목이 페이지에 존재하는지 확인
    def check_interest_item_exists(self):
        try:
            self.logger.info("        금리 완전 일치 항목 존재 여부 확인 중...")
            
            # 방법 1: strong 태그에서 '금리' 완전 일치만 찾기
            strong_elements = self.driver.find_elements(By.TAG_NAME, 'strong')
            for strong in strong_elements:
                try:
                    text = strong.text.strip()
                    if text == '금리':  # 완전 일치만
                        self.logger.info(f"        strong에서 금리 완전 일치 발견")
                        return True
                except:
                    continue
            
            # 방법 2: th 태그에서 '금리' 완전 일치만 찾기
            th_elements = self.driver.find_elements(By.TAG_NAME, 'th')
            for th in th_elements:
                try:
                    text = th.text.strip()
                    if text == '금리':  # 완전 일치만
                        self.logger.info(f"        th에서 금리 완전 일치 발견")
                        return True
                except:
                    continue
            
            # 방법 3: dt 태그에서 '금리' 완전 일치만 찾기
            dt_elements = self.driver.find_elements(By.TAG_NAME, 'dt')
            for dt in dt_elements:
                try:
                    text = dt.text.strip()
                    if text == '금리':  # 완전 일치만
                        self.logger.info(f"        dt에서 금리 완전 일치 발견")
                        return True
                except:
                    continue
            
            self.logger.info("        금리 완전 일치 항목을 찾을 수 없음")
            return False
            
        except Exception as e:
            self.logger.info(f"        오류: 금리 항목 확인 실패: {e}")
            return False
    
    # '금리' 항목 근처의 자세히보기 버튼을 적극적으로 찾아서 클릭
    def find_and_click_detail_button_aggressive(self):
        try:
            self.logger.info("        자세히보기 버튼 적극적 검색 중...")
            
            # 전략 1: '금리'가 포함된 요소 근처에서 자세히보기 버튼 찾기
            detail_button = self.find_detail_button_near_interest_text()
            if detail_button:
                return self.click_detail_button_safe(detail_button)
            
            # 전략 2: 모든 자세히보기 버튼 중에서 금리 관련된 것 찾기
            detail_button = self.find_any_detail_button_on_page()
            if detail_button:
                return self.click_detail_button_safe(detail_button)
            
            return False
            
        except Exception as e:
            self.logger.info(f"        오류: 자세히보기 버튼 찾기 실패: {e}")
            return False
    
    # '금리' 완전 일치 텍스트 근처의 자세히보기 버튼 찾기
    def find_detail_button_near_interest_text(self):
        try:
            self.logger.info("        금리 완전 일치 요소 근처에서 자세히보기 버튼 검색...")
            
            # '금리'와 완전 일치하는 요소만 찾기
            all_elements = self.driver.find_elements(By.XPATH, "//*")
            
            for element in all_elements:
                try:
                    element_text = element.text.strip()
                    if element_text == '금리':  # 완전 일치만
                        self.logger.info(f"        금리 완전 일치 요소 발견")
                        
                        # 1. 같은 요소 내에서 버튼 찾기
                        button = self.find_detail_button_in_element_improved(element)
                        if button:
                            self.logger.info(f"        같은 요소 내에서 자세히보기 버튼 발견")
                            return button
                        
                        # 2. 부모 요소에서 버튼 찾기
                        try:
                            parent = element.find_element(By.XPATH, "..")
                            button = self.find_detail_button_in_element_improved(parent)
                            if button:
                                self.logger.info(f"        부모 요소에서 자세히보기 버튼 발견")
                                return button
                        except:
                            pass
                        
                        # 3. 조상 요소들에서 버튼 찾기 (최대 3단계)
                        try:
                            for i in range(1, 4):
                                ancestor = element.find_element(By.XPATH, f"./ancestor::*[{i}]")
                                button = self.find_detail_button_in_element_improved(ancestor)
                                if button:
                                    self.logger.info(f"        조상({i}단계) 요소에서 자세히보기 버튼 발견")
                                    return button
                        except:
                            pass
                            
                except Exception:
                    continue
            
            self.logger.info("        금리 완전 일치 요소 근처에서 자세히보기 버튼을 찾을 수 없음")
            return None
            
        except Exception as e:
            self.logger.info(f"        오류: 금리 텍스트 근처 버튼 찾기 실패: {e}")
            return None
        
# 페이지의 모든 자세히보기 버튼 찾기
    def find_any_detail_button_on_page(self):
        try:
            self.logger.info("        페이지 전체에서 자세히보기 버튼 검색...")
            
            # 자세히보기 관련 텍스트 패턴
            detail_patterns = ['자세히보기', '상세보기', '자세히 보기', '상세 보기', '자세히', '상세']
            
            # 1. 텍스트로 버튼 찾기
            for pattern in detail_patterns:
                try:
                    buttons = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{pattern}')]")
                    for button in buttons:
                        if button.tag_name in ['a', 'button'] or button.get_attribute('onclick'):
                            self.logger.info(f"        자세히보기 버튼 발견")
                            return button
                except:
                    continue
            
            # 2. onclick 속성으로 버튼 찾기
            try:
                onclick_buttons = self.driver.find_elements(By.XPATH, "//*[@onclick]")
                for button in onclick_buttons:
                    onclick = button.get_attribute('onclick') or ''
                    button_text = button.text.strip()
                    
                    if ('자세히' in onclick or 'detail' in onclick.lower() or 
                        'popup' in onclick.lower() or '자세히' in button_text):
                        self.logger.info(f"        onclick 자세히보기 버튼 발견")
                        return button
            except:
                pass
            
            return None
            
        except Exception as e:
            self.logger.info(f"        오류: 전체 페이지 버튼 찾기 실패: {e}")
            return None
    
    # 특정 요소 내에서 자세히보기 버튼 찾기 (개선된 버전)
    def find_detail_button_in_element_improved(self, element):
        try:
            # 자세히보기 관련 정확한 텍스트 패턴
            detail_patterns = ['자세히보기', '상세보기', '자세히 보기', '상세 보기', '자세히', '상세']
            
            # a 태그와 button 태그 우선 검색
            for tag in ['a', 'button']:
                buttons = element.find_elements(By.TAG_NAME, tag)
                for button in buttons:
                    try:
                        button_text = button.text.strip()
                        onclick = button.get_attribute('onclick') or ''
                        title = button.get_attribute('title') or ''
                        
                        # 텍스트 매칭
                        if any(pattern in button_text for pattern in detail_patterns):
                            return button
                        
                        # title 속성 매칭
                        if any(pattern in title for pattern in detail_patterns):
                            return button
                        
                        # onclick 속성 매칭
                        if ('자세히' in onclick or 'detail' in onclick.lower()):
                            return button
                            
                    except:
                        continue
            
            # onclick 속성이 있는 모든 요소 검색
            onclick_elements = element.find_elements(By.XPATH, ".//*[@onclick]")
            for elem in onclick_elements:
                try:
                    onclick = elem.get_attribute('onclick') or ''
                    elem_text = elem.text.strip()
                    
                    if ('자세히' in onclick or 'detail' in onclick.lower() or 
                        any(pattern in elem_text for pattern in detail_patterns)):
                        return elem
                except:
                    continue
            
            return None
            
        except Exception:
            return None
    
    # 자세히보기 버튼 안전하게 클릭 (알럿 처리 포함)
    def click_detail_button_safe(self, button):
        try:
            # 클릭하기 전에 버튼 정보 확인
            button_text = button.text.strip()
            onclick = button.get_attribute('onclick') or ''
            
            self.logger.info(f"        버튼 클릭 시도")
            
            # 클릭 실행
            try:
                button.click()
            except:
                self.driver.execute_script("arguments[0].click();", button)
            
            # 짧은 대기 후 알럿 확인
            time.sleep(1)
            
            # 알럿이 있는지 확인하고 처리
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                self.logger.info(f"        오류: 알럿 발생: '{alert_text}'")
                alert.dismiss()  # 알럿 닫기
                self.logger.info("        알럿으로 인해 버튼 클릭 실패")
                return False
            except:
                # 알럿이 없으면 정상
                pass
            
            self.logger.info("        자세히보기 버튼 클릭 성공")
            return True
            
        except Exception as e:
            self.logger.info(f"        오류: 버튼 클릭 실패: {e}")
            
            # 혹시 알럿이 남아있다면 처리
            try:
                alert = self.driver.switch_to.alert
                alert.dismiss()
            except:
                pass
            
            return False
    
    # 기존 팝업 방식 처리 - 디버깅 정보 추가
    def handle_interest_rate_popup(self):
        info = {}
        original_window = self.driver.current_window_handle
        
        try:
            self.logger.info("        팝업방식 사용: 금리 팝업창 처리")
            time.sleep(5)  # 팝업 로딩 대기
            
            # 먼저 알럿이 있는지 확인
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                self.logger.info(f"        오류: 예상치 못한 알럿 발생: '{alert_text}'")
                alert.dismiss()
                self.logger.info("        알럿으로 인해 팝업 처리 불가")
                return info
            except:
                # 알럿이 없으면 정상 진행
                pass
            
            # 팝업창으로 전환
            windows = self.driver.window_handles
            
            if len(windows) > 1:
                # 새 창으로 전환
                for window in windows:
                    if window != original_window:
                        self.driver.switch_to.window(window)
                        break
                
                self.logger.info("        팝업창으로 전환 성공")
                time.sleep(3)
                
                # 기본이율 및 우대이율 데이터 추출
                basic_rate_info = self.extract_basic_rate_data()
                preferential_rate_info = self.extract_preferential_rate_data()
                
                # 디버깅 정보 추가
                if basic_rate_info.get('기본이율'):
                    basic_rate_info['기본이율']['method'] = '팝업방식'
                
                info.update(basic_rate_info)
                info.update(preferential_rate_info)
                
                self.logger.info(f"        팝업방식 처리 완료: {list(info.keys())}")
                
                # 원래 창으로 복귀
                self.driver.close()
                self.driver.switch_to.window(original_window)
            else:
                self.logger.info("        오류: 팝업창이 열리지 않음")
        
        except Exception as e:
            self.logger.info(f"        오류: 팝업 처리 실패: {e}")
            try:
                # 알럿 처리
                try:
                    alert = self.driver.switch_to.alert
                    alert.dismiss()
                    self.logger.info("        알럿 처리 완료")
                except:
                    pass
                
                # 창 정리
                windows = self.driver.window_handles
                if len(windows) > 1:
                    self.driver.close()
                self.driver.switch_to.window(original_window)
            except:
                pass
        
        return info
    
    # 대안 방식: '계약기간 중 금리' 완전 일치로 테이블 추출
    def extract_interest_rate_tables_alternative(self):
        info = {}
        
        try:
            self.logger.info("        대안 방식: 계약기간 중 금리 완전 일치 테이블 검색...")
            
            # 정확한 텍스트 매칭 (완전 일치만)
            target_text = '계약기간 중 금리'
            
            # 1단계: li > strong 구조에서 완전 일치 텍스트 찾기
            list_items = self.driver.find_elements(By.TAG_NAME, 'li')
            
            for li in list_items:
                try:
                    strong_elements = li.find_elements(By.TAG_NAME, 'strong')
                    
                    for strong in strong_elements:
                        strong_text = strong.text.strip()
                        
                        # 완전 일치 텍스트 매칭
                        if strong_text == target_text:
                            self.logger.info(f"        완전 일치 항목 발견: '{strong_text}'")
                            self.logger.info("        대안 방식 사용: 테이블 직접 크롤링")
                            
                            # 2단계: 해당 항목 주변에서 테이블 찾기
                            tables = self.find_tables_in_scope_precise(li, strong)
                            
                            if tables:
                                self.logger.info(f"        {len(tables)}개 테이블 발견")
                                
                                # 모든 테이블을 기본이율로 분류 (계약기간 중 금리는 기본이율)
                                for j, table in enumerate(tables):
                                    table_data = self.extract_table_data_comprehensive(table)
                                    if table_data and len(table_data) > 0:
                                        info['기본이율'] = {
                                            'type': 'table',
                                            'data': table_data,
                                            'source': strong_text,
                                            'method': '대안방식'  # 디버깅용
                                        }
                                        self.logger.info(f"        대안방식 테이블 추출 완료: {len(table_data)}행")
                                        break  # 첫 번째 테이블만 사용
                                
                                # 정확한 매칭을 찾았으므로 더 이상 검색하지 않음
                                self.logger.info(f"        '{target_text}' 항목 처리 완료")
                                return info
                            else:
                                self.logger.info(f"        오류: '{strong_text}' 주변에 테이블 없음")
                except Exception:
                    continue
            
            self.logger.info(f"        오류: '{target_text}' 완전 일치 항목을 찾을 수 없음")
            
        except Exception as e:
            self.logger.info(f"        오류: 대안 방식 실패: {e}")
        
        return info
    
    # 특정 li와 strong 요소 주변에서 테이블을 정확하게 찾기
    def find_tables_in_scope_precise(self, li, strong):
        tables = []
        found_tables = set()
        
        try:
            self.logger.info("        테이블 검색 중...")
            
            # 방법 1: 같은 li 요소 내의 테이블
            try:
                li_tables = li.find_elements(By.TAG_NAME, 'table')
                for table in li_tables:
                    if table.is_displayed() and id(table) not in found_tables:
                        tables.append(table)
                        found_tables.add(id(table))
                        self.logger.info("        방법1: li 내부에서 테이블 발견")
            except Exception:
                pass
            
            # 방법 2: li의 부모 요소들에서 테이블 찾기 (3단계까지만)
            try:
                parent = li.find_element(By.XPATH, "..")
                depth = 0
                max_depth = 3
                
                while parent and depth < max_depth:
                    try:
                        parent_tables = parent.find_elements(By.TAG_NAME, 'table')
                        for table in parent_tables:
                            if table.is_displayed() and id(table) not in found_tables:
                                tables.append(table)
                                found_tables.add(id(table))
                                self.logger.info(f"        방법2: 부모({depth+1}단계)에서 테이블 발견")
                        
                        parent = parent.find_element(By.XPATH, "..")
                        depth += 1
                    except Exception:
                        break
            except Exception:
                pass
            
            # 방법 3: li 다음 형제 요소들에서 테이블 찾기 (5개까지만)
            try:
                script = """
                    var li = arguments[0];
                    var tables = [];
                    var sibling = li.nextElementSibling;
                    var count = 0;
                    
                    while (sibling && count < 5) {
                        if (sibling.tagName === 'TABLE') {
                            tables.push(sibling);
                        }
                        var siblingTables = sibling.querySelectorAll('table');
                        for (var i = 0; i < siblingTables.length; i++) {
                            tables.push(siblingTables[i]);
                        }
                        sibling = sibling.nextElementSibling;
                        count++;
                    }
                    
                    return tables;
                """
                
                sibling_tables = self.driver.execute_script(script, li)
                for table in sibling_tables:
                    if id(table) not in found_tables:
                        tables.append(table)
                        found_tables.add(id(table))
                        self.logger.info("        방법3: 형제 요소에서 테이블 발견")
            except Exception:
                pass
            
            # 방법 4: strong의 부모 요소들에서 테이블 찾기
            try:
                strong_parent = strong.find_element(By.XPATH, "..")
                strong_parent_tables = strong_parent.find_elements(By.TAG_NAME, 'table')
                for table in strong_parent_tables:
                    if table.is_displayed() and id(table) not in found_tables:
                        tables.append(table)
                        found_tables.add(id(table))
                        self.logger.info("        방법4: strong 부모에서 테이블 발견")
            except Exception:
                pass
            
            self.logger.info(f"        총 {len(tables)}개 테이블 발견")
            return tables
            
        except Exception as e:
            self.logger.info(f"        오류: 테이블 검색 실패: {e}")
            return []
    
    # 테이블 데이터 종합 추출 - 개선된 버전
    def extract_table_data_comprehensive(self, table):
        try:
            rows = table.find_elements(By.TAG_NAME, 'tr')
            table_data = []
            
            if not rows:
                return []
            
            for row in rows:
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                    if cells:
                        row_data = []
                        for cell in cells:
                            cell_text = cell.text.strip()
                            # 빈 셀도 포함하되 공백으로 처리
                            row_data.append(cell_text if cell_text else '')
                        
                        # 모든 셀이 빈 값이 아닌 경우에만 추가
                        if any(cell for cell in row_data):
                            table_data.append(row_data)
                except Exception:
                    continue
            
            self.logger.info(f"        테이블 데이터 추출: {len(table_data)}행")
            if table_data:
                self.logger.info(f"        첫 번째 행: {table_data[0]}")
            
            return table_data
            
        except Exception as e:
            self.logger.info(f"        오류: 테이블 데이터 추출 실패: {e}")
            return []
    
    # 금리 및 이율 탭으로 이동
    def go_to_interest_rate_tab(self):
        try:
            tab_selectors = [
                "//a[contains(text(), '금리 및 이율')]",
                "//a[contains(text(), '금리')]",
                "//li[contains(text(), '금리 및 이율')]//a",
                "//li[contains(text(), '금리')]//a", 
                "//button[contains(text(), '금리 및 이율')]",
                "//button[contains(text(), '금리')]",
                "//span[contains(text(), '금리 및 이율')]",
                "//span[contains(text(), '금리')]",
                "//div[contains(text(), '금리 및 이율')]",
                "//div[contains(text(), '금리')]"
            ]
            
            for selector in tab_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            try:
                                element.click()
                                self.logger.info("        금리 및 이율 탭 클릭 완료")
                                return True
                            except:
                                self.driver.execute_script("arguments[0].click();", element)
                                self.logger.info("        금리 및 이율 탭 클릭 완료 (JS)")
                                return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.info(f"        오류: 금리 탭 이동 실패: {e}")
            return False
        
# 기본이율 데이터 추출 - 지수연동예금 지원 강화
    def extract_basic_rate_data(self):
        info = {}
        
        try:
            self.logger.info("        기본이율 데이터 추출 중...")
            
            # 1단계: 일반적인 기본이율 테이블 찾기 (기존 방식)
            tables = self.driver.find_elements(By.TAG_NAME, 'table')
            
            for table in tables:
                try:
                    if not table.is_displayed():
                        continue
                    
                    table_text = table.text
                    rows = table.find_elements(By.TAG_NAME, 'tr')
                    
                    # 기본이율 테이블 식별: 기간, 이율 정보가 있는 테이블
                    if (len(rows) > 1 and 
                        ('기간' in table_text or '개월' in table_text) and 
                        ('이율' in table_text or '금리' in table_text) and
                        any(char.isdigit() for char in table_text)):
                        
                        self.logger.info("        일반 기본이율 테이블 발견")
                        
                        table_data = []
                        for row in rows:
                            cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                            if cells:
                                row_data = [cell.text.strip() for cell in cells]
                                if any(cell for cell in row_data):
                                    table_data.append(row_data)
                        
                        info['기본이율'] = {
                            'type': 'table',
                            'data': table_data
                        }
                        
                        self.logger.info(f"        일반 기본이율 테이블: {len(table_data)}행 추출")
                        return info
                        
                except Exception as e:
                    continue
            
            # 2단계: 지수연동예금 특화 방식 - 모든 테이블 검사
            self.logger.info("        지수연동예금 방식으로 테이블 재검색...")
            
            for table in tables:
                try:
                    if not table.is_displayed():
                        continue
                    
                    table_text = table.text
                    rows = table.find_elements(By.TAG_NAME, 'tr')
                    
                    # 지수연동예금 조건: 금리나 %가 포함되고, 행이 있는 테이블
                    if (len(rows) > 0 and 
                        ('금리' in table_text or '%' in table_text or '이율' in table_text) and
                        len(table_text.strip()) > 10):
                        
                        self.logger.info(f"        지수연동예금 테이블 발견")
                        
                        table_data = []
                        for row in rows:
                            cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                            if cells:
                                row_data = [cell.text.strip() for cell in cells]
                                if any(cell for cell in row_data):
                                    table_data.append(row_data)
                        
                        if table_data:
                            info['기본이율'] = {
                                'type': 'table',
                                'data': table_data,
                                'source': '지수연동예금'
                            }
                            
                            self.logger.info(f"        지수연동예금 테이블: {len(table_data)}행 추출")
                            return info
                        
                except Exception as e:
                    continue
            
            # 3단계: 테이블이 없으면 텍스트 방식으로 정보 추출
            self.logger.info("        테이블 없음 - 텍스트 방식으로 금리 정보 추출...")
            
            # 금리 관련 텍스트 수집
            rate_texts = self.extract_rate_texts_from_popup()
            
            if rate_texts:
                info['기본이율'] = {
                    'type': 'text',
                    'data': rate_texts,
                    'source': '텍스트추출'
                }
                self.logger.info(f"        텍스트 방식으로 {len(rate_texts)}개 금리 정보 추출")
                return info
            
            self.logger.info("        오류: 기본이율 정보를 찾을 수 없음")
            
        except Exception as e:
            self.logger.info(f"        오류: 기본이율 추출 실패: {e}")
        
        return info
    
    # 팝업창에서 금리 관련 텍스트 정보 추출
    def extract_rate_texts_from_popup(self):
        rate_texts = []
        
        try:
            # 방법 1: 모든 텍스트에서 %가 포함된 라인 추출
            body_text = self.driver.find_element(By.TAG_NAME, 'body').text
            lines = body_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if (len(line) > 5 and len(line) < 200 and 
                    '%' in line and 
                    ('금리' in line or '이율' in line or any(char.isdigit() for char in line))):
                    
                    rate_texts.append(line)
            
            # 방법 2: 특정 요소들에서 금리 정보 추출
            selectors = ['div', 'span', 'p', 'td', 'th', 'li']
            
            for selector in selectors:
                elements = self.driver.find_elements(By.TAG_NAME, selector)
                for element in elements:
                    try:
                        if not element.is_displayed():
                            continue
                        
                        text = element.text.strip()
                        
                        # 금리 정보 조건
                        if (len(text) > 5 and len(text) < 100 and
                            '%' in text and
                            ('금리' in text or '이율' in text or 
                             '연' in text or '기간' in text) and
                            any(char.isdigit() for char in text)):
                            
                            # 중복 제거
                            if text not in rate_texts:
                                rate_texts.append(text)
                                
                    except Exception:
                        continue
            
            # 중복 제거 및 정리
            unique_rates = []
            for rate in rate_texts:
                # 너무 짧거나 의미없는 텍스트 제외
                if (len(rate) > 10 and 
                    not any(existing in rate or rate in existing for existing in unique_rates)):
                    unique_rates.append(rate)
            
            return unique_rates[:10]  # 최대 10개까지만
            
        except Exception as e:
            self.logger.info(f"        오류: 텍스트 추출 실패: {e}")
            return []
    
    # 우대이율 데이터 추출
    def extract_preferential_rate_data(self):
        info = {}
        
        try:
            self.logger.info("        우대이율 데이터 추출 중...")
            
            # 우대이율 탭 찾기 및 클릭
            preferential_tab = self.find_preferential_rate_tab()
            
            if preferential_tab:
                self.logger.info("        우대이율 탭 클릭")
                
                # 탭 클릭 전 현재 내용 기록
                before_content = self.driver.execute_script("return document.body.innerText;")
                
                preferential_tab.click()
                time.sleep(3)
                
                # 탭 클릭 후 내용
                after_content = self.driver.execute_script("return document.body.innerText;")
                
                # 우대이율 데이터 추출
                preferential_data = self.extract_preferential_data_clean(before_content, after_content)
                
                if preferential_data:
                    info['우대이율'] = preferential_data
                    self.logger.info(f"        우대이율 데이터: {preferential_data['type']} 형태")
            else:
                self.logger.info("        오류: 우대이율 탭을 찾을 수 없음")
            
        except Exception as e:
            self.logger.info(f"        오류: 우대이율 추출 실패: {e}")
        
        return info
    
    # 우대이율 탭 찾기
    def find_preferential_rate_tab(self):
        try:
            elements_with_onclick = self.driver.find_elements(By.XPATH, "//*[@onclick]")
            
            for element in elements_with_onclick:
                text = element.text.strip()
                if text == '우대이율':
                    return element
            
            return None
            
        except Exception as e:
            return None
    
    # 우대이율 데이터 정제 추출
    def extract_preferential_data_clean(self, before_content, after_content):
        result = {
            'type': None,
            'data': None,
            'tableData': [],
            'textData': []
        }
        
        try:
            # 1. 우대이율 테이블 확인
            tables = self.driver.find_elements(By.TAG_NAME, 'table')
            
            for table in tables:
                try:
                    if not table.is_displayed():
                        continue
                    
                    table_text = table.text
                    rows = table.find_elements(By.TAG_NAME, 'tr')
                    
                    # 우대이율 테이블 조건
                    is_preferential_table = (
                        len(rows) > 0 and len(rows) <= 20 and
                        (('우대' in table_text or '가산' in table_text or '추가' in table_text) or
                         ('기간' not in table_text and '개월' not in table_text and 
                          ('%' in table_text or any(char.isdigit() for char in table_text))) or
                         (len(rows) <= 10 and ('조건' in table_text or '대상' in table_text)))
                    )
                    
                    if is_preferential_table:
                        self.logger.info("        우대이율 테이블 발견")
                        
                        for row in rows:
                            cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                            if cells:
                                row_data = [cell.text.strip() for cell in cells]
                                if any(cell for cell in row_data):
                                    result['tableData'].append(row_data)
                        break
                        
                except:
                    continue
            
            # 2. 텍스트 데이터 추출 (테이블이 없는 경우에만)
            if not result['tableData']:
                self.logger.info("        우대이율 텍스트 추출 중...")
                
                # 탭 전환 전후 비교
                before_lines = set(line.strip() for line in before_content.split('\n'))
                after_lines = [line.strip() for line in after_content.split('\n')]
                
                # 새로 나타난 라인들 중 우대이율 관련 내용만 추출
                new_lines = [line for line in after_lines if line not in before_lines]
                
                for line in new_lines:
                    if (len(line) > 3 and 
                        ('우대' in line or '가산' in line or '추가' in line or 
                         '금리' in line or '이율' in line or '%' in line or
                         '조건' in line or '대상' in line or '적용' in line)):
                        
                        result['textData'].append(line)
                
                # 추가 텍스트 추출 (텍스트가 적으면)
                if len(result['textData']) < 3:
                    text_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div, p, span, li')
                    for element in text_elements:
                        try:
                            text = element.text.strip()
                            if (text and len(text) > 5 and len(text) < 500 and 
                                element.is_displayed() and
                                len(element.find_elements(By.XPATH, "./*")) == 0 and  # leaf node
                                ('우대' in text or '가산' in text or '추가' in text or 
                                 any(char.isdigit() and '%' in text for char in text))):
                                
                                # 중복 제거
                                if not any(existing in text or text in existing for existing in result['textData']):
                                    result['textData'].append(text)
                        except:
                            continue
            
            # 3. 결과 정리 및 타입 결정
            result['textData'] = [line for line in result['textData'] 
                                if (len(line) >= 3 and len(line) <= 500 and
                                    not any(keyword in line for keyword in 
                                          ['조회일 기준', '세금공제', '단위: 연%', 'KB국민은행', 
                                           '전체상품', '인터넷뱅킹']))]
            
            # 타입 결정
            if result['tableData']:
                result['type'] = 'table'
                result['data'] = result['tableData']
                self.logger.info(f"        우대이율 테이블: {len(result['tableData'])}행")
            elif result['textData']:
                result['type'] = 'text'
                result['data'] = result['textData']
                self.logger.info(f"        우대이율 텍스트: {len(result['textData'])}개")
            else:
                result['type'] = 'none'
                result['data'] = None
                self.logger.info("        오류: 우대이율 데이터 없음")
            
        except Exception as e:
            self.logger.info(f"        오류: 우대이율 데이터 추출 오류: {e}")
        
        return result
    
    # 상품안내 탭에서 개선된 정보 추출
    def extract_product_guide_info_improved(self):
        info = {}
        
        try:
            self.logger.info("        상품안내 탭 정보 추출 중...")
            
            # 상품안내 탭이 활성화되어 있는지 확인 및 클릭
            self.ensure_product_guide_tab_active()
            
            # 다양한 키워드 패턴으로 확장
            target_keywords = [
                {
                    'patterns': ['가입금액', '예치금액', '저축금액', '납입금액', '최소금액', '최저금액', '예금금액'], 
                    'key': '저축금액'
                },
                {
                    'patterns': ['가입대상', '대상', '가입조건', '자격요건'], 
                    'key': '가입대상'
                },
                {
                    'patterns': ['계약기간', '예치기간', '만기', '기간', '저축기간'], 
                    'key': '계약기간'
                }
            ]
            
            # 여러 방법으로 정보 추출 시도
            for keyword_obj in target_keywords:
                if keyword_obj['key'] in info:
                    continue
                    
                # 방법 1: li > strong 구조
                found_content = self.extract_by_li_strong_structure(keyword_obj)
                if found_content:
                    info[keyword_obj['key']] = found_content
                    continue
                
                # 방법 2: 테이블 구조
                found_content = self.extract_by_table_structure(keyword_obj)
                if found_content:
                    info[keyword_obj['key']] = found_content
                    continue
                
                # 방법 3: div/span 구조
                found_content = self.extract_by_div_span_structure(keyword_obj)
                if found_content:
                    info[keyword_obj['key']] = found_content
                    continue
                
                # 방법 4: 전체 텍스트에서 패턴 매칭
                found_content = self.extract_by_text_pattern(keyword_obj)
                if found_content:
                    info[keyword_obj['key']] = found_content
                    continue
            
            self.logger.info(f"        상품안내 탭 추출 완료: {list(info.keys())}")
            
        except Exception as e:
            self.logger.info(f"        오류: 상품안내 탭 추출 실패: {e}")
        
        return info
    
    # 상품안내 탭이 활성화되어 있는지 확인 및 클릭
    def ensure_product_guide_tab_active(self):
        try:
            # 상품안내 탭 클릭 시도
            tab_selectors = [
                "//a[contains(text(), '상품안내')]",
                "//li[contains(text(), '상품안내')]//a",
                "//button[contains(text(), '상품안내')]",
                "//span[contains(text(), '상품안내')]"
            ]
            
            for selector in tab_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            time.sleep(2)
                            self.logger.info("        상품안내 탭 클릭 완료")
                            return True
                except:
                    continue
            
            # 이미 상품안내 탭이 활성화되어 있을 수 있음
            self.logger.info("        상품안내 탭 버튼 없음 (이미 활성화된 것으로 추정)")
            return True
            
        except Exception as e:
            self.logger.info(f"        오류: 상품안내 탭 활성화 실패: {e}")
            return False
    
    # li > strong 구조로 정보 추출
    def extract_by_li_strong_structure(self, keyword_obj):
        try:
            list_items = self.driver.find_elements(By.TAG_NAME, 'li')
            
            for li in list_items:
                try:
                    strong_elements = li.find_elements(By.TAG_NAME, 'strong')
                    
                    for strong in strong_elements:
                        strong_text = strong.text.strip().replace(' ', '')
                        
                        # 키워드 매칭 확인
                        for pattern in keyword_obj['patterns']:
                            if pattern in strong_text:
                                self.logger.info(f"        li>strong에서 {keyword_obj['key']} 발견: {strong_text}")
                                
                                # 여러 방법으로 내용 추출
                                content = self.extract_content_from_strong(strong, li)
                                if content:
                                    return content
                                break
                except:
                    continue
        except:
            pass
        return None
    
    # 테이블 구조로 정보 추출
    def extract_by_table_structure(self, keyword_obj):
        try:
            # th/td 구조 확인
            th_elements = self.driver.find_elements(By.TAG_NAME, 'th')
            for th in th_elements:
                th_text = th.text.strip()
                for pattern in keyword_obj['patterns']:
                    if pattern in th_text:
                        self.logger.info(f"        테이블에서 {keyword_obj['key']} 발견: {th_text}")
                        
                        # 같은 행의 td 찾기
                        try:
                            parent_tr = th.find_element(By.XPATH, "./ancestor::tr[1]")
                            td_elements = parent_tr.find_elements(By.TAG_NAME, 'td')
                            for td in td_elements:
                                content = td.text.strip()
                                if content and len(content) > 2:
                                    return content
                        except:
                            pass
                        
                        # 다음 형제 요소 찾기
                        try:
                            next_sibling = th.find_element(By.XPATH, "./following-sibling::td[1]")
                            content = next_sibling.text.strip()
                            if content:
                                return content
                        except:
                            pass
                        break
        except:
            pass
        return None
    
    # div/span 구조로 정보 추출
    def extract_by_div_span_structure(self, keyword_obj):
        try:
            # div, span 등에서 키워드 포함 요소 찾기
            for tag in ['div', 'span', 'p', 'dt', 'dd']:
                elements = self.driver.find_elements(By.TAG_NAME, tag)
                for element in elements:
                    try:
                        element_text = element.text.strip()
                        for pattern in keyword_obj['patterns']:
                            if pattern in element_text:
                                self.logger.info(f"        {tag}에서 {keyword_obj['key']} 발견: {element_text[:30]}...")
                                
                                # 같은 요소 내에서 키워드 이후 텍스트 추출
                                if len(element_text) > len(pattern) + 5:
                                    content = element_text.replace(pattern, '', 1).strip()
                                    content = content.lstrip(':-').strip()
                                    if content:
                                        return content
                                
                                # 다음 형제 요소에서 찾기
                                try:
                                    next_element = element.find_element(By.XPATH, "./following-sibling::*[1]")
                                    content = next_element.text.strip()
                                    if content:
                                        return content
                                except:
                                    pass
                                break
                    except:
                        continue
        except:
            pass
        return None
    
    # 전체 텍스트에서 패턴 매칭으로 정보 추출
    def extract_by_text_pattern(self, keyword_obj):
        try:
            # 페이지 전체 텍스트 가져오기
            body_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            for pattern in keyword_obj['patterns']:
                if pattern in body_text:
                    self.logger.info(f"        텍스트 패턴에서 {keyword_obj['key']} 발견")
                    
                    # 패턴 이후 텍스트 추출
                    lines = body_text.split('\n')
                    for i, line in enumerate(lines):
                        if pattern in line:
                            # 같은 줄에서 추출
                            if len(line) > len(pattern) + 5:
                                content = line.replace(pattern, '', 1).strip()
                                content = content.lstrip(':-').strip()
                                if content and len(content) > 2:
                                    return content
                            
                            # 다음 줄에서 추출
                            if i + 1 < len(lines):
                                next_line = lines[i + 1].strip()
                                if next_line and len(next_line) > 2:
                                    return next_line
                            break
        except:
            pass
        return None
    
    # strong 요소에서 내용 추출하는 여러 방법
    def extract_content_from_strong(self, strong, li):
        # 방법 1: JavaScript로 형제 노드 추출
        try:
            script = """
            var strong = arguments[0];
            var content = [];
            var currentNode = strong.nextSibling;
            
            while (currentNode && currentNode.parentElement === strong.parentElement) {
                if (currentNode.nodeType === Node.TEXT_NODE) {
                    var text = currentNode.textContent.trim();
                    if (text.length > 0) {
                        content.push(text);
                    }
                } else if (currentNode.nodeType === Node.ELEMENT_NODE) {
                    var text = currentNode.textContent.trim();
                    if (text.length > 0) {
                        content.push(text);
                    }
                }
                currentNode = currentNode.nextSibling;
            }
            
            return content.join(' ').trim();
            """
            
            sibling_content = self.driver.execute_script(script, strong)
            if sibling_content and len(sibling_content.strip()) > 3:
                return sibling_content.strip()
        except:
            pass
        
        # 방법 2: li 전체에서 strong 제외
        try:
            li_full_text = li.text.strip()
            strong_full_text = strong.text.strip()
            
            if len(li_full_text) > len(strong_full_text):
                remaining_text = li_full_text.replace(strong_full_text, '', 1).strip()
                clean_text = remaining_text.lstrip(':-').strip()
                
                if clean_text and len(clean_text) > 3:
                    return clean_text
        except:
            pass
        
        # 방법 3: strong 다음 요소들 찾기
        try:
            next_elements = strong.find_elements(By.XPATH, "./following-sibling::*")
            for elem in next_elements:
                elem_text = elem.text.strip()
                if elem_text and len(elem_text) > 3:
                    return elem_text
        except:
            pass
        
        return None
    
    # 유의사항 탭에서 개선된 정보 추출
    def extract_notice_info_improved(self):
        info = {}
        
        try:
            self.logger.info("        유의사항 탭으로 이동 중...")
            
            # 유의사항 탭 클릭
            tab_clicked = self.click_notice_tab()
            
            if not tab_clicked:
                self.logger.info("        오류: 유의사항 탭을 찾을 수 없음")
                return info
            
            time.sleep(4)  # 탭 로딩 대기 시간 증가
            
            # 다양한 키워드 패턴으로 확장
            target_keywords = [
                {
                    'patterns': ['거래방법', '가입방법', '취급방법', '이용방법'], 
                    'key': '거래방법'
                },
                {
                    'patterns': ['세제혜택', '과세', '비과세', '세금', '세제'], 
                    'key': '세제혜택'
                }
            ]
            
            # 여러 방법으로 정보 추출 시도
            for keyword_obj in target_keywords:
                if keyword_obj['key'] in info:
                    continue
                    
                # 방법 1: li > strong 구조
                found_content = self.extract_by_li_strong_structure(keyword_obj)
                if found_content:
                    info[keyword_obj['key']] = found_content
                    continue
                
                # 방법 2: 테이블 구조
                found_content = self.extract_by_table_structure(keyword_obj)
                if found_content:
                    info[keyword_obj['key']] = found_content
                    continue
                
                # 방법 3: div/span 구조
                found_content = self.extract_by_div_span_structure(keyword_obj)
                if found_content:
                    info[keyword_obj['key']] = found_content
                    continue
                
                # 방법 4: 전체 텍스트에서 패턴 매칭
                found_content = self.extract_by_text_pattern(keyword_obj)
                if found_content:
                    info[keyword_obj['key']] = found_content
                    continue
            
            self.logger.info(f"        유의사항 탭 추출 완료: {list(info.keys())}")
            
        except Exception as e:
            self.logger.info(f"        오류: 유의사항 탭 추출 실패: {e}")
        
        return info
    
    # 유의사항 탭 클릭
    def click_notice_tab(self):
        try:
            tab_selectors = [
                "//a[contains(text(), '유의사항')]",
                "//a[contains(text(), '주의사항')]",
                "//li[contains(text(), '유의사항')]//a",
                "//button[contains(text(), '유의사항')]",
                "//span[contains(text(), '유의사항')]",
                "//div[contains(text(), '유의사항')]"
            ]
            
            for selector in tab_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            try:
                                element.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", element)
                            self.logger.info("        유의사항 탭 클릭 완료")
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.info(f"        오류: 유의사항 탭 클릭 실패: {e}")
            return False
    
    # 적금 탭으로 이동
    def click_savings_tab(self):
        try:
            self.logger.info("적금 탭으로 전환...")
            
            # 직접 적금 URL로 이동
            self.driver.get(self.savings_url)
            time.sleep(5)
            
            # 적금 키워드 확인
            body_text = self.driver.find_element(By.TAG_NAME, 'body').text
            if any(keyword in body_text for keyword in ['KB내맘대로적금', '청년도약계좌', '직장인우대적금']):
                self.logger.info("    적금 페이지 확인됨")
                return True
            
            # 버튼 클릭 방식 시도
            selectors = [
                "//a[contains(text(), '적금')]",
                "//li[contains(text(), '적금')]//a"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            time.sleep(5)
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.info(f"오류: 적금 탭 전환 실패: {e}")
            return False
    
    # 모든 상품 수집 - 알럿 처리 강화
    def collect_all_products(self):
        try:
            self.logger.info("전체 상품 수집 시작")
            
            # 예금 상품 수집
            self.logger.info("예금 상품 수집 중...")
            self.driver.get(self.base_url)
            time.sleep(5)
            
            deposit_products = self.get_products_from_page('예금')
            
            if deposit_products:
                self.logger.info(f"예금 상품 상세정보 수집...")
                for i, product in enumerate(deposit_products):
                    self.logger.info(f"[{i+1}/{len(deposit_products)}] {product['name']} (예금) 처리 중...")
                    
                    try:
                        detail_info = self.extract_detail_info(
                            product['url'], 
                            product['name'], 
                            product.get('button_element')
                        )
                        product['detail_info'] = detail_info
                        
                        if 'button_element' in product:
                            del product['button_element']
                        
                        # 수집된 필드 개수 확인
                        collected_fields = len([v for k, v in detail_info.items() 
                                              if k not in ['raw_data', 'url'] and v])
                        self.logger.info(f"    수집 완료: {collected_fields}/7개 필드")
                        
                        # 목록으로 복귀 전 알럿 확인
                        self.dismiss_any_alerts()
                        
                        # 목록으로 복귀
                        if i < len(deposit_products) - 1:
                            self.driver.get(self.base_url)
                            time.sleep(3)
                    
                    except Exception as e:
                        self.logger.info(f"    오류: 상품 처리 중 오류: {e}")
                        # 알럿 처리
                        self.dismiss_any_alerts()
                        # 목록으로 복귀
                        try:
                            self.driver.get(self.base_url)
                            time.sleep(3)
                        except:
                            pass
                        continue
                
                self.all_products.extend(deposit_products)
                self.logger.info(f"예금 상품 수집 완료: {len(deposit_products)}개")
            
            # 적금 상품 수집
            if self.click_savings_tab():
                self.logger.info("적금 상품 수집 중...")
                savings_products = self.get_products_from_page('적금')
                
                if savings_products:
                    self.logger.info(f"적금 상품 상세정보 수집...")
                    for i, product in enumerate(savings_products):
                        self.logger.info(f"[{i+1}/{len(savings_products)}] {product['name']} (적금) 처리 중...")
                        
                        try:
                            detail_info = self.extract_detail_info(
                                product['url'], 
                                product['name'], 
                                product.get('button_element')
                            )
                            product['detail_info'] = detail_info
                            
                            if 'button_element' in product:
                                del product['button_element']
                            
                            # 수집된 필드 개수 확인
                            collected_fields = len([v for k, v in detail_info.items() 
                                                  if k not in ['raw_data', 'url'] and v])
                            self.logger.info(f"    수집 완료: {collected_fields}/7개 필드")
                            
                            # 목록으로 복귀 전 알럿 확인
                            self.dismiss_any_alerts()
                            
                            # 목록으로 복귀
                            if i < len(savings_products) - 1:
                                self.driver.get(self.savings_url)
                                time.sleep(3)
                        
                        except Exception as e:
                            self.logger.info(f"    오류: 상품 처리 중 오류: {e}")
                            # 알럿 처리
                            self.dismiss_any_alerts()
                            # 목록으로 복귀
                            try:
                                self.driver.get(self.savings_url)
                                time.sleep(3)
                            except:
                                pass
                            continue
                    
                    self.all_products.extend(savings_products)
                    self.logger.info(f"적금 상품 수집 완료: {len(savings_products)}개")
            
            self.logger.info(f"수집 완료 - 예금: {len([p for p in self.all_products if p.get('category') == '예금'])}개, 적금: {len([p for p in self.all_products if p.get('category') == '적금'])}개, 총: {len(self.all_products)}개")
            
        except Exception as e:
            self.logger.info(f"오류: 전체 수집 오류: {e}")
            # 최종 알럿 처리
            self.dismiss_any_alerts()
    
    # 모든 알럿 처리
    def dismiss_any_alerts(self):
        try:
            while True:
                try:
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    self.logger.info(f"    오류: 알럿 처리: '{alert_text}'")
                    alert.dismiss()
                    time.sleep(1)
                except:
                    break
        except:
            pass
    
    # JSON 파일 저장
    def save_data(self, filename="KB.json"):
        dotenv.load_dotenv()
        directory_path = os.getenv("JSON_RESULT_PATH")
        os.makedirs(directory_path, exist_ok=True)
        full_path = os.path.join(directory_path, filename)

        try:
            clean_products = []
            for product in self.all_products:
                clean_product = {}
                for key, value in product.items():
                    if key != 'button_element' and value:
                        if key == 'detail_info' and isinstance(value, dict):
                            clean_detail = {k: v for k, v in value.items() if v and str(v).strip()}
                            if clean_detail:
                                clean_product[key] = clean_detail
                        else:
                            clean_product[key] = value
                        
                if clean_product:
                    clean_products.append(clean_product)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(clean_products, f, ensure_ascii=False, indent=2)
            self.logger.info(f"JSON 데이터가 {filename}에 저장되었습니다.")
            
        except Exception as e:
            self.logger.info(f"JSON 저장 오류: {e}")
    
    # 수집 결과 요약 출력
    def self.logger.info_summary(self):
        self.logger.info("수집 결과 요약")
        
        total_products = len(self.all_products)
        deposit_count = len([p for p in self.all_products if p.get('category') == '예금'])
        savings_count = len([p for p in self.all_products if p.get('category') == '적금'])
        
        self.logger.info(f"전체 상품: {total_products}개")
        self.logger.info(f"예금: {deposit_count}개")
        self.logger.info(f"적금: {savings_count}개")
        
        successful_details = 0
        field_stats = {
            '저축금액': 0, '가입대상': 0, '계약기간': 0, 
            '거래방법': 0, '세제혜택': 0, '기본이율': 0, '우대이율': 0
        }
        
        for product in self.all_products:
            detail_info = product.get('detail_info', {})
            if detail_info and not detail_info.get('error'):
                successful_details += 1
                for field in field_stats:
                    if detail_info.get(field):
                        field_stats[field] += 1
        
        self.logger.info("상세정보 수집 현황:")
        self.logger.info(f"성공: {successful_details}개 ({successful_details/total_products*100:.1f}%)")
        for field, count in field_stats.items():
            self.logger.info(f"{field}: {count}개")
        
        url_count = len([p for p in self.all_products 
                        if p.get('detail_info', {}).get('url')])
        self.logger.info(f"URL: {url_count}개")
    
    # 크롤링 실행
    def run(self):
        try:
            start_time = datetime.now()
            
            self.logger.info("국민은행 예금/적금 크롤링 시작")
            self.logger.info(f"실행 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            self.collect_all_products()
            
            if not self.all_products:
                self.logger.info("상품 목록을 수집하지 못했습니다.")
                return None
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info("크롤링 완료")
            self.logger.info(f"소요 시간: {duration:.1f}초")
            
            self.self.logger.info_summary()
            
            self.save_data()
            
            return {
                'timestamp': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_seconds': duration,
                'total_products': len(self.all_products),
                'deposit_count': len([p for p in self.all_products if p.get('category') == '예금']),
                'savings_count': len([p for p in self.all_products if p.get('category') == '적금'])
            }
            
        except Exception as e:
            self.logger.info(f"크롤링 오류: {str(e)}")
            return None
        finally:
            self.driver.quit()

    def start(self):
        self.logger.info("국민은행 예금/적금 크롤러 v2.0")
        self.logger.info("예금 + 적금 전체 수집")
        self.logger.info("7개 필수 항목 구조화 추출")

        result = self.run()

        if result:
            self.logger.info("크롤링 성공")
            self.logger.info(f"파일: kb_products.json")
            self.logger.info(f"예금 {result['deposit_count']}개 + 적금 {result['savings_count']}개 = 총 {result['total_products']}개")
        else:
            self.logger.info("크롤링 실패")

