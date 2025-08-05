from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import json
import re
import dotenv
import os
from src.crawler.util.BankLink import BankLink
import logging


class HanaBankCrawler:
    # 하나은행 예적금 상품 크롤러 초기화
    def __init__(self, headless=True):
        self.base_url =BankLink.HANA_BANK_LINK.value
        self.driver = self.setup_driver(headless)
        self.all_products = []
        self.logger = logging.getLogger(__name__)

        # 크롤링 순서에 맞는 탭 매핑
        self.tabs = {
            '정기예금': None,
            '적금': 'spb_2812',
            '입출금이 자유로운 예금': 'spb_2813'
        }
        
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
    
    # 크롤링 순서별 탭 전환
    def click_tab(self, tab_name):
        try:
            tab_id = self.tabs[tab_name]
            
            if tab_id is None:
                self.logger.info(f"{tab_name} - 기본 상태 (전환 불필요)")
                return True
            else:
                self.logger.info(f"{tab_name} 탭으로 전환 중...")
                script = f"doTab('{tab_id}')"
                self.driver.execute_script(script)
                time.sleep(5)
                self.logger.info(f"{tab_name} 탭 활성화 완료")
                return True
                
        except Exception as e:
            self.logger.info(f"{tab_name} 탭 전환 오류: {str(e)}")
            return False
    
    # 상품 목록에서 가입방법 추출
    def extract_join_method_from_list(self, product_link, product_name):
        try:
            container = None
            
            # 다양한 방법으로 컨테이너 찾기
            try:
                container = product_link.find_element(By.XPATH, "./ancestor::tr[1]")
            except:
                try:
                    container = product_link.find_element(By.XPATH, "./ancestor::li[1]")
                except:
                    try:
                        container = product_link.find_element(By.XPATH, "./ancestor::div[@class][1]")
                    except:
                        current = product_link
                        for _ in range(5):
                            try:
                                current = current.find_element(By.XPATH, "./..")
                                if current and current.text:
                                    container = current
                                    break
                            except:
                                break
            
            if container:
                container_text = re.sub(r'\s+', ' ', container.text).strip()
                
                # 가입방법 키워드 찾기
                keywords_found = []
                
                if '영업점' in container_text:
                    keywords_found.append('영업점')
                if '스마트폰' in container_text:
                    keywords_found.append('스마트폰')
                if '인터넷' in container_text and '인터넷뱅킹' not in container_text:
                    keywords_found.append('인터넷뱅킹')
                elif '인터넷뱅킹' in container_text:
                    keywords_found.append('인터넷뱅킹')
                if '온/' in container_text:
                    return '온/영업점'
                if '폰뱅킹' in container_text:
                    keywords_found.append('폰뱅킹')
                
                # 키워드 조합 규칙
                if '영업점' in keywords_found and '스마트폰' in keywords_found:
                    return '영업점 스마트폰'
                elif '스마트폰' in keywords_found:
                    return '스마트폰'
                elif '영업점' in keywords_found:
                    return '영업점'
                elif '인터넷뱅킹' in keywords_found:
                    return '인터넷뱅킹'
                elif '폰뱅킹' in keywords_found:
                    return '폰뱅킹'
                else:
                    return ""
            
            return ""
                
        except Exception as e:
            self.logger.info(f"      가입방법 추출 오류: {e}")
            return ""

