import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
import datetime
import logging
import re

class KJBankCompleteCrawler:
    def __init__(self, headless=True):
        """광주은행 크롤러 - 다중헤더 테이블 처리 포함 최종버전"""
        self.base_url = "https://www.kjbank.com"
        self.deposit_list_url = "https://www.kjbank.com/ib20/mnu/FPMDPTR030000"
        
        # Selenium 설정
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
        # 로깅 설정 - 간결하게
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s: %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def determine_product_category(self, product_name, menu_id=""):
        """상품 카테고리 결정 - 예금/적금만 인식"""
        text = product_name.lower()
        
        # menu_id 기반 분류 (우선순위)
        if menu_id == "ITRIRIF010100":
            return "적금"
        elif menu_id == "ITRIRIF010200":
            return "예금"
        elif menu_id == "ITRIRIF010300":
            return "기타"  # 입출금자유 -> 기타로 변경
        
        # 상품명 기반 분류
        if "적금" in text:
            return "적금"
        elif "예금" in text:
            return "예금"
        else:
            return "기타"  # 저축, 통장 등은 모두 기타로 분류

    def filter_deposit_savings_only(self, products):
        """예금과 적금만 필터링"""
        filtered = [product for product in products 
                    if product.get('type') in ['예금', '적금']]
        
        return filtered

    def detect_multi_header_table(self, table_element):
        """다중헤더 테이블 감지 (광주은행 특화)"""
        try:
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            if len(rows) < 2:
                return False
            
            # 첫 번째 행에서 colspan 또는 rowspan 확인
            first_row_cells = rows[0].find_elements(By.TAG_NAME, "th") + rows[0].find_elements(By.TAG_NAME, "td")
            
            has_multi_span = False
            
            for cell in first_row_cells:
                colspan = cell.get_attribute('colspan')
                rowspan = cell.get_attribute('rowspan')
                
                if (colspan and int(colspan) > 1) or (rowspan and int(rowspan) > 1):
                    has_multi_span = True
                    break
            
            # 두 번째 행에 헤더성 내용이 있는지 확인
            if len(rows) > 1 and has_multi_span:
                second_row_cells = rows[1].find_elements(By.TAG_NAME, "th") + rows[1].find_elements(By.TAG_NAME, "td")
                second_row_has_content = any(cell.text.strip() for cell in second_row_cells)
                
                if second_row_has_content:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"다중헤더 테이블 감지 오류: {e}")
            return False

    def extract_multi_header_table(self, table_element, table_idx):
        """다중헤더 테이블 전용 추출 (rowspan/colspan 완전 처리)"""
        try:
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            if len(rows) < 2:
                return None
            
            # 1단계: 최대 열 수 계산
            max_cols = 0
            for row_idx, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, "th") + row.find_elements(By.TAG_NAME, "td")
                col_count = 0
                
                for cell in cells:
                    colspan = cell.get_attribute('colspan')
                    colspan = int(colspan) if colspan and colspan.isdigit() else 1
                    col_count += colspan
                
                max_cols = max(max_cols, col_count)
            
            # 매트릭스 초기화 및 데이터 채우기
            table_matrix = []
            for _ in range(len(rows)):
                table_matrix.append([None] * max_cols)
            
            # rowspan/colspan 처리하여 매트릭스 채우기
            for row_idx, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, "th") + row.find_elements(By.TAG_NAME, "td")
                current_col = 0
                
                for cell in cells:
                    # 이미 채워진 셀 건너뛰기
                    while current_col < max_cols and table_matrix[row_idx][current_col] is not None:
                        current_col += 1
                    
                    if current_col >= max_cols:
                        break
                    
                    cell_text = cell.text.strip()
                    rowspan = cell.get_attribute('rowspan')
                    colspan = cell.get_attribute('colspan')
                    
                    rowspan = int(rowspan) if rowspan and rowspan.isdigit() else 1
                    colspan = int(colspan) if colspan and colspan.isdigit() else 1
                    
                    # 매트릭스에 셀 데이터 채우기
                    for r in range(rowspan):
                        for c in range(colspan):
                            if (row_idx + r < len(table_matrix) and 
                                current_col + c < max_cols):
                                table_matrix[row_idx + r][current_col + c] = cell_text
                    
                    current_col += colspan
            
            # 헤더 생성
            processed_headers = self.create_multi_headers(table_matrix, max_cols)
            
            # 데이터 행 추출
            header_row_count = self.detect_header_row_count(table_matrix)
            data_rows = []
            
            for row_idx in range(header_row_count, len(table_matrix)):
                row = table_matrix[row_idx]
                processed_row = [cell if cell is not None else "" for cell in row]
                
                if any(cell.strip() for cell in processed_row):
                    data_rows.append(processed_row)
            
            table_data = {
                "table_type": "multi_header",
                "headers": processed_headers,
                "rows": data_rows
            }
            
            return table_data
            
        except Exception as e:
            self.logger.error(f"다중헤더 테이블 추출 오류: {e}")
            return None

    def create_multi_headers(self, table_matrix, max_cols):
        """다중헤더를 단일 헤더 리스트로 생성"""
        try:
            header_row_count = self.detect_header_row_count(table_matrix)
            processed_headers = []
            
            for col_idx in range(max_cols):
                header_parts = []
                
                # 각 헤더 행에서 해당 열의 값 수집
                for row_idx in range(header_row_count):
                    if (row_idx < len(table_matrix) and 
                        col_idx < len(table_matrix[row_idx]) and
                        table_matrix[row_idx][col_idx]):
                        
                        cell_value = table_matrix[row_idx][col_idx].strip()
                        if cell_value and cell_value not in header_parts:
                            header_parts.append(cell_value)
                
                # 헤더 결합
                if header_parts:
                    combined_header = self.combine_header_parts(header_parts, col_idx)
                    processed_headers.append(combined_header)
                else:
                    processed_headers.append(f"열{col_idx+1}")
            
            return processed_headers
            
        except Exception as e:
            self.logger.error(f"다중헤더 생성 오류: {e}")
            return [f"열{i+1}" for i in range(max_cols)]

    def detect_header_row_count(self, table_matrix):
        """헤더 행 수 자동 감지"""
        try:
            if len(table_matrix) < 2:
                return 1
            
            # 데이터 행 패턴 찾기
            for row_idx in range(len(table_matrix)):
                row = table_matrix[row_idx]
                data_indicators = 0
                
                for cell in row:
                    if cell and (
                        re.search(r'[①②③④⑤]', cell) or      # 순서 번호
                        re.search(r'\d+\.?\d*%', cell) or     # 백분율
                        re.search(r'연\s*\d+', cell) or       # 연 X.X%
                        '중도해지금리' in cell or             # 광주은행 특화
                        ('만기해지' in cell and '①' not in cell) or  # 데이터성 만기해지
                        ('중도해지' in cell and '②' not in cell)     # 데이터성 중도해지
                    ):
                        data_indicators += 1
                
                # 데이터 지표가 2개 이상이면 데이터 행으로 판단
                if data_indicators >= 2:
                    return max(row_idx, 1)
            
            # 기본값: 2행 헤더
            return 2
            
        except Exception as e:
            self.logger.warning(f"헤더 행 수 감지 실패: {e}")
            return 2

    def combine_header_parts(self, header_parts, col_idx):
        """헤더 부분들을 의미있게 결합"""
        try:
            if len(header_parts) == 1:
                return header_parts[0]
            
            # 중복 제거 및 순서 보존
            unique_parts = []
            for part in header_parts:
                if part and part not in unique_parts:
                    unique_parts.append(part)
            
            if len(unique_parts) == 1:
                return unique_parts[0]
            
            # 광주은행 특화 결합 규칙
            combined = "_".join(unique_parts)
            
            # "상황별 예상 적용금리" + "A" = "상황별 예상 적용금리_A"
            if "상황별" in combined and "적용금리" in combined:
                return combined
            
            # 일반적인 결합
            return combined
                
        except Exception as e:
            self.logger.warning(f"헤더 결합 오류: {e}")
            return "_".join(header_parts) if header_parts else f"열{col_idx+1}"

    def extract_preferential_rate_info(self, product_data):
        """범용 우대금리 정보 추출 - 다중헤더 테이블 처리 포함"""
        preferential_data = {
            'has_preferential': False,
            'text_info': [],
            'table_list': [],
            'table_count': 0
        }
        
        try:
            # 우대금리 섹션 찾기
            detail_section = None
            
            try:
                main_section = self.driver.find_element(By.CSS_SELECTOR, "ul.fpm-list-type01.view")
                list_items = main_section.find_elements(By.TAG_NAME, "li")
                
                for item in list_items:
                    try:
                        title_element = item.find_element(By.CSS_SELECTOR, ".list-tit-area strong")
                        title = title_element.text.strip()
                        
                        if "우대금리" in title:
                            detail_section = item
                            break
                    except:
                        continue
            except:
                pass
            
            if not detail_section:
                product_data['preferential_rate'] = preferential_data
                return
            
            # 콘텐츠 영역 추출
            content_area = detail_section.find_element(By.CSS_SELECTOR, ".list-con-area")
            
            # 텍스트 정보 추출
            text_content = content_area.text.strip()
            if text_content:
                text_lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                preferential_data['text_info'] = text_lines
                preferential_data['has_preferential'] = True
            
            # 모든 테이블 추출 (다중헤더 감지 포함)
            all_tables = content_area.find_elements(By.TAG_NAME, "table")
            
            for table_idx, table in enumerate(all_tables):
                try:
                    # 다중헤더 테이블 감지 및 처리
                    if self.detect_multi_header_table(table):
                        table_data = self.extract_multi_header_table(table, table_idx)
                    else:
                        table_data = self.extract_any_table_structure(table, table_idx)
                    
                    if table_data and self.is_meaningful_table_structure(table_data):
                        table_data["table_index"] = table_idx + 1
                        preferential_data['table_list'].append(table_data)
                        
                except Exception as e:
                    self.logger.error(f"테이블 {table_idx+1} 추출 오류: {e}")
                    continue
            
            preferential_data['table_count'] = len(preferential_data['table_list'])
            
        except Exception as e:
            self.logger.error(f"우대금리 정보 추출 실패: {e}")
            preferential_data['error'] = str(e)
        
        product_data['preferential_rate'] = preferential_data

    def extract_any_table_structure(self, table_element, table_idx):
        """일반 테이블 구조 추출"""
        try:
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            if len(rows) < 1:
                return None
            
            row_count = len(rows)
            first_row_cells = rows[0].find_elements(By.TAG_NAME, "th") + rows[0].find_elements(By.TAG_NAME, "td")
            col_count = len(first_row_cells)
            
            table_type = self.determine_table_structure_only(rows, col_count, row_count)
            
            if table_type == "vertical":
                return self.extract_vertical_structure(rows, table_idx)
            else:
                return self.extract_horizontal_structure(rows, table_idx)
                
        except Exception as e:
            self.logger.error(f"테이블 {table_idx+1} 구조 분석 오류: {e}")
            return None

    def determine_table_structure_only(self, rows, col_count, row_count):
        """테이블 유형 판단"""
        try:
            if col_count == 2 and row_count >= 2:
                return "vertical"
            elif col_count >= 3:
                return "horizontal"
            else:
                return "horizontal"
        except:
            return "horizontal"

    def extract_vertical_structure(self, rows, table_idx):
        """세로표 구조 추출"""
        try:
            table_data = {
                "table_type": "vertical",
                "headers": ["항목", "내용"],
                "rows": []
            }
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "th") + row.find_elements(By.TAG_NAME, "td")
                
                if len(cells) >= 2:
                    col1 = cells[0].text.strip()
                    col2 = cells[1].text.strip()
                    if col1 or col2:
                        table_data["rows"].append([col1, col2])
                elif len(cells) == 1:
                    col1 = cells[0].text.strip()
                    if col1:
                        table_data["rows"].append([col1, ""])
            
            return table_data if table_data["rows"] else None
            
        except Exception as e:
            self.logger.error(f"세로표 구조 추출 오류: {e}")
            return None

    def extract_horizontal_structure(self, rows, table_idx):
        """가로표 구조 추출"""
        try:
            table_data = {
                "table_type": "horizontal",
                "headers": [],
                "rows": []
            }
            
            if len(rows) > 0:
                header_cells = rows[0].find_elements(By.TAG_NAME, "th") + rows[0].find_elements(By.TAG_NAME, "td")
                headers = [cell.text.strip() for cell in header_cells]
                table_data["headers"] = headers
            
            for row_idx in range(1, len(rows)):
                row = rows[row_idx]
                cells = row.find_elements(By.TAG_NAME, "th") + row.find_elements(By.TAG_NAME, "td")
                row_data = [cell.text.strip() for cell in cells]
                
                if any(cell for cell in row_data):
                    table_data["rows"].append(row_data)
            
            if not table_data["rows"] and table_data["headers"]:
                if any(header for header in table_data["headers"]):
                    table_data["rows"].append(table_data["headers"])
                    table_data["headers"] = [f"열{i+1}" for i in range(len(table_data["headers"]))]
            
            return table_data if (table_data["headers"] or table_data["rows"]) else None
            
        except Exception as e:
            self.logger.error(f"가로표 구조 추출 오류: {e}")
            return None

    def is_meaningful_table_structure(self, table_data):
        """테이블 유효성 검사"""
        if not table_data:
            return False
        
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        
        has_content = len(rows) > 0 or len(headers) > 0
        
        if has_content:
            all_cells = []
            for header in headers:
                all_cells.append(str(header))
            for row in rows:
                for cell in row:
                    all_cells.append(str(cell))
            
            has_real_content = any(cell.strip() for cell in all_cells)
            return has_real_content
        
        return False

    def extract_rate_table_info_improved(self, product_data):
        """금리 테이블 추출"""
        try:
            main_window = self.driver.current_window_handle
            
            # 금리안내 바로가기 버튼 찾기
            rate_button = None
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            
            for link in all_links:
                if "금리안내 바로가기" in link.text.strip():
                    rate_button = link
                    break
            
            if not rate_button:
                product_data['period_rate'] = {'status': 'button_not_found'}
                return
            
            # 버튼 메타데이터 추출
            product_code = rate_button.get_attribute('data-param1')
            menu_id = rate_button.get_attribute('data-menu_id')
            
            product_data["product_code"] = product_code or ""
            product_data["rate_menu_id"] = menu_id or ""
            
            # 상품 카테고리 결정 (수정된 메서드 사용)
            product_data["type"] = self.determine_product_category(
                product_data["name"], menu_id
            )
            
            # 버튼 클릭 및 처리
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", rate_button)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", rate_button)
            time.sleep(3)
            
            # 창 처리 로직
            all_windows = self.driver.window_handles
            
            if len(all_windows) > 1:
                for window in all_windows:
                    if window != main_window:
                        self.driver.switch_to.window(window)
                        break
                
                time.sleep(2)
                product_data["rate_url"] = self.driver.current_url
                
                if menu_id == "ITRIRIF010300":
                    rate_tables = self.extract_savings_account_tables()
                else:
                    rate_tables = self.extract_rate_tables_from_page()
                
                self.driver.close()
                self.driver.switch_to.window(main_window)
                time.sleep(1)
                
            else:
                time.sleep(2)
                product_data["rate_url"] = self.driver.current_url
                
                if menu_id == "ITRIRIF010300":
                    rate_tables = self.extract_savings_account_tables()
                else:
                    rate_tables = self.extract_rate_tables_from_page()
                
                self.driver.back()
                time.sleep(2)
            
            product_data['period_rate'] = {
                'product_code': product_code,
                'rate_menu_id': menu_id,
                'table_list': rate_tables,
                'table_count': len(rate_tables),
                'status': 'success'
            }
            
        except Exception as e:
            self.logger.error(f"금리 테이블 추출 실패: {e}")
            product_data['period_rate'] = {'status': 'failed', 'error': str(e)}

    def extract_rate_tables_from_page(self):
        """금리 페이지에서 테이블 추출"""
        try:
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            meaningful_tables = []
            
            for i, table in enumerate(tables):
                try:
                    table_data = self.extract_simple_table_structure(table)
                    
                    if table_data and self.is_meaningful_rate_table_improved(table_data):
                        cleaned_table_data = self.clean_rate_table_data(table_data)
                        if cleaned_table_data:
                            cleaned_table_data["table_index"] = i + 1
                            meaningful_tables.append(cleaned_table_data)
                            
                except Exception as e:
                    self.logger.error(f"테이블 {i+1} 처리 오류: {e}")
                    continue
            
            return meaningful_tables
            
        except Exception as e:
            self.logger.error(f"금리 테이블 추출 실패: {e}")
            return []

    def extract_savings_account_tables(self):
        """입출금자유상품 테이블 추출"""
        try:
            time.sleep(3)
            all_tables = self.driver.find_elements(By.TAG_NAME, "table")
            meaningful_tables = []
            
            for i, table in enumerate(all_tables):
                try:
                    table_data = self.extract_simple_table_structure(table)
                    
                    if table_data and self.is_savings_account_rate_table_improved(table_data):
                        cleaned_table_data = self.clean_rate_table_data(table_data)
                        if cleaned_table_data:
                            cleaned_table_data["table_index"] = i + 1
                            meaningful_tables.append(cleaned_table_data)
                            
                except Exception as e:
                    self.logger.error(f"테이블 {i+1} 처리 오류: {e}")
                    continue
            
            if not meaningful_tables:
                text_tables = self.extract_rate_from_text_structure()
                meaningful_tables.extend(text_tables)
            
            return meaningful_tables
            
        except Exception as e:
            self.logger.error(f"입출금자유상품 테이블 추출 실패: {e}")
            return []

    def is_meaningful_rate_table_improved(self, table_data):
        """의미있는 금리 테이블 판단"""
        if not table_data or not table_data.get("rows"):
            return False
        
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        all_text = " ".join(headers + [str(cell) for row in rows for cell in row])
        
        # UI 요소 키워드 필터링
        ui_keywords = [
            "상품명 선택", "달력 레이어", "연도\n2029", "월\n01", "일\n01",
            "조회일자", "달력", "드롭다운", "레이어"
        ]
        
        if any(keyword in all_text for keyword in ui_keywords):
            return False
        
        # 금리 테이블 키워드
        general_rate_keywords = [
            "기본금리", "최고금리", "우대금리", "연이율", "%", "금액구간", "가입기간"
        ]
        
        has_general_keyword = any(keyword in all_text for keyword in general_rate_keywords)
        has_percentage = "%" in all_text
        has_sufficient_data = len(rows) >= 1
        
        return has_general_keyword and has_percentage and has_sufficient_data

    def is_savings_account_rate_table_improved(self, table_data):
        """입출금자유상품 테이블 판단"""
        if not table_data:
            return False
        
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        all_text = " ".join(headers + [str(cell) for row in rows for cell in row]).lower()
        
        # UI 요소 필터링
        ui_keywords = [
            "상품명 선택", "달력 레이어", "연도\n2029", "월\n01", "일\n01",
            "조회일자", "달력", "드롭다운", "레이어"
        ]
        
        if any(keyword.lower() in all_text for keyword in ui_keywords):
            return False
        
        # 입출금자유상품 특정 헤더
        savings_specific_headers = [
            '상품명', '금액구간별', '기본금리', '금리', '구분', '상품금리'
        ]
        
        header_text = " ".join(headers).lower()
        has_specific_header = any(keyword.lower() in header_text for keyword in savings_specific_headers)
        
        # 일반적인 저축상품 키워드
        general_savings_keywords = [
            '금액구간', '구간별', '보통예금', '저축예금',
            '만원', '이상', '미만', '원'
        ]
        
        has_general_keyword = any(keyword in all_text for keyword in general_savings_keywords)
        has_percentage = "%" in all_text
        
        return has_specific_header or (has_general_keyword and has_percentage)

    def clean_rate_table_data(self, table_data):
        """기간별 금리표 데이터 정리 (상품명 컬럼 제거)"""
        try:
            if not table_data:
                return None
            
            headers = table_data.get("headers", [])
            rows = table_data.get("rows", [])
            
            # 상품명 컬럼 찾기
            product_name_col_index = None
            for i, header in enumerate(headers):
                if "상품명" in header:
                    product_name_col_index = i
                    break
            
            # 상품명 컬럼이 없으면 원본 반환
            if product_name_col_index is None:
                return table_data
            
            # 상품명 컬럼 제거
            new_headers = []
            for i, header in enumerate(headers):
                if i != product_name_col_index:
                    new_headers.append(header)
            
            new_rows = []
            for row in rows:
                if len(row) > product_name_col_index:
                    new_row = []
                    for i, cell in enumerate(row):
                        if i != product_name_col_index:
                            new_row.append(cell)
                    
                    if any(cell.strip() for cell in new_row):
                        new_rows.append(new_row)
                else:
                    if any(cell.strip() for cell in row):
                        new_rows.append(row)
            
            # 데이터 일관성 확인
            if new_headers and new_rows:
                expected_col_count = len(new_headers)
                corrected_rows = []
                
                for row in new_rows:
                    if len(row) < expected_col_count:
                        corrected_row = row + [""] * (expected_col_count - len(row))
                        corrected_rows.append(corrected_row)
                    elif len(row) > expected_col_count:
                        corrected_row = row[:expected_col_count]
                        corrected_rows.append(corrected_row)
                    else:
                        corrected_rows.append(row)
                
                new_rows = corrected_rows
            
            return {
                "headers": new_headers,
                "rows": new_rows
            }
            
        except Exception as e:
            self.logger.error(f"테이블 데이터 정리 실패: {e}")
            return table_data

    def extract_simple_table_structure(self, table_element):
        """간단한 테이블 구조 추출 (rowspan/colspan 처리)"""
        try:
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            if len(rows) < 1:
                return None
            
            # 전체 테이블 구조를 매트릭스로 구성
            table_matrix = []
            max_cols = 0
            
            # 첫 번째 패스: 전체 구조 파악
            for row_idx, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, "th") + row.find_elements(By.TAG_NAME, "td")
                col_count = 0
                
                for cell in cells:
                    colspan = cell.get_attribute('colspan')
                    colspan = int(colspan) if colspan and colspan.isdigit() else 1
                    col_count += colspan
                
                max_cols = max(max_cols, col_count)
            
            # 매트릭스 초기화
            for _ in range(len(rows)):
                table_matrix.append([None] * max_cols)
            
            # 두 번째 패스: 실제 데이터 채우기
            for row_idx, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, "th") + row.find_elements(By.TAG_NAME, "td")
                current_col = 0
                
                for cell in cells:
                    # 이미 채워진 셀 건너뛰기
                    while current_col < max_cols and table_matrix[row_idx][current_col] is not None:
                        current_col += 1
                    
                    if current_col >= max_cols:
                        break
                    
                    cell_text = cell.text.strip()
                    rowspan = cell.get_attribute('rowspan')
                    colspan = cell.get_attribute('colspan')
                    
                    rowspan = int(rowspan) if rowspan and rowspan.isdigit() else 1
                    colspan = int(colspan) if colspan and colspan.isdigit() else 1
                    
                    # 셀 데이터 채우기
                    for r in range(rowspan):
                        for c in range(colspan):
                            if (row_idx + r < len(table_matrix) and 
                                current_col + c < max_cols):
                                table_matrix[row_idx + r][current_col + c] = cell_text
                    
                    current_col += colspan
            
            # 매트릭스를 table_data 형식으로 변환
            table_data = {
                "headers": [],
                "rows": []
            }
            
            # 빈 셀을 빈 문자열로 변환
            for row_idx in range(len(table_matrix)):
                processed_row = []
                for cell in table_matrix[row_idx]:
                    processed_row.append(cell if cell is not None else "")
                table_matrix[row_idx] = processed_row
            
            if table_matrix:
                # 첫 번째 행을 헤더로 처리
                table_data["headers"] = table_matrix[0]
                
                # 나머지 행을 데이터로 처리
                for row in table_matrix[1:]:
                    if any(cell.strip() for cell in row):
                        table_data["rows"].append(row)
            
            return table_data if (table_data["headers"] or table_data["rows"]) else None
            
        except Exception as e:
            self.logger.error(f"테이블 구조 추출 오류: {e}")
            return None

    def extract_rate_from_text_structure(self):
        """텍스트 구조에서 금리 정보 추출"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            rate_patterns = [
                r'(\d+(?:천|백)?만원)\s*(?:이상|미만).*?(\d+\.?\d*%)',
                r'(보통예금|저축예금)\s+(\d+\.?\d*%)',
                r'(구간별|금액구간별).*?(\d+\.?\d*%)',
            ]
            
            tables = []
            
            for i, pattern in enumerate(rate_patterns):
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                
                if matches:
                    if i == 0:
                        headers = ["금액구간별", "기본금리"]
                    elif i == 1:
                        headers = ["구분", "기본금리"]  
                    else:
                        headers = ["구분", "금리"]
                    
                    rows = []
                    for match in matches[:5]:
                        if len(match) >= 2:
                            rows.append([match[0], match[1]])
                    
                    if rows:
                        table_data = {
                            "headers": headers,
                            "rows": rows,
                            "table_index": 2
                        }
                        tables.append(table_data)
                        break
            
            return tables
            
        except Exception as e:
            self.logger.warning(f"텍스트 구조에서 금리 추출 실패: {e}")
            return []

    def get_product_list_from_main_page(self, limit=10):
        """목록 페이지에서 상품 목록 추출"""
        try:
            self.driver.get(self.deposit_list_url)
            time.sleep(3)
            
            product_list = self.wait.until(
                EC.presence_of_element_located((By.ID, "list_goods"))
            )
            
            product_items = product_list.find_elements(By.TAG_NAME, "li")
            
            products = []
            for idx, item in enumerate(product_items):
                if len(products) >= limit:
                    break
                    
                try:
                    product_link = None
                    name = ""
                    product_idx = ""
                    
                    try:
                        product_link = item.find_element(By.CSS_SELECTOR, "a.btn_guide")
                        name = product_link.text.strip()
                        product_idx = product_link.get_attribute("data-idx")
                    except:
                        try:
                            all_links = item.find_elements(By.TAG_NAME, "a")
                            for link in all_links:
                                if link.text.strip() and "data-idx" in link.get_attribute("outerHTML"):
                                    product_link = link
                                    name = link.text.strip()
                                    product_idx = link.get_attribute("data-idx")
                                    break
                        except:
                            pass
                    
                    if not name or not product_link:
                        continue
                    
                    # 금리 정보 추출
                    max_rate = ""
                    basic_rate = ""
                    try:
                        max_rate_elem = item.find_element(By.CSS_SELECTOR, ".value.max .number")
                        max_rate = max_rate_elem.text.strip() + "%"
                    except:
                        pass
                    
                    try:
                        basic_rate_elem = item.find_element(By.CSS_SELECTOR, ".value.default .number")
                        basic_rate = basic_rate_elem.text.strip() + "%"
                    except:
                        pass
                    
                    products.append({
                        "name": name,
                        "product_idx": product_idx or str(idx + 1),
                        "max_rate": max_rate,
                        "basic_rate": basic_rate,
                        "list_index": len(products) + 1
                    })
                    
                except Exception as e:
                    continue
            
            return products
            
        except Exception as e:
            self.logger.error(f"목록 페이지 크롤링 실패: {e}")
            return []

    def extract_detail_page_info(self, product_data):
        """상품 상세 페이지 정보 추출"""
        try:
            detail_list = self.driver.find_element(By.CSS_SELECTOR, "ul.fpm-list-type01.view")
            list_items = detail_list.find_elements(By.TAG_NAME, "li")
            
            for item in list_items:
                try:
                    title_element = item.find_element(By.CSS_SELECTOR, ".list-tit-area strong")
                    title = title_element.text.strip()
                    
                    content_area = item.find_element(By.CSS_SELECTOR, ".list-con-area")
                    content = content_area.text.strip()
                    
                    if "가입기간" in title or "계약기간" in title:
                        product_data["sub_term"] = content
                    elif "가입대상" in title:
                        product_data["sub_target"] = content
                    elif "거래방법" in title or "가입방법" in title:
                        product_data["sub_way"] = content
                    elif "가입금액" in title:
                        product_data["sub_amount"] = content
                    elif "세제혜택" in title:
                        product_data["tax_benefit"] = content
                    elif "상품유형" in title:
                        try:
                            product_type_element = item.find_element(By.CSS_SELECTOR, ".list-con-area ul.cs-lists li")
                            product_data["detail_type"] = product_type_element.text.strip()
                        except:
                            product_data["detail_type"] = content.strip()
                except:
                    continue
        except:
            pass

    def extract_complete_product_info(self, product_info, index):
        """완전한 상품 정보 추출"""
        name = product_info["name"]
        
        try:
            # 목록 페이지로 이동
            self.driver.get(self.deposit_list_url)
            time.sleep(2)
            
            # 해당 상품 찾아서 클릭
            product_list = self.wait.until(
                EC.presence_of_element_located((By.ID, "list_goods"))
            )
            
            product_items = product_list.find_elements(By.TAG_NAME, "li")
            target_link = None
            
            for item in product_items:
                try:
                    link = item.find_element(By.CSS_SELECTOR, "a.btn_guide")
                    if link.text.strip() == name:
                        target_link = link
                        break
                except:
                    continue
            
            if not target_link:
                raise Exception(f"상품 '{name}' 링크를 찾을 수 없음")
            
            # 상품 클릭
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_link)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", target_link)
            time.sleep(3)
            
            # 기본 정보 구조 생성 (수정된 변수명 적용)
            product_data = {
                "name": name,
                "product_idx": str(index),
                "list_index": index,
                "scraped_at": datetime.datetime.now().isoformat(),
                "product_code": "",
                "rate_menu_id": "",
                "type": "미분류",
                "detail_type": "",
                "basic_rate": product_info.get("basic_rate", ""),
                "max_rate": product_info.get("max_rate", ""),
                "url_link": self.driver.current_url,
                "sub_amount": "",
                "sub_target": "",
                "sub_way": "",
                "sub_term": "",
                "tax_benefit": "",
                "preferential_rate": {},
                "period_rate": {},
                "rate_url": ""
            }
            
            # 상세 페이지 정보 추출
            self.extract_detail_page_info(product_data)
            
            # 다중헤더 우대금리 정보 추출
            self.extract_preferential_rate_info(product_data)
            
            # 기간별 금리 테이블 추출
            self.extract_rate_table_info_improved(product_data)
            
            return product_data
            
        except Exception as e:
            self.logger.error(f"상품 '{name}' 처리 실패: {e}")
            return {
                "name": name,
                "product_idx": str(index),
                "list_index": index,
                "scraped_at": datetime.datetime.now().isoformat(),
                "error": str(e)
            }

    def crawl_all_products(self, limit=None):
        """전체 상품 크롤링 (다중헤더 처리 포함)"""
        try:
            # 1. 목록 페이지에서 상품 목록 가져오기
            product_list = self.get_product_list_from_main_page(limit=limit or 999)
            
            if not product_list:
                print("상품 목록을 가져올 수 없습니다.")
                return []
            
            all_products = []
            
            # 2. 각 상품별 완전 정보 크롤링
            for i, product_info in enumerate(product_list):
                print(f"[{i+1}/{len(product_list)}] {product_info['name']} 크롤링 중...")
                
                try:
                    complete_product = self.extract_complete_product_info(product_info, i+1)
                    all_products.append(complete_product)
                    
                    time.sleep(1)  # 요청 간격 조절
                    
                except Exception as e:
                    error_product = {
                        "name": product_info['name'],
                        "product_idx": str(i+1),
                        "list_index": i+1,
                        "scraped_at": datetime.datetime.now().isoformat(),
                        "error": f"예외 발생: {str(e)}"
                    }
                    all_products.append(error_product)
                    continue
            
            # 3. 예금과 적금만 필터링
            filtered_products = self.filter_deposit_savings_only(all_products)
            
            # 4. 결과 저장
            current_date = datetime.datetime.now().strftime("%Y%m%d")
            filename = f"gwangju_bank_products_{current_date}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(filtered_products, f, ensure_ascii=False, indent=2)
            
            # 5. 최종 결과 요약
            success_count = len([p for p in filtered_products if 'error' not in p])
            error_count = len([p for p in filtered_products if 'error' in p])
            
            print(f"크롤링 완료! 전체 {len(all_products)}개 중 예금/적금 {len(filtered_products)}개 상품")
            print(f"결과 저장: {filename}")
            
            return filtered_products
            
        except Exception as e:
            print(f"전체 크롤링 실패: {e}")
            return []

    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()

# 실행 코드
if __name__ == "__main__":
    crawler = KJBankCompleteCrawler(headless=True)
    
    try:
        # 전체 크롤링 실행
        products = crawler.crawl_all_products(limit=None) 
            
        print("\n크롤링 완료!")
        
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n오류 발생: {e}")
    finally:
        crawler.close()