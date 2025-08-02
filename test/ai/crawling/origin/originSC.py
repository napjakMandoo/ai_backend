from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import re
import datetime
from typing import List, Dict, Optional


class SCBankCleanCrawler:
    """SC제일은행 크롤러 - 로그 정리 및 불필요 필드 제거 버전"""

    BASE_URL = "https://www.standardchartered.co.kr/np/kr/pl/se/SavingList.jsp?id=list1"
    DETAIL_URL_BASE = "https://www.standardchartered.co.kr/np/kr/pl/se/SavingDetail.jsp"

    def __init__(self, headless: bool = True, timeout: int = 15):
        self.headless = headless
        self.timeout = timeout
        self.driver = self._create_driver()
        self.wait = WebDriverWait(self.driver, timeout)

    def _create_driver(self):
        """Chrome 드라이버 생성"""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        return webdriver.Chrome(options=options)

    def click_tab_by_name(self, tab_name: str) -> bool:
        """탭 이름으로 클릭"""
        try:
            if tab_name == "목돈모으기":
                tab_selector = "ul.tab_btns li:nth-child(4) a"
            elif tab_name == "목돈굴리기":
                tab_selector = "ul.tab_btns li:nth-child(5) a"
            else:
                return False

            tab_element = self.driver.find_element(By.CSS_SELECTOR, tab_selector)
            self.driver.execute_script("arguments[0].click();", tab_element)
            time.sleep(3)
            return True

        except Exception:
            return False

    def extract_product_links_from_current_page(self) -> List[Dict]:
        """현재 페이지의 상품 링크 추출"""
        products = []

        try:
            # 1. .top_class 컨테이너들 확인
            top_containers = self.driver.find_elements(By.CSS_SELECTOR, ".top_class")

            for container in top_containers:
                try:
                    links = container.find_elements(By.CSS_SELECTOR, 'a[href*="SavingDetail"]')

                    for link in links:
                        href = link.get_attribute('href')
                        Name = link.text.strip()

                        if not Name or Name in ["상세보기", "자세히보기", "더보기"]:
                            continue

                        id_match = re.search(r'id=(\d+)', href)
                        if not id_match:
                            continue
                        product_id = id_match.group(1)

                        # 금리 정보 추출
                        container_text = container.text
                        basic_rate = ""
                        max_rate = ""

                        rate_match = re.search(r'최고\s*([\d.]+%),?\s*최저\s*([\d.]+%)', container_text)
                        if rate_match:
                            max_rate = rate_match.group(1)
                            basic_rate = rate_match.group(2)
                        else:
                            max_only_match = re.search(r'최고\s*([\d.]+%)', container_text)
                            if max_only_match:
                                max_rate = max_only_match.group(1)

                            min_only_match = re.search(r'최저\s*([\d.]+%)', container_text)
                            if min_only_match:
                                basic_rate = min_only_match.group(1)

                        products.append({
                            'product_id': product_id,
                            'Name': Name,
                            'basic_rate': basic_rate,
                            'max_rate': max_rate,
                            'url_link': href
                        })
                        break

                except Exception:
                    continue

            # 2. product_ranking 컨테이너에서 누락된 상품들 추가
            try:
                ranking_container = self.driver.find_element(By.CSS_SELECTOR, ".product_ranking")
                ranking_links = ranking_container.find_elements(By.CSS_SELECTOR, 'a[href*="SavingDetail"]')

                existing_ids = {p['product_id'] for p in products}

                for link in ranking_links:
                    href = link.get_attribute('href')
                    Name = link.text.strip()

                    if not Name or Name in ["상세보기", "자세히보기", "더보기"]:
                        continue

                    id_match = re.search(r'id=(\d+)', href)
                    if not id_match:
                        continue
                    product_id = id_match.group(1)

                    if product_id in existing_ids:
                        continue

                    basic_rate = ""
                    max_rate = ""

                    try:
                        current = link
                        for level in range(4):
                            current = current.find_element(By.XPATH, "..")
                            if current.tag_name.lower() == 'li':
                                li_text = current.text
                                rate_match = re.search(r'최고\s*([\d.]+%),?\s*최저\s*([\d.]+%)', li_text)
                                if rate_match:
                                    max_rate = rate_match.group(1)
                                    basic_rate = rate_match.group(2)
                                    break
                    except:
                        pass

                    products.append({
                        'product_id': product_id,
                        'Name': Name,
                        'basic_rate': basic_rate,
                        'max_rate': max_rate,
                        'url_link': href
                    })

            except Exception:
                pass

        except Exception:
            pass

        return products

    def extract_pattern_a_info(self) -> Dict[str, str]:
        """패턴 A: SC행복적금"""
        info = {
            'sub_target': '',
            'sub_amount': '',
            'sub_term': ''
        }

        try:
            h3_elements = self.driver.find_elements(By.CSS_SELECTOR, "h3.title3")

            for h3 in h3_elements:
                h3_text = h3.text.strip()

                if h3_text.startswith("가입대상") and ":" in h3_text:
                    base_target = h3_text.split(":", 1)[1].strip()

                    details = []
                    try:
                        ul_elements = h3.find_elements(By.XPATH, "following-sibling::ul[position()<=2]")
                        for ul in ul_elements:
                            ul_items = ul.find_elements(By.TAG_NAME, "li")
                            ul_texts = [li.text.strip() for li in ul_items if li.text.strip()]
                            details.extend(ul_texts)
                    except:
                        pass

                    if details:
                        info['sub_target'] = f"{base_target} ({', '.join(details)})"
                    else:
                        info['sub_target'] = base_target

                elif h3_text.startswith("저축금액") and ":" in h3_text:
                    info['sub_amount'] = h3_text.split(":", 1)[1].strip()

                elif h3_text.startswith("가입기간"):
                    try:
                        next_p = h3.find_element(By.XPATH, "following-sibling::p[1]")
                        info['sub_term'] = next_p.text.strip()
                    except:
                        pass

        except Exception:
            pass

        return info

    def extract_pattern_b_info(self) -> Dict[str, str]:
        """패턴 B: 퍼스트가계적금"""
        info = {
            'sub_target': '',
            'sub_amount': '',
            'sub_term': ''
        }

        try:
            product_info_h3 = None
            h3_elements = self.driver.find_elements(By.CSS_SELECTOR, "h3.title3")

            for h3 in h3_elements:
                if "상품안내" in h3.text:
                    product_info_h3 = h3
                    break

            if not product_info_h3:
                return info

            try:
                content_div = product_info_h3.find_element(By.XPATH,
                                                           "following-sibling::div[contains(@class, 'goodsViw_cont')][1]")
                all_lis = content_div.find_elements(By.CSS_SELECTOR, "li")

                for li in all_lis:
                    li_text = li.text.strip()
                    li_class = li.get_attribute('class')

                    if li_text.startswith("가입대상") and "li_bks" in li_class:
                        info['sub_target'] = self._extract_colon_value(li_text)

                    elif any(li_text.startswith(prefix) for prefix in
                             ["가입금액", "예치금액", "적립금액", "가입한도"]) and "li_bks" in li_class:
                        if not info['sub_amount']:
                            info['sub_amount'] = self._extract_colon_value(li_text)

                    elif li_text.startswith("계약기간") and "li_bk" in li_class:
                        period_details = []
                        try:
                            parent_ul = li.find_element(By.XPATH, "..")
                            all_siblings = parent_ul.find_elements(By.TAG_NAME, "li")

                            collect_next = False
                            for sibling in all_siblings:
                                if sibling == li:
                                    collect_next = True
                                    continue
                                if collect_next and "cont_hp" in sibling.get_attribute('class'):
                                    sibling_text = sibling.text.strip()
                                    if sibling_text and ("정기적립식" in sibling_text or "자유적립식" in sibling_text):
                                        period_details.append(sibling_text)
                                elif collect_next and "li_bk" in sibling.get_attribute('class'):
                                    break
                        except:
                            pass

                        if period_details:
                            info['sub_term'] = '; '.join(period_details)
                        else:
                            info['sub_term'] = self._extract_colon_value(li_text)

                    elif li_text.startswith("가입기간") and "li_bks" in li_class:
                        period_text = self._extract_colon_value(li_text)
                        if period_text:
                            info['sub_term'] = period_text

            except Exception:
                pass

        except Exception:
            pass

        return info

    def extract_pattern_c_info(self) -> Dict[str, str]:
        """패턴 C: 두드림적금"""
        info = {
            'sub_target': '',
            'sub_amount': '',
            'sub_term': ''
        }

        try:
            h3_elements = self.driver.find_elements(By.CSS_SELECTOR, "h3.title3")

            for h3 in h3_elements:
                h3_text = h3.text.strip()

                if h3_text == "가입대상":
                    try:
                        next_p = h3.find_element(By.XPATH, "following-sibling::p[1]")
                        info['sub_target'] = next_p.text.strip()
                    except:
                        pass

                elif h3_text == "가입금액":
                    try:
                        next_p = h3.find_element(By.XPATH, "following-sibling::p[1]")
                        info['sub_amount'] = next_p.text.strip()
                    except:
                        pass

                elif h3_text == "가입기간":
                    try:
                        next_p = h3.find_element(By.XPATH, "following-sibling::p[1]")
                        info['sub_term'] = next_p.text.strip()
                    except:
                        pass

        except Exception:
            pass

        return info

    def _extract_colon_value(self, text: str) -> str:
        """':'으로 분리된 값 추출"""
        if ":" in text:
            return text.split(":", 1)[1].strip()
        return text

    def detect_pattern_and_extract_info(self) -> Dict[str, str]:
        """패턴을 자동 감지하고 정보 추출"""
        try:
            h3_elements = self.driver.find_elements(By.CSS_SELECTOR, "h3.title3")

            for h3 in h3_elements:
                h3_text = h3.text.strip()
                if (h3_text.startswith("가입대상") or h3_text.startswith("저축금액")) and ":" in h3_text:
                    return self.extract_pattern_a_info()

            for h3 in h3_elements:
                if "상품안내" in h3.text:
                    return self.extract_pattern_b_info()

            return self.extract_pattern_c_info()

        except Exception:
            return {
                'sub_target': '',
                'sub_amount': '',
                'sub_term': ''
            }

    def extract_preferential_rate_info(self) -> Dict:
        """우대이율 정보 추출"""
        preferential_data = {
            'text_info': [],
            'table_list': [],
            'table_count': 0
        }

        try:
            h3_elements = self.driver.find_elements(By.CSS_SELECTOR, "h3.title3")

            for h3 in h3_elements:
                h3_text = h3.text.strip()

                if "우대이율" in h3_text or "우대금리" in h3_text:
                    preferential_data['text_info'].append(h3_text)

                    # SC행복적금 패턴
                    if ":" in h3_text and "최대 우대 이율 합계" in h3_text:
                        try:
                            next_ul = h3.find_element(By.XPATH, "following-sibling::ul[1]")
                            ul_items = next_ul.find_elements(By.TAG_NAME, "li")
                            for li in ul_items:
                                li_text = li.text.strip()
                                if li_text and li_text not in preferential_data['text_info']:
                                    preferential_data['text_info'].append(li_text)
                        except Exception:
                            pass

                    # 두드림적금 패턴
                    elif "최대 우대 금리 합계" in h3_text:
                        try:
                            next_table = h3.find_element(By.XPATH, "following-sibling::table[1]")
                            if next_table and "table_type_2" in next_table.get_attribute("class"):
                                table_data = self.extract_table_data(next_table)
                                if table_data:
                                    preferential_data['table_list'].append({
                                        "headers": table_data[0] if table_data else [],
                                        "rows": table_data[1:] if len(table_data) > 1 else []
                                    })
                        except Exception:
                            pass

                        try:
                            next_div = h3.find_element(By.XPATH,
                                                       "following-sibling::div[contains(@class, 'goodsViw_cont')][1]")
                            if next_div:
                                div_text = next_div.text.strip()
                                if div_text:
                                    lines = [line.strip() for line in div_text.split('\n') if line.strip()]
                                    for line in lines:
                                        if line and line not in preferential_data['text_info']:
                                            preferential_data['text_info'].append(line)
                        except Exception:
                            pass

                    # 기타 패턴
                    elif h3_text == "우대이율":
                        try:
                            next_div = h3.find_element(By.XPATH,
                                                       "following-sibling::div[contains(@class, 'goodsViw_cont')][1]")
                            if next_div:
                                div_text = next_div.text.strip()
                                if div_text:
                                    lines = [line.strip() for line in div_text.split('\n') if line.strip()]
                                    preferential_data['text_info'].extend(lines)
                        except:
                            pass

                    preferential_data['table_count'] = len(preferential_data['table_list'])
                    break

        except Exception:
            pass

        return preferential_data

    def extract_tax_benefit_info(self) -> str:
        """세제혜택 정보 추출"""
        try:
            h3_elements = self.driver.find_elements(By.CSS_SELECTOR, "h3.title3")

            for h3 in h3_elements:
                h3_text = h3.text.strip()

                if "비과세" in h3_text:
                    if "가입불가" in h3_text:
                        try:
                            next_div = h3.find_element(By.XPATH,
                                                       "following-sibling::div[contains(@class, 'goodsViw_cont')][1]")
                            if next_div:
                                div_text = next_div.text.strip()
                                if div_text and "비과세" in div_text:
                                    return f"{h3_text} {div_text}"
                        except:
                            pass
                        return h3_text

                    elif h3_text == "비과세종합저축":
                        # SC행복적금: H3 다음 P 요소
                        try:
                            next_p = h3.find_element(By.XPATH, "following-sibling::p[1]")
                            if next_p:
                                p_text = next_p.text.strip()
                                if p_text and "비과세" in p_text:
                                    return p_text
                        except:
                            pass

                        # 퍼스트가계적금: H3 다음 DIV 내 P 요소
                        try:
                            next_div = h3.find_element(By.XPATH,
                                                       "following-sibling::div[contains(@class, 'goodsViw_cont')][1]")
                            if next_div:
                                p_elements = next_div.find_elements(By.TAG_NAME, "p")
                                for p in p_elements:
                                    p_text = p.text.strip()
                                    if p_text and "비과세" in p_text:
                                        return p_text

                                div_text = next_div.text.strip()
                                if div_text and "비과세" in div_text:
                                    return div_text
                        except:
                            pass

                        # 두드림적금: H3 다음 UL
                        try:
                            next_ul = h3.find_element(By.XPATH, "following-sibling::ul[1]")
                            if next_ul:
                                li_elements = next_ul.find_elements(By.TAG_NAME, "li")
                                for li in li_elements:
                                    li_text = li.text.strip()
                                    if li_text and "비과세" in li_text:
                                        return li_text
                        except:
                            pass

                    else:
                        try:
                            next_p = h3.find_element(By.XPATH, "following-sibling::p[1]")
                            tax_text = next_p.text.strip()
                            if tax_text and "비과세" in tax_text:
                                return tax_text
                        except:
                            try:
                                next_div = h3.find_element(By.XPATH,
                                                           "following-sibling::div[contains(@class, 'goodsViw_cont')][1]")
                                if next_div:
                                    div_text = next_div.text.strip()
                                    if div_text and "비과세" in div_text:
                                        return div_text
                            except:
                                try:
                                    next_ul = h3.find_element(By.XPATH, "following-sibling::ul[1]")
                                    ul_items = next_ul.find_elements(By.TAG_NAME, "li")
                                    for li in ul_items:
                                        li_text = li.text.strip()
                                        if li_text and "비과세" in li_text:
                                            return li_text
                                except:
                                    pass

                    return h3_text

            return ""

        except Exception:
            return ""

    def extract_table_data(self, table_element) -> List[List[str]]:
        """테이블 데이터를 2차원 리스트로 추출"""
        try:
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            table_data = []

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "th") + row.find_elements(By.TAG_NAME, "td")
                row_data = [cell.text.strip() for cell in cells]
                if any(row_data):
                    table_data.append(row_data)

            return table_data
        except:
            return []

    def extract_rate_tables_from_rate_tab(self) -> List[Dict]:
        """금리 탭에서 약정이율표 추출"""
        rate_tables = []

        try:
            tabs = self.driver.find_elements(By.CSS_SELECTOR, '.tab_btns a')
            rate_tab = None

            for tab in tabs:
                if "금리" in tab.text:
                    rate_tab = tab
                    break

            if not rate_tab:
                return rate_tables

            self.driver.execute_script("arguments[0].click();", rate_tab)
            time.sleep(2)

            tables = self.driver.find_elements(By.TAG_NAME, "table")

            for i, table in enumerate(tables):
                try:
                    table_text = table.text.lower()

                    # 제외 대상 테이블
                    if any(keyword in table_text for keyword in ["중도해지", "만기후", "세율", "소득세", "지방소득세"]):
                        continue

                    # 약정이율표 키워드 확인
                    rate_keywords = ["약정", "기본금리", "최고금리", "적용금리", "연이율"]
                    has_rate_keyword = any(keyword in table_text for keyword in rate_keywords)
                    has_percentage = "%" in table_text

                    if has_rate_keyword and has_percentage:
                        table_data = self.extract_table_data(table)
                        if table_data and len(table_data) > 1:
                            rate_tables.append({
                                "headers": table_data[0],
                                "rows": table_data[1:]
                            })

                except Exception:
                    continue

        except Exception:
            pass

        return rate_tables

    def extract_product_detail(self, product_id: str, Name: str) -> Dict:
        """상품 상세 정보 추출"""
        url_link = f"{self.DETAIL_URL_BASE}?id={product_id}"

        try:
            self.driver.get(url_link)
            time.sleep(3)

            detail_info = {
                'Name': Name,
                'scraped_at': datetime.datetime.now().isoformat(),
                'product_code': product_id,
                'type': '',
                'basic_rate': '',
                'max_rate': '',
                'url_link': url_link,
                'sub_amount': '',
                'sub_target': '',
                'sub_term': '',
                'tax_benefit': '',
                'preferential_rate': {
                    'text_info': [],
                    'table_list': [],
                    'table_count': 0
                },
                'period_rate': {
                    'table_list': [],
                    'table_count': 0
                }
            }

            # 기본 정보 추출
            basic_info = self.detect_pattern_and_extract_info()
            for key, value in basic_info.items():
                if value:
                    detail_info[key] = value

            # 우대이율 정보 추출
            detail_info['preferential_rate'] = self.extract_preferential_rate_info()

            # 세제혜택 정보 추출
            tax_benefit = self.extract_tax_benefit_info()
            detail_info['tax_benefit'] = tax_benefit

            # 약정이율표 추출
            rate_tables = self.extract_rate_tables_from_rate_tab()
            detail_info['period_rate']['table_list'] = rate_tables
            detail_info['period_rate']['table_count'] = len(rate_tables)

            return detail_info

        except Exception as e:
            return {
                'Name': Name,
                'product_code': product_id,
                'url_link': url_link,
                'error': str(e)
            }

    def crawl_tab_products(self, tab_name: str, limit: int = None) -> List[Dict]:
        """특정 탭의 상품들 크롤링"""
        print(f"=== {tab_name} 크롤링 시작 ===")

        self.driver.get(self.BASE_URL)
        time.sleep(3)

        if not self.click_tab_by_name(tab_name):
            print(f"'{tab_name}' 탭 클릭 실패")
            return []

        product_links = self.extract_product_links_from_current_page()

        if limit:
            product_links = product_links[:limit]

        print(f"{tab_name}에서 {len(product_links)}개 상품 발견")

        products = []
        for i, product in enumerate(product_links):
            print(f"[{i + 1}/{len(product_links)}] {product['Name']} 크롤링 중...")

            detail_info = self.extract_product_detail(product['product_id'], product['Name'])

            if 'error' not in detail_info:
                detail_info['basic_rate'] = product.get('basic_rate', '') or detail_info.get('basic_rate', '')
                detail_info['max_rate'] = product.get('max_rate', '') or detail_info.get('max_rate', '')

                # 금리 정보가 없는 경우 약정이율표에서 추출
                if not detail_info['basic_rate'] and not detail_info['max_rate']:
                    rate_tables = detail_info.get('period_rate', {}).get('table_list', [])
                    if rate_tables:
                        for table in rate_tables:
                            rows = table.get('rows', [])
                            if rows:
                                rates = []
                                for row in rows:
                                    if len(row) > 2:
                                        rate_text = row[2]
                                        if rate_text and rate_text.replace('.', '').isdigit():
                                            rates.append(float(rate_text))

                                if rates:
                                    min_rate = min(rates)
                                    max_rate = max(rates)
                                    detail_info['basic_rate'] = f"{min_rate}%"
                                    detail_info['max_rate'] = f"{max_rate}%"
                                    break

                detail_info['type'] = '적금' if tab_name == '목돈모으기' else '예금'

            products.append(detail_info)
            time.sleep(1)

        return products

    def crawl_all_products(self, limit_per_tab: int = None) -> List[Dict]:
        """모든 탭의 상품 크롤링"""
        all_products = []

        tabs_to_crawl = ['목돈모으기', '목돈굴리기']

        for tab_name in tabs_to_crawl:
            try:
                products = self.crawl_tab_products(tab_name, limit=limit_per_tab)
                all_products.extend(products)  # 리스트에 직접 추가
                print(f"{tab_name}: {len(products)}개 상품 완료")
            except Exception as e:
                print(f"{tab_name} 탭 크롤링 실패: {e}")

        return all_products

    def save_to_json(self, data: List[Dict], filename: str = None) -> str:
        """결과를 JSON 파일로 저장 - 날짜 기반 파일명"""
        if filename is None:
            # 현재 날짜로 파일명 생성 (YYYY-MM-DD 형식)
            current_date = datetime.datetime.now().strftime("%Y%m%d")
            filename = f"sc_bank_products_{current_date}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"결과 저장: {filename}")
        return filename

    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()

def main():
    """메인 실행 함수"""
    print("SC제일은행 예/적금 크롤링 시작...")

    crawler = SCBankCleanCrawler(headless=True)

    try:
        # 모든 상품 크롤링
        all_products = crawler.crawl_all_products()

        # 결과 출력
        total_products = len(all_products)
        print(f"\n=== 크롤링 완료 ===")
        print(f"총 {total_products}개 상품 수집")

        # 카테고리별 개수 출력
        deposit_count = sum(1 for p in all_products if p.get('type') == '예금')
        savings_count = sum(1 for p in all_products if p.get('type') == '적금')
        print(f"예금: {deposit_count}개, 적금: {savings_count}개")

        # JSON 저장
        filename = crawler.save_to_json(all_products)

        return all_products

    except Exception as e:
        print(f"크롤링 오류: {e}")
        return {}
    finally:
        crawler.close()

if __name__ == "__main__":
    results = main()