# 현재 탭의 상품명 링크와 가입방법을 함께 수집
    def get_current_tab_products(self, tab_name):
        products = []
        try:
            self.logger.info(f"\n=== {tab_name} 상품 수집 중 ===")
            
            # 페이지 로드 대기
            time.sleep(3)
            
            # 상품 링크들 찾기
            product_links = self.driver.find_elements(
                By.XPATH, 
                "//em/a[contains(@href, 'mall080')]"
            )
            
            self.logger.info(f"발견된 상품명 링크: {len(product_links)}개")
            
            for i, link in enumerate(product_links):
                try:
                    product_name = link.text.strip()
                    product_url = link.get_attribute("href")
                    
                    if product_name and product_url and 'kebhana.com' in product_url and len(product_name) < 50:
                        # 상품별 가입방법 추출
                        join_method = self.extract_join_method_from_list(link, product_name)
                        
                        products.append({
                            'category': tab_name,
                            'index': i + 1,
                            'name': product_name,
                            'url': product_url,
                            'join_method_from_list': join_method,
                            'detail_info': {}
                        })
                        
                        join_method_display = join_method if join_method else "키워드 없음"
                        self.logger.info(f"  {i+1}. {product_name} → {join_method_display}")
                    else:
                        self.logger.info(f"  제외: {product_name} (길이: {len(product_name)})")
                
                except Exception as e:
                    self.logger.info(f"  링크 {i+1} 처리 오류: {str(e)}")
                    continue
            
            self.logger.info(f"{tab_name}: {len(products)}개 상품 수집 완료")
            return products
            
        except Exception as e:
            self.logger.info(f"{tab_name} 상품 수집 오류: {str(e)}")
            return []
    
    # 페이지네이션을 처리하여 모든 상품 수집
    def get_current_tab_products_with_pagination(self, tab_name):
        all_products = []
        page_index = 0
        page_number = 1
        
        while True:
            self.logger.info(f"{tab_name} 페이지 {page_number} 수집 중...")
            
            # 현재 페이지 상품 수집
            page_products = self.get_current_tab_products(tab_name)
            
            if page_products:
                all_products.extend(page_products)
                self.logger.info(f"페이지 {page_number}: {len(page_products)}개 상품 수집")
                
                # 상품이 10개 미만이면 마지막 페이지
                if len(page_products) < 10:
                    self.logger.info(f"페이지 {page_number}가 마지막 페이지 (상품 {len(page_products)}개)")
                    break
            else:
                self.logger.info(f"페이지 {page_number}: 상품 없음 - 마지막 페이지")
                break
            
            # 다음 페이지로 이동
            page_index += 10
            page_number += 1
            
            if not self.go_to_page(page_index):
                break
            
            time.sleep(3)
        
        self.logger.info(f"{tab_name} 총 {len(all_products)}개 상품 수집 완료 ({page_number}페이지)")
        return all_products
    
    # 특정 페이지로 이동
    def go_to_page(self, page_index):
        try:
            self.logger.info(f"doPaging('{page_index}')로 페이지 이동...")
            script = f"doPaging('{page_index}')"
            self.driver.execute_script(script)
            time.sleep(3)
            self.logger.info(f"페이지 {page_index//10 + 1}로 이동 완료")
            return True
        except Exception as e:
            self.logger.info(f"페이지 이동 오류 (무시): {str(e)[:50]}...")
            return True

    # 다음 페이지가 있는지 확인
    def has_next_page(self):
        try:
            # 다음 버튼 찾기
            next_elements = self.driver.find_elements(
                By.XPATH, 
                "//*[contains(text(), '다음') and contains(text(), '10개')]"
            )
            
            for next_btn in next_elements:
                if next_btn.is_displayed():
                    is_disabled = next_btn.get_attribute("disabled")
                    self.logger.info(f"다음 버튼 상태: {'비활성화' if is_disabled else '활성화'}")
                    return not is_disabled
            
            return False
        except Exception as e:
            self.logger.info(f"다음 페이지 확인 오류: {e}")
            return False

