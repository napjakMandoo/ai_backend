from selenium import webdriver
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime
import re
import time
import json
import dotenv
import os

class JejuBankDepositSavingsOnlyCrawler:

    def __init__(self, headless: bool = True, timeout: int = 15, base_url:str=""):
        self.headless = headless
        self.timeout = timeout
        self.driver = self._create_driver()
        self.base_url = base_url

    def _create_driver(self) -> webdriver.Chrome:
        options = Options()
        if self.headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        return webdriver.Chrome(options=options)

    def safe_find_text(self, element, selector, default="-"):
        """안전하게 텍스트를 찾는 헬퍼 함수"""
        try:
            return element.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return default

    def determine_product_category(self, product_name, product_badge=""):
        """상품명과 배지로 카테고리 결정 (예금/적금만)"""
        text = (product_name + " " + product_badge).lower()
        
        if "적금" in text or "savings" in text:
            return "적금"
        else:
            return "예금"

    def extract_product_id_from_href(self, href_attr):
        """href 속성에서 상품 ID 추출"""
        if not href_attr:
            return ""
        
        try:
            match = re.search(r"'(SID_[^']+)'", href_attr)
            if match:
                return match.group(1)
        except:
            pass
        return ""

    def select_deposit_products(self):
        """예금 상품만 선택"""
        try:
            deposit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[name="cdVal"][value="00"]')
            if not deposit_button.get_attribute('class') or 'active' not in deposit_button.get_attribute('class'):
                deposit_button.click()
                time.sleep(2)
        except Exception as e:
            pass

    def select_savings_products(self):
        """적금 상품만 선택 (예금 해제 후 적금 선택)"""
        try:
            # 예금 버튼 해제 (이미 active 상태이므로 클릭하면 해제됨)
            deposit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[name="cdVal"][value="00"]')
            if 'active' in deposit_button.get_attribute('class'):
                deposit_button.click()
                time.sleep(1)
            
            # 적금 버튼 선택
            savings_button = self.driver.find_element(By.CSS_SELECTOR, 'button[name="cdVal"][value="01"]')
            savings_button.click()
            time.sleep(2)
        except Exception as e:
            pass

    def load_all_products(self):
        """더보기 버튼을 클릭해서 모든 상품 로드"""
        while True:
            try:
                more_button = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    'button.btn.white[onclick*="fn_loadMore"]'
                )
                
                if more_button.is_displayed():
                    more_button.click()
                    time.sleep(3)
                else:
                    break
            except NoSuchElementException:
                break

    def extract_basic_product_info(self, product_type="예금"):
        """상품 목록에서 기본 정보 추출"""
        products = []
        
        try:
            product_list = self.driver.find_element(By.ID, "prdList")
            product_items = product_list.find_elements(By.TAG_NAME, "li")
            
            for idx, item in enumerate(product_items):
                try:
                    # 상품명
                    title_elem = item.find_element(By.CSS_SELECTOR, "h3.tit")
                    name = title_elem.text.strip()
                    
                    # 상품 카테고리
                    category_elem = item.find_element(By.CSS_SELECTOR, ".prd-badge")
                    product_badge = category_elem.text.strip()
                    
                    # 상품 설명
                    desc_elem = item.find_element(By.CSS_SELECTOR, "p.txt")
                    description = desc_elem.text.strip()
                    
                    # 배지들
                    badges = item.find_elements(By.CSS_SELECTOR, ".badge")
                    badge_list = [badge.text.strip() for badge in badges]
                    
                    # 상품 ID 추출
                    link = item.find_element(By.CSS_SELECTOR, 'a[href*="javascript:fn_setSessionStorage"]')
                    href_attr = link.get_attribute('href')
                    product_id = self.extract_product_id_from_href(href_attr)
                    
                    # 목록에서 금리 정보 추출 (있는 경우만)
                    basic_rate = ""
                    max_rate = ""
                    
                    try:
                        rates_group = item.find_element(By.CSS_SELECTOR, ".rates-group")
                        rates_text = rates_group.text.strip()
                        
                        basic_match = re.search(r'기본 연 : ([\d.]+%)', rates_text)
                        max_match = re.search(r'최고 연([\d.]+%)', rates_text)
                        
                        if basic_match:
                            basic_rate = basic_match.group(1)
                        if max_match:
                            max_rate = max_match.group(1)
                            
                    except NoSuchElementException:
                        rate_texts = item.text
                        rate_matches = re.findall(r'연 ([\d.]+%)', rate_texts)
                        if rate_matches:
                            if len(rate_matches) >= 2:
                                basic_rate = rate_matches[0]
                                max_rate = rate_matches[1]
                            elif len(rate_matches) == 1:
                                basic_rate = rate_matches[0]
                    
                    product_data = {
                        "name": name,
                        "product_badge": product_badge,
                        "description": description,
                        "badges": badge_list,
                        "product_id": product_id,
                        "basic_rate": basic_rate,
                        "max_rate": max_rate,
                        "list_index": idx + 1,
                        "product_type": product_type
                    }
                    
                    products.append(product_data)
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            pass
            
        return products

    def get_product_detail_url(self, product_id):
        """상품 ID로 상세 페이지 URL 생성"""
        return f"{self.base_url}?mode=detail&prdId={product_id}"

    def crawl_product_detail(self, product_id):
        """상품 상세 정보 크롤링 - 기본 정보만"""
        url_link = self.get_product_detail_url(product_id)
        detail_info = {}
        
        try:
            self.driver.get(url_link)
            time.sleep(3)
            
            # 상품명 추출
            try:
                product_title = self.driver.find_element(By.CSS_SELECTOR, "h3.product-tit")
                detail_info['name'] = product_title.text.strip()
            except:
                detail_info['name'] = ""
            
            # 금리 정보 추가 추출
            try:
                basic_rate_elem = self.driver.find_element(By.CSS_SELECTOR, ".card3:first-child p.txt")
                basic_rate_text = basic_rate_elem.text.strip()
                basic_rate_match = re.search(r'연\s*([\d.]+)%', basic_rate_text)
                detail_info['basic_rate'] = basic_rate_match.group(1) + '%' if basic_rate_match else ''
            except:
                detail_info['basic_rate'] = ''
                
            try:
                max_rate_elem = self.driver.find_element(By.CSS_SELECTOR, ".card3:last-child p.txt")
                max_rate_text = max_rate_elem.text.strip()
                max_rate_match = re.search(r'연\s*([\d.]+)%', max_rate_text)
                detail_info['max_rate'] = max_rate_match.group(1) + '%' if max_rate_match else ''
            except:
                detail_info['max_rate'] = ''
            
            # 상품안내 탭 클릭
            try:
                product_info_tab = self.driver.find_element(
                    By.XPATH, 
                    "//button[contains(text(), '상품안내') and @aria-controls='section1']"
                )
                if 'active' not in product_info_tab.get_attribute('class'):
                    product_info_tab.click()
                    time.sleep(1)
            except:
                pass
            
            # DT-DD 구조에서 기본 정보 추출
            dt_elements = self.driver.find_elements(By.CSS_SELECTOR, "dt")
            
            for dt in dt_elements:
                try:
                    key = dt.text.strip()
                    dd = dt.find_element(By.XPATH, "following-sibling::dd[1]")
                    
                    if dd and key:
                        value = dd.text.strip()
                        # 세제혜택은 여기서 제외 (유의사항 탭에서 별도 추출)
                        if value and len(key) < 50 and key != "세제혜택":
                            detail_info[key] = value
                                
                except Exception as e:
                    continue
                    
            return detail_info
            
        except Exception as e:
            return {'error': f"Failed to crawl detail: {str(e)}"}

    def get_element_innertext_with_bullets(self, element):
        """JavaScript를 사용하여 element의 innerText 추출 + CSS ::before 불릿포인트 추가"""
        try:
            # JavaScript로 각 li 요소의 ::before 내용과 텍스트를 조합
            enhanced_text = self.driver.execute_script("""
                const element = arguments[0];
                const listItems = element.querySelectorAll('li');
                let result = element.innerText;
                
                listItems.forEach(li => {
                    // li의 직접적인 텍스트만 가져오기 (중첩된 요소 제외)
                    let liText = '';
                    for (let node of li.childNodes) {
                        if (node.nodeType === Node.TEXT_NODE) {
                            liText += node.textContent;
                        }
                    }
                    liText = liText.trim();
                    
                    if (!liText) return;
                    
                    // 부모 ul의 클래스 확인
                    const parentUl = li.parentElement;
                    const ulClass = parentUl.className || '';
                    
                    // ::before 스타일 가져오기
                    const beforeStyle = window.getComputedStyle(li, '::before');
                    let bullet = beforeStyle.content;
                    
                    // content 값 정리
                    if (bullet && bullet !== 'none' && bullet !== '""') {
                        bullet = bullet.replace(/['"]/g, ''); // 따옴표 제거
                    } else {
                        // CSS content가 없으면 클래스명으로 판단
                        if (ulClass.includes('listTypeDot')) {
                            bullet = '•';
                        } else if (ulClass.includes('listTypeDash')) {
                            bullet = '-';
                        } else {
                            bullet = '•'; // 기본값
                        }
                    }
                    
                    // 현재 줄의 시작 부분을 찾아서 불릿 추가
                    const lines = result.split('\\n');
                    for (let i = 0; i < lines.length; i++) {
                        const line = lines[i].trim();
                        // 정확한 매칭을 위해 li의 직접 텍스트와 비교
                        if (line.startsWith(liText) || liText.startsWith(line.substring(0, Math.min(line.length, 20)))) {
                            // 들여쓰기 정도 확인
                            const originalLine = lines[i];
                            const leadingSpaces = originalLine.match(/^\\s*/)[0];
                            lines[i] = leadingSpaces + bullet + ' ' + line;
                            break;
                        }
                    }
                    result = lines.join('\\n');
                });
                
                return result;
            """, element)
            
            return enhanced_text.strip()
            
        except Exception as e:
            print(f"불릿포인트 처리 오류: {e}")
            # 오류 시 기본 innerText 반환
            try:
                return self.driver.execute_script("return arguments[0].innerText;", element).strip()
            except:
                return element.text.strip()

    def parse_text_sections(self, full_text):
        """텍스트를 의미있는 섹션으로 분리 - innerText 기반 원본 구조 보존"""
        try:
            # innerText는 이미 깔끔하게 정리된 상태이므로 그대로 사용
            if len(full_text) <= 2000:
                return [full_text]
            
            # 2000자가 넘는 경우만 의미있는 단위로 분할
            sections = []
            lines = full_text.split('\n')
            current_section = ""
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 현재 섹션에 추가했을 때 2000자를 넘으면 섹션 분할
                if current_section and len(current_section + "\n" + line) > 2000:
                    sections.append(current_section)
                    current_section = line
                else:
                    if current_section:
                        current_section += "\n" + line
                    else:
                        current_section = line
            
            # 마지막 섹션 추가
            if current_section:
                sections.append(current_section)
            
            return sections if sections else [full_text]
            
        except Exception as e:
            return [full_text]

    def extract_rate_info_from_rate_tab(self, product_id):
        """금리안내 탭에서 기본금리와 우대금리 정보 추출"""
        rate_info = {
            'basic_rate': {
                'table_list': [],
                'table_count': 0,
                'text_info': []
            },
            'preferential_rate': {
                'text_info': [],
                'table_list': [],
                'table_count': 0
            }
        }
        
        url_link = self.get_product_detail_url(product_id)
        
        try:
            if self.driver.current_url != url_link:
                self.driver.get(url_link)
                time.sleep(3)
            
            # 금리안내 탭 클릭
            rate_tab = self.driver.find_element(By.CSS_SELECTOR, "button[aria-controls='section2']")
            if 'active' not in rate_tab.get_attribute('class'):
                self.driver.execute_script("arguments[0].click();", rate_tab)
                time.sleep(2)
            
            # section2 대기
            section2 = self.driver.find_element(By.ID, "section2")
            
            # DL.text-row-item에서 기본금리와 우대금리 섹션 찾기
            dl_elements = section2.find_elements(By.CSS_SELECTOR, "dl.text-row-item")
            
            for dl in dl_elements:
                try:
                    dt = dl.find_element(By.CSS_SELECTOR, "dt")
                    dt_text = dt.text.strip()
                    dd = dl.find_element(By.CSS_SELECTOR, "dd")
                    
                    if dt_text == "기본금리":
                        # 기본금리 테이블 추출
                        tables = dd.find_elements(By.CSS_SELECTOR, "table.col.my-0")
                        for table_idx, table in enumerate(tables):
                            table_data = self.extract_rate_table_structure(table)
                            if table_data:
                                table_data["table_index"] = table_idx + 1
                                rate_info['basic_rate']['table_list'].append(table_data)
                        
                        # 기본금리 텍스트 정보 (innerText 사용하여 깔끔한 구조 보존)
                        text_divs = dd.find_elements(By.CSS_SELECTOR, "div")
                        for div in text_divs:
                            try:
                                inner_text = self.driver.execute_script("return arguments[0].innerText;", div).strip()
                                if inner_text and len(inner_text) > 10:
                                    rate_info['basic_rate']['text_info'].append(inner_text)
                            except:
                                inner_text = div.text.strip()
                                if inner_text and len(inner_text) > 10:
                                    rate_info['basic_rate']['text_info'].append(inner_text)
                        
                        rate_info['basic_rate']['table_count'] = len(rate_info['basic_rate']['table_list'])
                    
                    elif dt_text == "우대금리":
                        # innerText 사용하여 깔끔한 텍스트 구조 보존 (불릿포인트 포함)
                        dd_inner_text = self.get_element_innertext_with_bullets(dd)
                        if dd_inner_text and len(dd_inner_text) > 10:
                            unique_lines = self.parse_text_sections(dd_inner_text)
                            rate_info['preferential_rate']['text_info'] = unique_lines
                        
                        # 우대금리 테이블 추출 (모든 table 요소를 대상으로)
                        tables = dd.find_elements(By.CSS_SELECTOR, "table")
                        for table_idx, table in enumerate(tables):
                            table_data = self.extract_preferential_table_structure(table, table_idx + 1)
                            if table_data:
                                rate_info['preferential_rate']['table_list'].append(table_data)
                        
                        rate_info['preferential_rate']['table_count'] = len(rate_info['preferential_rate']['table_list'])
                
                except Exception:
                    continue
                    
        except Exception as e:
            pass
            
        return rate_info

    def extract_tax_benefit_from_caution_tab(self, product_id):
        """유의사항 탭에서 세제혜택 정보 추출"""
        tax_benefit = ""
        
        url_link = self.get_product_detail_url(product_id)
        
        try:
            if self.driver.current_url != url_link:
                self.driver.get(url_link)
                time.sleep(3)
            
            # 유의사항 탭 클릭
            caution_tab = self.driver.find_element(By.CSS_SELECTOR, "button[aria-controls='section3']")
            if 'active' not in caution_tab.get_attribute('class'):
                self.driver.execute_script("arguments[0].click();", caution_tab)
                time.sleep(2)
            
            # section3에서 세제혜택 정보 찾기
            section3 = self.driver.find_element(By.ID, "section3")
            dl_elements = section3.find_elements(By.CSS_SELECTOR, "dl.text-row-item")
            
            for dl in dl_elements:
                try:
                    dt = dl.find_element(By.CSS_SELECTOR, "dt")
                    if dt.text.strip() == "세제혜택":
                        dd = dl.find_element(By.CSS_SELECTOR, "dd")
                        try:
                            tax_benefit = self.driver.execute_script("return arguments[0].innerText;", dd).strip()
                        except:
                            tax_benefit = dd.text.strip()
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            pass
            
        return tax_benefit

    def extract_rate_table_structure(self, table_element):
        """기본금리 테이블 구조 추출"""
        try:
            table_data = {
                "headers": [],
                "rows": []
            }
            
            # 행 추출
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            if not rows:
                return None
            
            # 헤더 추출 (첫 번째 행)
            if rows:
                header_cells = rows[0].find_elements(By.TAG_NAME, "th")
                if not header_cells:
                    header_cells = rows[0].find_elements(By.TAG_NAME, "td")
                
                headers = [cell.text.strip() for cell in header_cells if cell.text.strip()]
                table_data["headers"] = headers
            
            # 데이터 행 추출
            for row in rows[1:]:
                cells = row.find_elements(By.TAG_NAME, "td")
                if not cells:
                    cells = row.find_elements(By.TAG_NAME, "th")
                
                row_data = [cell.text.strip() for cell in cells]
                
                if any(cell.strip() for cell in row_data):
                    table_data["rows"].append(row_data)
            
            return table_data if table_data["headers"] or table_data["rows"] else None
                
        except Exception as e:
            return None

    def extract_preferential_table_structure(self, table_element, table_index):
        """우대서비스 테이블 구조 추출"""
        try:
            table_data = {
                "headers": [],
                "rows": [],
                "table_index": table_index
            }
            
            # 기본적인 테이블 구조 처리
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            
            # 첫 번째 행을 헤더로 처리
            if rows:
                header_cells = rows[0].find_elements(By.TAG_NAME, "th")
                if not header_cells:
                    header_cells = rows[0].find_elements(By.TAG_NAME, "td")
                
                headers = [cell.text.strip() for cell in header_cells if cell.text.strip()]
                table_data["headers"] = headers
            
            # 나머지 행들을 데이터로 처리
            for row in rows[1:]:
                cells = row.find_elements(By.TAG_NAME, "td")
                if not cells:
                    cells = row.find_elements(By.TAG_NAME, "th")
                
                row_data = [cell.text.strip() for cell in cells]
                
                if any(cell.strip() for cell in row_data):
                    table_data["rows"].append(row_data)
            
            return table_data if table_data["headers"] or table_data["rows"] else None
            
        except Exception as e:
            return None

    def map_detail_to_standard_format(self, detail_info):
        """상세 정보를 표준 포맷으로 매핑"""
        field_mapping = {
            '가입대상': 'sub_target',
            '가입금액': 'sub_amount',
            '가입기간': 'sub_term',
            '거래방법': 'sub_way',
            '예금종류': 'detail_type',
            '상품특징': 'product_description'
        }
        
        mapped_data = {}
        for jeju_field, standard_field in field_mapping.items():
            if jeju_field in detail_info:
                mapped_data[standard_field] = detail_info[jeju_field]
        
        return mapped_data

    def fetch_deposit_and_savings_products(self, limit_per_type=None):
        """예금과 적금 상품을 순차적으로 크롤링"""
        
        driver = self.driver
        driver.get(self.base_url)

        wait = WebDriverWait(driver, self.timeout)
        wait.until(EC.presence_of_element_located((By.ID, "prdList")))

        all_products = []
        
        # 1. 예금 상품 크롤링 (초기 상태가 예금 선택)
        self.select_deposit_products()  # 예금 버튼 확실히 선택
        time.sleep(2)
        
        # 더보기로 모든 예금 상품 로드
        if not limit_per_type:
            self.load_all_products()
        
        deposit_products_info = self.extract_basic_product_info("예금")
        if limit_per_type:
            deposit_products_info = deposit_products_info[:limit_per_type]
        
        # 2. 적금 상품 크롤링
        self.select_savings_products()  # 예금 해제 후 적금 선택
        time.sleep(2)
        
        # 더보기로 모든 적금 상품 로드
        if not limit_per_type:
            self.load_all_products()
        
        savings_products_info = self.extract_basic_product_info("적금")
        if limit_per_type:
            savings_products_info = savings_products_info[:limit_per_type]
        
        # 3. 모든 상품 합치기
        all_products_info = deposit_products_info + savings_products_info
        
        # 4. 각 상품의 상세 정보 크롤링
        products = []
        
        for idx, product_data in enumerate(all_products_info):
            print(f"[{idx + 1}/{len(all_products_info)}] {product_data['name']} ({product_data['product_type']}) 크롤링 중...")
            
            # 기본 상세 정보 크롤링
            detail_info = {}
            rate_info = {
                'basic_rate': {'table_list': [], 'table_count': 0, 'text_info': []},
                'preferential_rate': {'text_info': [], 'table_list': [], 'table_count': 0}
            }
            tax_benefit = ""
            
            if product_data['product_id']:
                # 기본 정보 크롤링
                detail_info = self.crawl_product_detail(product_data['product_id'])
                
                if 'error' not in detail_info:
                    # 금리안내 탭에서 기본금리 + 우대금리 추출
                    rate_info = self.extract_rate_info_from_rate_tab(product_data['product_id'])
                    
                    # 유의사항 탭에서 세제혜택 추출
                    tax_benefit = self.extract_tax_benefit_from_caution_tab(product_data['product_id'])
                
                time.sleep(1)

            # 표준 포맷으로 매핑
            mapped_info = self.map_detail_to_standard_format(detail_info)
            
            # 상품 카테고리 결정
            type = self.determine_product_category(
                product_data['name'], 
                product_data.get('product_badge', '')
            )
            
            # JSON 구조로 구성
            product = {
                # 기본 식별 정보
                "name": product_data["name"],
                "product_idx": str(idx + 1),
                "list_index": idx + 1,
                "scraped_at": datetime.datetime.now().isoformat(),
                "product_code": product_data["product_id"],
                "type": type,
                "detail_type": mapped_info.get('detail_type', ''),
                
                # 금리 정보 (상세 페이지에서 추출한 것 우선 사용)
                "basic_rate": detail_info.get('basic_rate', product_data.get('basic_rate', '')),
                "max_rate": detail_info.get('max_rate', product_data.get('max_rate', '')),
                "url_link": self.get_product_detail_url(product_data["product_id"]),
                
                # 가입 조건 정보
                "sub_amount": mapped_info.get('sub_amount', ''),
                "sub_target": mapped_info.get('sub_target', ''),
                "sub_way": mapped_info.get('sub_way', ''),
                "sub_term": mapped_info.get('sub_term', ''),
                "tax_benefit": tax_benefit,  # 유의사항 탭에서 추출한 세제혜택
                
                # 우대금리 및 기간별 금리
                "preferential_rate": rate_info['preferential_rate'],
                "period_rate": rate_info['basic_rate']  # 기본금리를 period_rate로 사용
            }

            products.append(product)

        return products

    def save_to_json(self, products, filename=None):
        dotenv.load_dotenv()
        directory_path = os.getenv("JSON_RESULT_PATH")

        os.makedirs(directory_path, exist_ok=True)
        """결과를 JSON 파일로 저장"""
        if filename is None:
            filename = f"JEJU.json"

        file_path = os.path.join(directory_path, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        print(f"결과 저장: {filename}")
        return filename


    def start(self):
        try:
            # 예금/적금만 크롤링 (각각 5개씩 테스트)
            products = self.fetch_deposit_and_savings_products(limit_per_type=None)

            print(f"크롤링 완료! 총 {len(products)}개 상품")

            # JSON으로 저장
            filename = self.save_to_json(products)

            return products

        except Exception as e:
            print(e)
            return []
        finally:
            self.driver.quit()



