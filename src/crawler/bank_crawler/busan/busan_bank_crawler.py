import os

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
import logging


class BusanBankUnifiedCrawler:
    # BASE_URL = 'https://www.busanbank.co.kr/ib20/mnu/FPMDPO012009001'

    def __init__(self, headless: bool = True, timeout: int = 15, base_url: str = ""):
        self.headless = headless
        self.timeout = timeout
        self.driver = self._create_driver()
        self.base_url = base_url
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

    def safe_find_text(self, element, selector, default="-"):
        """안전하게 텍스트를 찾는 헬퍼 함수"""
        try:
            return element.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return default

    def determine_product_category(self, Name, product_description=""):
        """상품명과 설명으로 카테고리 결정"""
        text = (Name + " " + product_description).lower()

        if "적금" in text or "savings" in text:
            return "적금"
        elif "예금" in text or "deposit" in text:
            return "예금"
        elif "저축" in text:
            return "입출금자유"
        else:
            return "기타"

    def extract_product_code_from_url(self, url_link):
        """URL에서 상품 코드 추출"""
        if not url_link:
            return ""

        try:
            # FPCD 파라미터에서 상품 코드 추출
            if "FPCD=" in url_link:
                return url_link.split("FPCD=")[1].split("&")[0]
        except:
            pass
        return ""

    def get_product_detail_url(self, item):
        """상품 상세 페이지 URL 추출"""
        try:
            link = item.find_element(By.CSS_SELECTOR, "p.item-thumb-tit a.FPCD_DTL")
            fpcd = link.get_attribute("fpcd")
            acsys_fpcd = link.get_attribute("acsys_fpcd")
            fp_hlv_dvcd = link.get_attribute("fp_hlv_dvcd")

            if fpcd:
                base_detail_url = "https://www.busanbank.co.kr/ib20/mnu/FPMPDTDT0000001"
                params = [f"FPCD={fpcd}"]
                if acsys_fpcd and acsys_fpcd != "0":
                    params.append(f"ACSYS_FPCD={acsys_fpcd}")
                if fp_hlv_dvcd:
                    params.append(f"FP_HLV_DVCD={fp_hlv_dvcd}")

                return f"{base_detail_url}?" + "&".join(params)

        except NoSuchElementException:
            try:
                link = item.find_element(By.CSS_SELECTOR, "a[fpcd]")
                fpcd = link.get_attribute("fpcd")
                if fpcd:
                    return f"https://www.busanbank.co.kr/ib20/mnu/FPMPDTDT0000001?FPCD={fpcd}"
            except:
                pass
        except Exception as e:
            pass

        return ""

    def extract_preferential_rate_info(self, detail_info):
        """우대이율 정보를 광주은행 구조로 추출 - 실제 테이블 내용 파싱"""
        preferential_data = {
            'has_preferential': False,
            'text_info': [],
            'table_list': [],
            'table_count': 0
        }

        try:
            # 우대이율 정보 찾기
            preferential_text = detail_info.get('우대이율', '')

            if preferential_text and preferential_text != '-':
                preferential_data['has_preferential'] = True

                # 텍스트를 줄 단위로 분할
                text_lines = [line.strip() for line in preferential_text.split('\n') if line.strip()]
                preferential_data['text_info'] = text_lines

                # 실제 우대이율 테이블 추출을 위해 다시 페이지에서 찾기
                try:
                    # 우대이율 DT 요소 찾기
                    dt_elements = self.driver.find_elements(By.CSS_SELECTOR, "dt")
                    for dt in dt_elements:
                        if dt.text.strip() == '우대이율':
                            # 해당 DD 요소 찾기
                            dd = dt.find_element(By.XPATH, "following-sibling::dd[1]")

                            # DD 안의 테이블들 찾기
                            tables = dd.find_elements(By.CSS_SELECTOR, "table")

                            for table_idx, table in enumerate(tables):
                                table_data = self.extract_preferential_table_structure(table, table_idx + 1)
                                if table_data:
                                    preferential_data['table_list'].append(table_data)

                            break

                    preferential_data['table_count'] = len(preferential_data['table_list'])

                except Exception as e:
                    # 테이블 추출 실패시 기본 구조만 제공
                    if '%p' in preferential_text:
                        basic_table = {
                            "table_type": "vertical",
                            "headers": ["조건", "우대금리"],
                            "rows": [["우대조건 충족시", "우대금리 적용"]],
                            "table_index": 1
                        }
                        preferential_data['table_list'] = [basic_table]
                        preferential_data['table_count'] = 1

        except Exception as e:
            pass

        return preferential_data

    def extract_preferential_table_structure(self, table_element, table_index):
        """우대이율 테이블의 실제 구조 추출"""
        try:
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            if not rows:
                return None

            table_data = {
                "table_type": "horizontal",
                "headers": [],
                "rows": [],
                "table_index": table_index
            }

            # 첫 번째 행을 헤더로 처리
            if rows:
                header_cells = rows[0].find_elements(By.TAG_NAME, "td") + rows[0].find_elements(By.TAG_NAME, "th")
                headers = []
                for cell in header_cells:
                    text = cell.text.strip()
                    if text:
                        headers.append(text)

                table_data["headers"] = headers

            # 나머지 행들을 데이터로 처리
            for row in rows[1:]:
                cells = row.find_elements(By.TAG_NAME, "td") + row.find_elements(By.TAG_NAME, "th")
                row_data = []
                for cell in cells:
                    text = cell.text.strip()
                    row_data.append(text)

                if any(cell for cell in row_data):
                    table_data["rows"].append(row_data)

            # 유효한 테이블인지 확인
            if table_data["headers"] or table_data["rows"]:
                return table_data

            return None

        except Exception as e:
            return None

    def extract_period_rate_table(self, url_link):
        """금리/이율 탭에서 기간별 금리 테이블 추출 - 수정된 버전"""
        period_rate_data = {
            'table_list': [],
            'table_count': 0,
            'status': 'failed'
        }

        if not url_link:
            return period_rate_data

        try:
            # 현재 창 핸들 저장
            main_window = self.driver.current_window_handle

            # 상세 페이지로 이동 (이미 있다면 스킵)
            current_url = self.driver.current_url
            if url_link not in current_url:
                self.driver.get(url_link)
                time.sleep(3)

            # 금리/이율 탭 찾기 및 클릭
            try:
                # 여러 가능한 선택자로 시도
                rate_tab_selectors = [
                    "//button[contains(text(), '금리/이율')]",
                    "//a[contains(text(), '금리/이율')]",
                    "//li[contains(text(), '금리/이율')]",
                    "//*[contains(@class, 'tab') and contains(text(), '금리/이율')]"
                ]

                rate_tab = None
                for selector in rate_tab_selectors:
                    try:
                        rate_tab = self.driver.find_element(By.XPATH, selector)
                        break
                    except:
                        continue

                if rate_tab:
                    self.driver.execute_script("arguments[0].click();", rate_tab)
                    time.sleep(2)

                    # tbl-type2 테이블만 대상으로 함
                    tables = self.driver.find_elements(By.CSS_SELECTOR, "table.tbl-type2")

                    for i, table in enumerate(tables):
                        try:
                            table_data = self.extract_fixed_rate_table_structure(table)
                            if table_data and len(table_data['rows']) > 0:
                                table_data["table_index"] = i + 1
                                period_rate_data['table_list'].append(table_data)
                        except Exception as e:
                            continue

                    period_rate_data['table_count'] = len(period_rate_data['table_list'])
                    period_rate_data['status'] = 'success' if period_rate_data['table_list'] else 'no_maturity_tables'

                else:
                    period_rate_data['status'] = 'tab_not_found'

            except Exception as e:
                period_rate_data['status'] = 'tab_error'

        except Exception as e:
            period_rate_data['error'] = str(e)

        return period_rate_data

    def extract_fixed_rate_table_structure(self, table_element):
        """범용적인 금리 테이블 구조 추출 - 상품별 다양한 행 수 대응"""
        try:
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            if not rows:
                return None

            table_data = {
                "headers": [],
                "rows": []
            }

            # 헤더 추출 (첫 번째 행)
            if rows:
                header_cells = rows[0].find_elements(By.TAG_NAME, "th") + rows[0].find_elements(By.TAG_NAME, "td")
                headers = [cell.text.strip() for cell in header_cells]
                table_data["headers"] = headers

            # 만기지급 관련 행들 추출 - 범용적 접근
            maturity_rows = []
            maturity_section_found = False
            maturity_rowspan = 0
            maturity_start_row = -1

            for row_idx in range(1, len(rows)):
                row = rows[row_idx]
                cells = row.find_elements(By.TAG_NAME, "th") + row.find_elements(By.TAG_NAME, "td")

                if not cells:
                    continue

                # 모든 셀의 텍스트 추출
                cell_texts = [cell.text.strip() for cell in cells]
                first_cell_text = cell_texts[0] if cell_texts else ""

                # 만기지급 섹션 시작 감지
                if first_cell_text == "만기지급" and not maturity_section_found:
                    maturity_section_found = True
                    maturity_start_row = row_idx

                    # rowspan 속성 확인으로 섹션 범위 계산
                    try:
                        first_cell = cells[0]
                        rowspan_attr = first_cell.get_attribute('rowspan')
                        if rowspan_attr and rowspan_attr.isdigit():
                            maturity_rowspan = int(rowspan_attr)
                        else:
                            maturity_rowspan = 1
                    except:
                        maturity_rowspan = 1

                    maturity_rows.append(cell_texts)
                    continue

                # 만기지급 섹션 내의 행들 처리
                if maturity_section_found:
                    # rowspan 기반으로 섹션 범위 확인
                    if maturity_rowspan > 1:
                        # rowspan 범위 내인지 확인
                        if row_idx < maturity_start_row + maturity_rowspan:
                            # 4개 셀인 경우 (rowspan으로 인해 첫 번째 컬럼이 생략됨)
                            if len(cell_texts) == 4:
                                # 만기지급 rowspan 범위 내의 모든 행은 만기지급에 속함
                                # 앞에 "만기지급" 추가하여 5개 컬럼으로 맞춤
                                adjusted_row = ["만기지급"] + cell_texts
                                maturity_rows.append(adjusted_row)
                                continue
                        else:
                            # rowspan 범위를 벗어나면 만기지급 섹션 종료
                            break

                    # rowspan이 없거나 1인 경우, 다른 섹션이 시작되면 종료
                    elif first_cell_text and first_cell_text not in ["", "만기지급"]:
                        # 다른 섹션(만기후, 중도해지 등)이 시작되면 종료
                        other_sections = ["만기후", "만기 후", "중도해지", "중도 해지", "월이자지급", "분기지급"]
                        if any(section in first_cell_text for section in other_sections):
                            break

            table_data["rows"] = maturity_rows

            return table_data if maturity_rows else None

        except Exception as e:
            return None

    def is_valid_rate_table(self, table_data):
        """유효한 금리 테이블인지 확인"""
        if not table_data:
            return False

        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        all_text = " ".join(headers + [str(cell) for row in rows for cell in row])

        # 금리 관련 키워드 확인
        rate_keywords = ["금리", "이율", "%", "기간", "개월", "만기"]
        has_rate_keyword = any(keyword in all_text for keyword in rate_keywords)

        # "만기지급" 부분만 필터링 (요구사항)
        has_maturity = "만기" in all_text

        return has_rate_keyword and has_maturity and len(rows) > 0

    def crawl_product_detail(self, url_link):
        """상품 상세 정보 크롤링 - DT-DD 구조 정확히 파싱"""
        if not url_link:
            return {}

        try:
            self.driver.get(url_link)
            time.sleep(3)

            detail_info = {}

            # 상품명 추출
            detail_info['detail_title'] = self.safe_find_text(self.driver, ".item-detail-tit")

            # DT-DD 구조에서 정보 추출 (개별 DT 요소별로)
            dt_elements = self.driver.find_elements(By.CSS_SELECTOR, "dt")

            for dt in dt_elements:
                try:
                    key = dt.text.strip()

                    # 필요없는 항목 제외
                    if key in ['바로가기', '자주쓰는메뉴', '스킨설정', '상품평점', '최고금리', '상품개요', '상품특징']:
                        continue

                    # 다음 형제 요소(DD) 찾기
                    dd = dt.find_element(By.XPATH, "following-sibling::dd[1]")

                    if dd and key:
                        # DD 내용 추출 (HTML 태그 제거하고 텍스트만)
                        value = dd.text.strip()

                        if value and len(key) < 50:
                            detail_info[key] = value

                except Exception as e:
                    continue

            return detail_info

        except Exception as e:
            return {'error': f"Failed to crawl detail: {str(e)}"}

    def map_detail_to_standard_format(self, detail_info):
        """상세 정보를 표준 포맷으로 매핑 - 변수명 수정 버전"""
        # 부산은행 필드명을 새로운 변수명으로 매핑
        field_mapping = {
            '가입자격': 'sub_target',
            '가입대상': 'sub_target',  # 가입자격과 동일한 의미
            '가입기간': 'sub_term',
            '가입금액': 'sub_amount',
            '가입방법': 'sub_way',
            '세제혜택': 'tax_benefit',
            '예금과목': 'detail_type'  # product_type -> detail_type
        }

        mapped_data = {}
        for busan_field, standard_field in field_mapping.items():
            if busan_field in detail_info:
                value = detail_info[busan_field]
                mapped_data[standard_field] = value

        # 가입자격과 가입대상이 모두 있는 경우, 더 상세한 것을 사용
        if '가입자격' in detail_info and '가입대상' in detail_info:
            target_text = detail_info['가입자격']
            subject_text = detail_info['가입대상']

            # 더 긴 설명을 선택
            if len(target_text) > len(subject_text):
                mapped_data['sub_target'] = target_text
            else:
                mapped_data['sub_target'] = subject_text

        return mapped_data

    def filter_deposit_savings_only(self, products):
        """예금과 적금만 필터링"""
        filtered = [product for product in products
                    if product['type'] in ['예금', '적금']]  # product_category -> type

        excluded_count = len(products) - len(filtered)
        if excluded_count > 0:
            self.logger.info(f"입출금자유/기타 상품 {excluded_count}개 제외됨")

        return filtered

    def fetch_products_with_unified_structure(self, limit=999):
        """통합 구조로 상품 정보 크롤링"""

        driver = self.driver
        driver.get(self.base_url)

        wait = WebDriverWait(driver, self.timeout)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.paginate")))

        # 페이지 수 확인
        paging = driver.find_element(By.CSS_SELECTOR, "div.paginate")
        page_links = paging.find_elements(By.CSS_SELECTOR, "a")
        last_page = max(int(a.text) for a in page_links if a.text.isdigit())

        products = []

        # 모든 상품의 기본 정보 수집 (제한 적용)
        all_product_data = []

        for page in range(1, last_page + 1):
            # 목표 개수에 도달하면 중단
            if len(all_product_data) >= limit:
                break

            if page > 1:
                driver.get(self.base_url)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.paginate")))

                for _ in range(page - 1):
                    try:
                        paging = driver.find_element(By.CSS_SELECTOR, "div.paginate")
                        next_btn = paging.find_element(
                            By.CSS_SELECTOR,
                            f"a[href=\"javascript:ibsGoPage({page});\"]"
                        )
                        next_btn.click()
                        wait.until(EC.text_to_be_present_in_element(
                            (By.CSS_SELECTOR, "div.paginate strong"), str(page)
                        ))
                        break
                    except:
                        time.sleep(1)
                        continue

            wait.until(EC.presence_of_all_elements_located((
                By.CSS_SELECTOR,
                "div.item-type-list.ty_logo.ty_rate ul > li.clearfix"
            )))

            items = driver.find_elements(
                By.CSS_SELECTOR,
                "div.item-type-list.ty_logo.ty_rate ul > li.clearfix"
            )

            for idx, item in enumerate(items):
                # 목표 개수에 도달하면 중단
                if len(all_product_data) >= limit:
                    break

                try:
                    # 기본 정보 추출
                    Name = self.safe_find_text(item, "p.item-thumb-tit a")  # prod_title -> Name
                    desc = self.safe_find_text(item, "div.item-info > div.desc")
                    prod_description = desc.replace("\n", " ").strip()

                    # 금리 정보
                    basic_rate = self.safe_find_text(
                        item, "div.tag > span.rate_default > strong"
                    ).rstrip(",")

                    max_rate = self.safe_find_text(item, "div.tag > strong")

                    # 상세 URL
                    url_link = self.get_product_detail_url(item)  # detail_url -> url_link

                    product_data = {
                        "Name": Name,  # product_name -> Name
                        "basic_rate": basic_rate,
                        "max_rate": max_rate,
                        "url_link": url_link,  # detail_url -> url_link
                        "product_description": prod_description,
                        "page": page,
                        "index": idx
                    }

                    all_product_data.append(product_data)

                except Exception as e:
                    continue

        # 각 상품의 완전한 정보 구성
        for idx, product_data in enumerate(all_product_data):
            self.logger.info(f"[{idx + 1}/{len(all_product_data)}] {product_data['Name']} 크롤링 중...")

            # 상세 정보 크롤링
            detail_info = {}
            preferential_rate = {
                'has_preferential': False,
                'text_info': [],
                'table_list': [],
                'table_count': 0
            }
            period_rate = {
                'table_list': [],
                'table_count': 0,
                'status': 'failed'
            }

            if product_data['url_link']:
                detail_info = self.crawl_product_detail(product_data['url_link'])

                # 우대이율 정보 추출 (웹 페이지에서 직접)
                if 'error' not in detail_info:
                    preferential_rate = self.extract_preferential_rate_info(detail_info)

                    # 기간별 금리 테이블 추출
                    period_rate = self.extract_period_rate_table(product_data['url_link'])

                time.sleep(1)

            # 표준 포맷으로 매핑
            mapped_info = self.map_detail_to_standard_format(detail_info)

            # 상품 카테고리 결정
            type = self.determine_product_category(  # product_category -> type
                product_data['Name'],
                product_data.get('product_description', '')
            )

            # 상품 코드 추출
            product_code = self.extract_product_code_from_url(product_data['url_link'])

            # 새로운 변수명으로 JSON 구조 구성
            product = {
                # 기본 식별 정보
                "Name": product_data["Name"],  # product_name -> Name
                "product_idx": str(idx + 1),
                "list_index": idx + 1,
                "scraped_at": datetime.datetime.now().isoformat(),
                "product_code": product_code,
                "type": type,  # product_category -> type
                "detail_type": mapped_info.get('detail_type', ''),  # product_type -> detail_type

                # 금리 정보
                "basic_rate": product_data["basic_rate"],
                "max_rate": product_data["max_rate"],
                "url_link": product_data["url_link"],  # detail_url -> url_link

                # 가입 조건 정보
                "sub_amount": mapped_info.get('sub_amount', ''),  # join_amount -> sub_amount
                "sub_target": mapped_info.get('sub_target', ''),  # join_target -> sub_target
                "sub_way": mapped_info.get('sub_way', ''),  # join_method -> sub_way
                "sub_term": mapped_info.get('sub_term', ''),  # join_period -> sub_term
                "tax_benefit": mapped_info.get('tax_benefit', ''),

                # 우대금리 및 기간별 금리
                "preferential_rate": preferential_rate,
                "period_rate": period_rate,
                "rate_url": product_data["url_link"]  # 동일한 URL
            }

            products.append(product)

        driver.quit()
        return products

    def save_to_json(self, products, filename=None):
        dotenv.load_dotenv()
        directory_path = os.getenv("JSON_RESULT_PATH")

        os.makedirs(directory_path, exist_ok=True)

        if filename is None:
            filename = f"BNK_BUSAN.json"

        file_path = os.path.join(directory_path, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        return file_path

    # def save_to_json(self, products, filename=None):
    #     dotenv.load_dotenv()
    #
    #     directory_path = os.getenv("JSON_RESULT_PATH")
    #
    #     """결과를 JSON 파일로 저장"""
    #     if filename is None:
    #         current_date = datetime.datetime.now().strftime("%Y%m%d")
    #         filename = f"busan_bank_products_{current_date}.json"
    #
    #     with open(filename, 'w', encoding='utf-8') as f:
    #         json.dump(products, f, ensure_ascii=False, indent=2)
    #
    #     return filename

    def start(self):
        try:
            all_products = self.fetch_products_with_unified_structure(limit=999)

            # 예금과 적금만 필터링
            products = self.filter_deposit_savings_only(all_products)

            self.logger.info(f"크롤링 완료! 전체 {len(all_products)}개 중 예금/적금 {len(products)}개 상품")

            # 필터링된 결과만 저장
            filename = self.save_to_json(products)
            self.logger.info(f"결과 저장: {filename}")

            # 결과 요약 출력
            self.logger.info("\n=== 결과 요약 ===")
            category_count = {}

            for product in products:
                category = product['type']  # product_category -> type
                category_count[category] = category_count.get(category, 0) + 1

            for category, count in category_count.items():
                self.logger.info(f"{category}: {count}개")

            return products

        except Exception as e:
            self.logger.info(f"크롤링 오류: {e}")
            return []