# 상품 상세정보 추출
    def extract_product_detail(self, product_url, product_name, category, join_method_from_list=""):
        detail_info = {
            '가입대상': '',
            '가입금액': '',
            '가입기간': '',
            '기본금리': '',
            '우대금리': '',
            '세제혜택': '',
            '가입방법': join_method_from_list
        }
        
        main_window = self.driver.current_window_handle
        
        try:
            self.logger.info(f"    상세정보 수집: {product_name}")
            if join_method_from_list:
                self.logger.info(f"    목록 가입방법: {join_method_from_list}")
            
            # 새 탭에서 상세페이지 열기
            self.driver.execute_script(f"window.open('{product_url}', '_blank');")
            time.sleep(2)
            
            windows = self.driver.window_handles
            if len(windows) > 1:
                self.driver.switch_to.window(windows[1])
                time.sleep(3)
                
                # 핵심 정보 추출
                self.extract_core_info_optimized(detail_info)
                
                # 새 탭 닫기
                self.driver.close()
                self.driver.switch_to.window(main_window)
                
                extracted_count = len([v for v in detail_info.values() if v])
                self.logger.info(f"    {extracted_count}개 항목 추출 완료")
            
        except Exception as e:
            self.logger.info(f"    상세정보 추출 오류: {str(e)}")
            detail_info['error'] = str(e)
            
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(main_window)
            except:
                pass
        
        return detail_info
    
    # 핵심 정보 추출
    def extract_core_info_optimized(self, detail_info):
        
        # 1. 가입방법 추출 (목록에서 이미 추출한 경우 건너뛰기)
        if not detail_info.get('가입방법'):
            try:
                join_method_patterns = [
                    "인터넷뱅킹, 스마트폰뱅킹, 폰뱅킹",
                    "영업점 인터넷 스마트폰",
                    "영업점, 인터넷뱅킹, 스마트폰뱅킹"
                ]
                
                elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '인터넷뱅킹') or contains(text(), '스마트폰뱅킹') or contains(text(), '영업점')]")
                for elem in elements:
                    text = elem.text.strip()
                    if any(pattern in text for pattern in ["인터넷뱅킹", "스마트폰뱅킹"]) and len(text) < 100:
                        detail_info['가입방법'] = text
                        self.logger.info(f"      가입방법: {text}")
                        break
                        
            except Exception as e:
                self.logger.info(f"      가입방법 추출 오류: {e}")
        
        # 2-5. DT/DD 구조로 기본 정보 추출
        try:
            dt_elements = self.driver.find_elements(By.TAG_NAME, "dt")
            
            for dt in dt_elements:
                try:
                    label = dt.text.strip()
                    dd_element = dt.find_element(By.XPATH, "following-sibling::dd[1]")
                    value = dd_element.text.strip()
                    
                    if not value:
                        continue
                    
                    # 라벨에 따른 매핑
                    if '가입금액' in label or '최저가입금액' in label or '납입금액' in label:
                        detail_info['가입금액'] = value
                        self.logger.info(f"      가입금액: {value}")
                    
                    elif '가입대상' in label or '대상' in label:
                        detail_info['가입대상'] = value
                        self.logger.info(f"      가입대상: {value}")
                    
                    elif '가입기간' in label or '기간' in label:
                        detail_info['가입기간'] = value
                        self.logger.info(f"      가입기간: {value}")
                    
                    elif '세제혜택' in label or '세금' in label:
                        detail_info['세제혜택'] = value
                        self.logger.info(f"      세제혜택: {value}")
                
                except Exception as e:
                    continue
        
        except Exception as e:
            self.logger.info(f"      DT/DD 추출 오류: {e}")
        
        # 6. 금리 테이블 추출
        try:
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            self.logger.info(f"      총 {len(tables)}개 테이블 발견")
            
            for i, table in enumerate(tables):
                if not table.is_displayed():
                    continue
                
                # 테이블 캡션 확인
                caption_text = ""
                caption = table.find_elements(By.TAG_NAME, "caption")
                if caption:
                    caption_text = caption[0].text.strip().lower()
                
                # 테이블 전체 텍스트
                table_text = table.text.lower()
                
                # 금리 관련 테이블인지 확인
                is_rate_table = ('금리' in table_text or '%' in table_text or 
                               'tbl_col01' in table.get_attribute("class"))
                
                if is_rate_table:
                    table_data = self.extract_table_data_complete(table)
                    
                    # 우대금리 테이블 판단
                    is_preferential = (
                        '우대' in caption_text or '우대' in table_text or
                        ('수수료' in caption_text and '우대' in table_text) or
                        '달곤미니하나통장 우대금리' in caption_text or
                        '변경사항' in caption_text
                    )
                    
                    if is_preferential:
                        detail_info['우대금리'] = table_data
                        self.logger.info(f"      우대금리 테이블 추출: {caption_text}")
                    
                    else:
                        # 기본금리 테이블
                        if not detail_info['기본금리'] or len(table_data.get('data', [])) > len(detail_info['기본금리'].get('data', [])):
                            detail_info['기본금리'] = table_data
                            self.logger.info(f"      기본금리 테이블 추출: {caption_text}")
        
        except Exception as e:
            self.logger.info(f"      금리 테이블 추출 오류: {e}")
    
    # 테이블 데이터를 완전히 구조화하여 추출
    def extract_table_data_complete(self, table):
        try:
            table_data = {
                'headers': [],
                'data': [],
                'caption': '',
                'class': table.get_attribute("class"),
                'summary': table.get_attribute("summary") or ""
            }
            
            # 캡션 추출
            caption = table.find_elements(By.TAG_NAME, "caption")
            if caption:
                table_data['caption'] = caption[0].text.strip()
            
            # 테이블 행들 추출
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            for row_index, row in enumerate(rows):
                # 헤더 행 처리 (th만 있는 행)
                ths = row.find_elements(By.TAG_NAME, "th")
                tds = row.find_elements(By.TAG_NAME, "td")
                
                if ths and not tds and not table_data['headers']:
                    # 순수 헤더 행
                    table_data['headers'] = [th.text.strip() for th in ths]
                    continue
                
                # 데이터 행 처리 (td만 있는 행)
                elif tds and not ths:
                    row_data = [td.text.strip() for td in tds]
                    if any(row_data):
                        table_data['data'].append(row_data)
                
                # 혼합 행 처리 (th와 td가 같이 있는 행)
                elif ths and tds:
                    mixed_row = {}
                    for i, th in enumerate(ths):
                        th_text = th.text.strip()
                        if i < len(tds):
                            td_text = tds[i].text.strip()
                            if th_text and td_text:
                                mixed_row[th_text] = td_text
                    
                    if mixed_row:
                        table_data['data'].append(mixed_row)
                    else:
                        # 순서대로 배열로 처리
                        all_cells = []
                        for cell in row.find_elements(By.XPATH, ".//th | .//td"):
                            all_cells.append(cell.text.strip())
                        
                        if any(all_cells):
                            table_data['data'].append(all_cells)
            
            return table_data
            
        except Exception as e:
            self.logger.info(f"테이블 데이터 추출 오류: {e}")
            return {'headers': [], 'data': [], 'caption': '', 'class': '', 'summary': ''}
        
# 모든 상품 수집
    def collect_all_products(self):
        try:
            self.logger.info("전체 상품 수집 시작")
            
            # 메인 페이지 접속 (기본 상태: 정기예금)
            self.driver.get(self.base_url)
            time.sleep(5)
            
            # 크롤링 순서에 맞는 탭 리스트
            tab_order = ['정기예금', '적금', '입출금이 자유로운 예금']
            
            for tab_name in tab_order:
                try:
                    self.logger.info(f"\n{tab_name} 탭 처리 시작")
                    
                    # 탭 전환
                    if not self.click_tab(tab_name):
                        continue
                    
                    # 페이지네이션 처리하여 모든 상품 수집
                    if tab_name == '입출금이 자유로운 예금':
                        # 입출금만 페이지네이션 적용
                        tab_products = self.get_current_tab_products_with_pagination(tab_name)
                    else:
                        # 정기예금, 적금은 기존 방식
                        tab_products = self.get_current_tab_products(tab_name)
                    
                    if tab_products:
                        self.all_products.extend(tab_products)
                        self.logger.info(f"{tab_name}: 총 {len(tab_products)}개 상품 수집 완료")
                        
                        # 수집된 상품 목록 미리보기
                        self.logger.info(f"{tab_name} 상품 목록:")
                        for i, product in enumerate(tab_products[:3]):
                            self.logger.info(f"   {i+1}. {product['name']}")
                        if len(tab_products) > 3:
                            self.logger.info(f"   ... 외 {len(tab_products)-3}개")
                    else:
                        self.logger.info(f"{tab_name}: 상품을 찾을 수 없음")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    self.logger.info(f"{tab_name} 처리 오류: {str(e)}")
                    continue
            
            total_count = len(self.all_products)
            self.logger.info(f"\n수집 완료 - 정기예금: {len([p for p in self.all_products if p['category'] == '정기예금'])}개, 적금: {len([p for p in self.all_products if p['category'] == '적금'])}개, 입출금: {len([p for p in self.all_products if p['category'] == '입출금이 자유로운 예금'])}개, 총: {total_count}개")
            
            # 상세정보 수집 호출
            if self.all_products:
                self.collect_detail_info()
            else:
                self.logger.info("수집된 상품이 없어 상세정보 수집을 건너뜁니다.")
            
        except Exception as e:
            self.logger.info(f"전체 수집 오류: {str(e)}")
    
    # 모든 상품의 상세정보 수집
    def collect_detail_info(self):
        try:
            self.logger.info(f"\n상품별 상세정보 수집 시작")
            
            success_count = 0
            
            for i, product in enumerate(self.all_products):
                try:
                    self.logger.info(f"\n[{i+1}/{len(self.all_products)}] {product['name']} ({product['category']}) 처리 중...")
                    
                    # 목록에서 추출한 가입방법
                    join_method_from_list = product.get('join_method_from_list', '')
                    
                    # 상세정보 추출
                    detail_info = self.extract_product_detail(
                        product['url'], 
                        product['name'], 
                        product['category'],
                        join_method_from_list
                    )
                    product['detail_info'] = detail_info
                    
                    if not detail_info.get('error'):
                        success_count += 1
                        
                        # 추출된 정보 간단 요약
                        extracted_fields = [k for k, v in detail_info.items() if v]
                        self.logger.info(f"    수집 완료: {len(extracted_fields)}/7개 필드")
                    
                    # 요청 간격 조절
                    time.sleep(2)
                
                except Exception as e:
                    self.logger.info(f"    오류: {str(e)}")
                    product['detail_info'] = {'error': str(e)}
                    continue
            
            self.logger.info("모든 상품 상세정보 수집 완료")
            
        except Exception as e:
            self.logger.info(f"상세정보 수집 오류: {str(e)}")
    
    # JSON 파일로 저장
    def save_data(self, filename="HANA.json"):
        dotenv.load_dotenv()
        directory_path = os.getenv("JSON_RESULT_PATH")

        os.makedirs(directory_path, exist_ok=True)
        full_path = os.path.join(directory_path, filename)

        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(self.all_products, f, ensure_ascii=False, indent=2)
            self.logger.info(f"JSON 데이터가 {filename}에 저장되었습니다.")
        except Exception as e:
            self.logger.info(f"JSON 저장 오류: {str(e)}")
    
    # 수집 결과 요약 출력
    def print_summary(self):
        self.logger.info("수집 결과 요약")
        
        total_products = len(self.all_products)
        deposit_count = len([p for p in self.all_products if p['category'] == '정기예금'])
        savings_count = len([p for p in self.all_products if p['category'] == '적금'])
        checking_count = len([p for p in self.all_products if p['category'] == '입출금이 자유로운 예금'])
        
        self.logger.info(f"전체 상품: {total_products}개")
        self.logger.info(f"정기예금: {deposit_count}개")
        self.logger.info(f"적금: {savings_count}개")
        self.logger.info(f"입출금이 자유로운 예금: {checking_count}개")
        
        successful_details = 0
        field_stats = {
            '가입대상': 0, '가입금액': 0, '가입기간': 0, 
            '기본금리': 0, '우대금리': 0, '세제혜택': 0, '가입방법': 0
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
                        if p.get('detail_info', {}).get('가입방법')])
        self.logger.info(f"가입방법: {url_count}개")
    
    # 크롤링 실행
    def run(self):
        try:
            from datetime import datetime
            start_time = datetime.now()
            
            self.logger.info("하나은행 예금/적금 크롤링 시작")
            self.logger.info(f"실행 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            self.collect_all_products()
            
            if not self.all_products:
                self.logger.info("상품 목록을 수집하지 못했습니다.")
                return None
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info("크롤링 완료")
            self.logger.info(f"소요 시간: {duration:.1f}초")
            
            self.print_summary()
            
            self.save_data()
            
            return {
                'timestamp': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_seconds': duration,
                'total_products': len(self.all_products),
                'deposit_count': len([p for p in self.all_products if p['category'] == '정기예금']),
                'savings_count': len([p for p in self.all_products if p['category'] == '적금']),
                'checking_count': len([p for p in self.all_products if p['category'] == '입출금이 자유로운 예금'])
            }
            
        except Exception as e:
            self.logger.info(f"크롤링 오류: {str(e)}")
            return None
        finally:
            self.driver.quit()

    # 브라우저 종료
    def close_driver(self):
        try:
            self.driver.quit()
            self.logger.info("브라우저가 종료되었습니다.")
        except Exception as e:
            self.logger.info(f"브라우저 종료 오류: {str(e)}")

    def start(self):
        self.logger.info("하나은행 예금/적금 크롤러 v2.0")
        self.logger.info("정기예금 + 적금 + 입출금이 자유로운 예금 전체 수집")
        self.logger.info("7개 필수 항목 구조화 추출")

        result = self.run()

        if result:
            self.logger.info("크롤링 성공")
            self.logger.info(f"파일: hana_bank_products.json")
            self.logger.info(
                f"정기예금 {result['deposit_count']}개 + 적금 {result['savings_count']}개 + 입출금 {result['checking_count']}개 = 총 {result['total_products']}개")
        else:
            self.logger.info("크롤링 실패")

