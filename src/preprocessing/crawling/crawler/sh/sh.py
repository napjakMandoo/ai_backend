#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수협은행 금융상품 크롤링 시스템 (Python + Selenium) - 카테고리별 크롤링 버전
대상: 목돈마련상품, 여유자금운용상품
결과: JSON 파일로 저장 (기업은행과 동일한 포맷)
우대조건 테이블만 제대로 긁게 정밀화 필요 (거의 다됨)
"""
import dotenv
import os
import logging
import json
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

from src.preprocessing.crawling.BankLink import BankLink

class SuhyupBankCategoryCrawler:
    """수협은행 금융상품 카테고리별 크롤링 클래스"""
    
    def __init__(self, headless: bool = True):
        """초기화"""
        self.headless = headless
        self.logger = logging.getLogger(__name__)
        self.driver = self._create_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.all_products = []
        self.processed_products = set()
        self.logger = logging.getLogger(__name__)

        # 크롤링할 카테고리 정의
        self.categories = [
            {'name': '목돈마련상품'},
            {'name': '여유자금운용상품'}
        ]

    def _create_driver(self)-> webdriver.Chrome:
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
        self.logger.info("✅ Chrome 드라이버 설정 완료")
        return webdriver.Chrome(options=opts)

    def navigate_to_deposits_page(self):
        """수협은행 예금 메인 페이지로 이동"""
        try:
            url = BankLink.SH_BANK_LINK.value
            self.driver.get(url)
            
            # iframe으로 전환
            iframe = self.wait.until(
                EC.presence_of_element_located((By.ID, "ib20_content_frame"))
            )
            self.driver.switch_to.frame(iframe)
            
            self.logger.info("✅ 수협은행 예금 메인 페이지 접속 완료")
            time.sleep(3)
            
        except Exception as e:
            self.logger.error(f"❌ 페이지 접속 실패: {e}")
            raise
    
    def navigate_to_category(self, category_name: str) -> bool:
        """특정 카테고리로 이동"""
        try:
            self.logger.info(f"🔄 '{category_name}' 카테고리로 이동 중...")
            
            # 사이드바의 모든 링크를 검사하여 텍스트 매칭
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            self.logger.info(f"총 {len(all_links)}개 링크 검사 중...")
            
            category_links = []
            for link in all_links:
                try:
                    link_text = link.text.strip()
                    if category_name in link_text:
                        category_links.append(link)
                        self.logger.info(f"매칭 링크 발견: '{link_text}'")
                except:
                    continue
            
            if not category_links:
                self.logger.error(f"❌ '{category_name}' 카테고리 링크를 찾을 수 없습니다")
                return False
            
            # 첫 번째 링크 클릭
            target_link = category_links[0]
            self.logger.info(f"🖱️ '{category_name}' 링크 클릭: '{target_link.text.strip()}'")
            
            try:
                self.driver.execute_script("arguments[0].scrollIntoView();", target_link)
                time.sleep(1)
                target_link.click()
            except Exception as e:
                self.logger.warning(f"⚠️ 일반 클릭 실패, JavaScript로 클릭 시도: {e}")
                self.driver.execute_script("arguments[0].click();", target_link)
            
            time.sleep(5)
            self.logger.info(f"✅ '{category_name}' 카테고리 이동 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ '{category_name}' 카테고리 이동 실패: {e}")
            return False
    
    def get_page_products(self, category_name: str) -> List[Dict[str, Any]]:
        """현재 페이지의 상품 목록 가져오기"""
        try:
            time.sleep(2)
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, "a.go-detail")
            
            products = []
            excluded_count = 0
            
            for i, element in enumerate(product_elements):
                try:
                    title_element = element.find_element(By.TAG_NAME, "dt")
                    title = title_element.text.strip()
                    
                    if not title or len(title) < 3:
                        excluded_count += 1
                        continue
                    
                    product_key = f"{category_name}_i{i}_{title}"
                    
                    if product_key in self.processed_products:
                        continue
                    
                    # 금리 정보 추출
                    list_rates = self._extract_rates_from_list(element)
                    
                    if list_rates.get('basic_rate') is None or list_rates.get('max_rate') is None:
                        excluded_count += 1
                        continue
                    
                    products.append({
                        'title': title,
                        'element': element,
                        'product_key': product_key,
                        'category': category_name,
                        'index': i,
                        'list_basic_rate': list_rates.get('basic_rate'),
                        'list_max_rate': list_rates.get('max_rate')
                    })
                    
                    self.logger.info(f"✅ 상품 추가: {title}")
                    
                except Exception as e:
                    excluded_count += 1
                    continue
            
            self.logger.info(f"📦 {len(products)}개 상품 추출 (제외: {excluded_count}개)")
            return products
            
        except Exception as e:
            self.logger.error(f"❌ 상품 목록 가져오기 실패: {e}")
            return []
    
    def _extract_rates_from_list(self, product_element) -> Dict[str, Optional[float]]:
        """상품 리스트에서 금리 정보 추출"""
        rates = {'basic_rate': None, 'max_rate': None}
        
        try:
            product_card = product_element
            card_text = ""
            
            for _ in range(5):
                try:
                    card_text = product_card.text
                    if card_text and '%' in card_text:
                        break
                    product_card = product_card.find_element(By.XPATH, "..")
                except:
                    break
            
            if not card_text:
                return rates
            
            # 최고금리 패턴
            max_rate_patterns = [
                r'최고\s*(?:연)?\s*(?:금리)?\s*(\d+\.?\d*)\s*%',
                r'최고금리\s*(\d+\.?\d*)\s*%'
            ]
            
            for pattern in max_rate_patterns:
                match = re.search(pattern, card_text)
                if match:
                    try:
                        rate_value = float(match.group(1))
                        if 0.1 <= rate_value <= 10.0:
                            rates['max_rate'] = rate_value
                            break
                    except:
                        continue
            
            # 기본금리 패턴
            basic_rate_patterns = [
                r'기본\s*(?:연)?\s*(?:금리)?\s*(\d+\.?\d*)\s*%',
                r'기본금리\s*(\d+\.?\d*)\s*%'
            ]
            
            for pattern in basic_rate_patterns:
                match = re.search(pattern, card_text)
                if match:
                    try:
                        rate_value = float(match.group(1))
                        if 0.1 <= rate_value <= 10.0:
                            rates['basic_rate'] = rate_value
                            break
                    except:
                        continue
            
            # 일반 패턴
            if rates['basic_rate'] is None or rates['max_rate'] is None:
                general_rates = re.findall(r'(\d+\.\d+)%', card_text)
                valid_rates = []
                
                for rate_str in general_rates:
                    try:
                        rate_value = float(rate_str)
                        if 0.1 <= rate_value <= 10.0:
                            valid_rates.append(rate_value)
                    except:
                        continue
                
                if valid_rates:
                    if len(valid_rates) >= 2:
                        rates['basic_rate'] = min(valid_rates)
                        rates['max_rate'] = max(valid_rates)
                    else:
                        rates['basic_rate'] = valid_rates[0]
                        rates['max_rate'] = valid_rates[0]
            
        except Exception as e:
            self.logger.warning(f"금리 추출 실패: {e}")
        
        return rates
    
    def extract_product_info(self, product_title: str, product_key: str, category_name: str, list_basic_rate: float = None, list_max_rate: float = None) -> Dict[str, Any]:
        """상품 정보 추출"""
        try:
            self.logger.info(f"🔍 '{product_title}' 정보 수집 중...")
            
            self.processed_products.add(product_key)
            time.sleep(2)
            
            # 기본 정보 추출
            join_amount = self._extract_dt_info('가입금액')
            join_target = self._extract_dt_info('가입대상')
            join_method = self._extract_dt_info('가입방법', ['거래방법'])
            join_period = self._extract_dt_info('가입기간', ['계약기간', '예치기간'])
            
            # 우대조건 먼저 추출 (금리 탭으로 가기 전)
            preferential_conditions = self._extract_preferential_conditions()
            
            # 그 다음 금리 정보 추출 (금리 탭으로 이동)
            interest_rates = self._extract_interest_rates()
            
            # 최종 금리 결정
            basic_rate = list_basic_rate if list_basic_rate else 2.0
            max_rate = list_max_rate if list_max_rate else 2.5
            
            # 기간별금리 구조화
            period_rates = self._structure_period_rates(interest_rates)
            
            product_info = {
                '은행명': '수협은행',
                '상품명': product_title,
                '상품유형': '적금' if '적금' in product_title else '예금',
                '상품카테고리': category_name,
                '상품상세URL': self.driver.current_url,
                '크롤링일시': datetime.now().strftime("%Y-%m-%d"),
                '가입금액': join_amount if join_amount != '정보 없음' else None,
                '가입대상': join_target if join_target != '정보 없음' else None,
                '가입방법': join_method if join_method != '정보 없음' else None,
                '계약기간': join_period if join_period != '정보 없음' else None,
                '기본금리': basic_rate,
                '최대금리': max_rate,
                '세제혜택': None,
                '예금자보호': '5천만원 한도 보호',
                '우대조건': preferential_conditions,
                '금리계산방식': '단리',
                '기간별금리': period_rates
            }
            
            self.logger.info(f"✅ '{product_title}' 정보 수집 완료")
            return product_info
            
        except Exception as e:
            self.logger.error(f"❌ '{product_title}' 정보 수집 실패: {e}")
            self.processed_products.add(product_key)
            
            return {
                '은행명': '수협은행',
                '상품명': product_title,
                '상품유형': '적금' if '적금' in product_title else '예금',
                '상품카테고리': category_name,
                '상품상세URL': self.driver.current_url,
                '크롤링일시': datetime.now().strftime("%Y-%m-%d"),
                '기본금리': list_basic_rate,
                '최대금리': list_max_rate,
                '우대조건': [],
                '기간별금리': []
            }
    
    def _extract_dt_info(self, keyword: str, alt_keywords: List[str] = None) -> str:
        """DT 태그에서 정보 추출 - 키워드 확장"""
        try:
            keywords = [keyword] + (alt_keywords or [])
            
            # 가입방법의 경우 추가 키워드 확장
            if keyword == '가입방법':
                keywords.extend(['신규/해지 방법', '신규해지방법', '신규/해지', '가입/해지', '가입해지방법'])
            
            for search_keyword in keywords:
                dt_elements = self.driver.find_elements(By.TAG_NAME, "dt")
                
                for dt in dt_elements:
                    dt_text = dt.text.strip()
                    if search_keyword in dt_text:
                        try:
                            dd_element = dt.find_element(By.XPATH, "following-sibling::dd[1]")
                            if dd_element:
                                text = dd_element.text.strip()
                                if text and len(text) > 0:
                                    return text
                        except:
                            continue
            
            return '정보 없음'
            
        except Exception as e:
            return '정보 없음'
    
    def _extract_preferential_conditions(self) -> List[Dict[str, Any]]:
   
        try:
            conditions = []
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            self.logger.info(f"🔍 총 {len(tables)}개 테이블 검사 중...")
            
            for table_idx, table in enumerate(tables):
                try:
                    # 테이블 전체 텍스트 가져오기
                    table_text = table.text.strip()
                    table_text_lower = table_text.lower()
                    
                    # 테이블 헤더 분석
                    headers = table.find_elements(By.TAG_NAME, "th")
                    header_texts = [h.text.strip() for h in headers]
                    header_combined = ' '.join(header_texts).lower()
                    
                    self.logger.info(f"📋 테이블 {table_idx+1}: 헤더 = {header_combined}")
                    self.logger.info(f"📋 테이블 {table_idx+1}: 전체텍스트 포함 키워드 = {table_text_lower[:100]}...")
                    
                    # 우대조건 테이블 식별 키워드 확장
                    preferential_keywords = [
                        '우대금리', '우대조건', '항목', '거래우대금리', '가입우대금리',
                        '특별우대', '추가금리', '가산금리', '우대내용', '우대이율',
                        '가해우대금리', '가해우대', '적용기준'
                    ]
                    
                    # 제외할 테이블 키워드
                    exclude_keywords = [
                        '계약기간', '예치기간', '약정이율', '기본이율',
                        '중도해지', '해지금리', '해지이율', '만기후', '만기 후'
                    ]
                    
                    # 우대조건 테이블인지 확인 (헤더 + 전체 텍스트 모두 확인)
                    is_preferential_header = any(keyword in header_combined for keyword in preferential_keywords)
                    is_preferential_text = any(keyword in table_text_lower for keyword in preferential_keywords)
                    is_excluded = any(keyword in header_combined or keyword in table_text_lower for keyword in exclude_keywords)
                    
                    if (is_preferential_header or is_preferential_text) and not is_excluded:
                        self.logger.info(f"✅ 우대조건 테이블 발견: {header_combined}")
                        
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        self.logger.info(f"📝 총 {len(rows)}개 행 처리 중...")
                        
                        # 테이블 구조 분석을 위해 모든 행의 셀 개수 확인
                        row_structures = []
                        for row in rows:
                            cells = row.find_elements(By.CSS_SELECTOR, "th, td")
                            cell_texts = [cell.text.strip() for cell in cells]
                            row_structures.append({
                                'cells': cells,
                                'cell_texts': cell_texts,
                                'cell_count': len(cells)
                            })
                        
                        # 헤더 행 식별 (첫 번째 행이거나 th 태그가 많은 행)
                        header_row_idx = 0
                        for i, row_struct in enumerate(row_structures):
                            th_count = len([cell for cell in row_struct['cells'] if cell.tag_name == 'th'])
                            if th_count >= len(row_struct['cells']) // 2:  # 절반 이상이 th인 경우
                                header_row_idx = i
                                break
                        
                        self.logger.info(f"🏷️ 헤더 행: {header_row_idx}, 구조: {row_structures[header_row_idx]['cell_texts']}")
                        
                        # 데이터 행들 처리 (헤더 행 이후)
                        table_conditions = []
                        for row_idx in range(header_row_idx + 1, len(row_structures)):
                            try:
                                row_struct = row_structures[row_idx]
                                cells = row_struct['cells']
                                cell_texts = row_struct['cell_texts']
                                
                                # 빈 행 스킵
                                if not any(text.strip() for text in cell_texts):
                                    continue
                                
                                self.logger.info(f"  📄 행 {row_idx}: {len(cells)}개 셀 = {cell_texts}")
                                
                                condition_name = None
                                condition_detail = None
                                additional_rate = None
                                
                                # 셀 개수에 따른 처리
                                if len(cells) == 1:
                                    # 1개 셀: 제목이나 구분자인 경우가 많음, 스킵
                                    continue
                                    
                                elif len(cells) == 2:
                                    # 2개 셀: [조건명, 상세내용] 또는 [조건명, 금리]
                                    condition_name = cell_texts[0]
                                    condition_detail = cell_texts[1]
                                    
                                elif len(cells) >= 3:
                                    # 3개 이상 셀: [조건명, 상세내용, 금리] 형태
                                    condition_name = cell_texts[0]
                                    condition_detail = cell_texts[1]
                                    
                                    # 마지막 셀에서 금리 추출
                                    rate_text = cell_texts[-1]
                                    rate_match = re.search(r'(\d+\.?\d*)\s*%?[Pp]?', rate_text)
                                    if rate_match:
                                        try:
                                            rate_value = float(rate_match.group(1))
                                            # 금리가 %P 단위인지 % 단위인지 확인
                                            if '%P' in rate_text.upper() or 'P' in rate_text.upper():
                                                additional_rate = rate_value  # %P 단위 그대로
                                            else:
                                                additional_rate = rate_value  # % 단위
                                        except:
                                            pass
                                
                                # 조건명이 없거나 너무 짧은 경우 스킵
                                if not condition_name or len(condition_name.strip()) < 2:
                                    continue
                                
                                # 조건명이 제외 키워드를 포함하는 경우 스킵
                                condition_name_lower = condition_name.lower()
                                if any(exclude in condition_name_lower for exclude in ['계약기간', '만기', '해지', '중도']):
                                    continue
                                
                                # 상세내용에서 추가 금리 정보 추출 (금리 컬럼이 별도로 없는 경우)
                                if additional_rate is None and condition_detail:
                                    detail_rate_match = re.search(r'(\d+\.?\d*)\s*%[Pp]?', condition_detail)
                                    if detail_rate_match:
                                        try:
                                            rate_value = float(detail_rate_match.group(1))
                                            if '%P' in condition_detail.upper() or 'P' in condition_detail.upper():
                                                additional_rate = rate_value
                                            else:
                                                additional_rate = rate_value
                                        except:
                                            pass
                                
                                condition_entry = {
                                    '조건': condition_name,
                                    '상세내용': condition_detail if condition_detail else condition_name,
                                    '추가금리': additional_rate
                                }
                                
                                table_conditions.append(condition_entry)
                                self.logger.info(f"  ✓ 조건 추가: {condition_name} -> {additional_rate}")
                                
                            except Exception as e:
                                self.logger.warning(f"  ⚠️ 행 {row_idx} 처리 실패: {e}")
                                continue
                        
                        if table_conditions:
                            conditions.extend(table_conditions)
                            self.logger.info(f"✅ 테이블에서 {len(table_conditions)}개 조건 추출")
                            # 첫 번째 유효한 우대조건 테이블만 사용
                            break
                    else:
                        self.logger.info(f"  ❌ 우대조건 테이블이 아님: {header_combined}")
                            
                except Exception as e:
                    self.logger.warning(f"⚠️ 테이블 {table_idx+1} 처리 실패: {e}")
                    continue
            
            self.logger.info(f"🎯 최종 우대조건 {len(conditions)}개 추출 완료")
            return conditions
            
        except Exception as e:
            self.logger.error(f"❌ 우대조건 추출 실패: {e}")
            return []
                        
            
    
    def _extract_interest_rates(self) -> Dict[str, Any]:
        """금리 정보 추출 - 오직 첫 번째 기본이율 테이블만 수집"""
        try:
            # 금리 탭 클릭
            rate_buttons = self.driver.find_elements(By.TAG_NAME, "a")
            rate_tab_clicked = False
            
            for button in rate_buttons:
                button_text = button.text.lower()
                if ('금리' in button_text and '보기' in button_text) or '오늘의 금리' in button_text:
                    try:
                        self.logger.info(f"🔄 '{button.text}' 탭 클릭")
                        button.click()
                        time.sleep(3)
                        rate_tab_clicked = True
                        break
                    except:
                        continue
            
            if not rate_tab_clicked:
                self.logger.warning("⚠️ 금리 탭을 찾지 못했습니다")
            
            basic_rates = {}
            max_rates = {}
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            self.logger.info(f"🔍 총 {len(tables)}개 테이블 검사 중...")
            
            for table_idx, table in enumerate(tables):
                try:
                    headers = table.find_elements(By.TAG_NAME, "th")
                    header_texts = [h.text.strip() for h in headers]
                    header_combined = ' '.join(header_texts).lower()
                    
                    self.logger.info(f"📋 테이블 {table_idx+1}: 헤더 = {header_combined}")
                    
                    # 명확히 제외할 테이블들
                    exclude_patterns = [
                        '우대금리', '우대조건', '항목', '적용기준', '거래우대금리',
                        '중도해지', '해지금리', '해지이율', '만기후', '만기 후',
                        '조기해지', '해약', '파기', '위반', '연체'
                    ]
                    
                    if any(pattern in header_combined for pattern in exclude_patterns):
                        self.logger.info(f"  ❌ 제외된 테이블: {header_combined}")
                        continue
                    
                    # 기본 금리 테이블 식별 키워드
                    rate_table_patterns = [
                        '기본이율', '약정이율', '이율', '기간', '계약기간', '예치기간'
                    ]
                    
                    if not any(pattern in header_combined for pattern in rate_table_patterns):
                        self.logger.info(f"  ⚠️ 금리 테이블이 아님: {header_combined}")
                        continue
                    
                    # 첫 번째 유효한 금리 테이블 처리
                    self.logger.info(f"✅ 기본이율 테이블 처리: {header_combined}")
                    
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    if len(rows) < 2:
                        self.logger.info(f"  ⚠️ 행이 부족함: {len(rows)}개")
                        continue
                    
                    processed_any_rate = False
                    
                    for row_idx, row in enumerate(rows[1:], 1):
                        try:
                            cells = row.find_elements(By.CSS_SELECTOR, "th, td")
                            if len(cells) >= 2:
                                period = cells[0].text.strip()
                                
                                # 유효한 기간인지 확인
                                if self._is_valid_rate_period(period):
                                    self.logger.info(f"    ✓ 유효한 기간: {period}")
                                    
                                    if len(cells) == 2:
                                        # 기본금리만 있는 테이블
                                        rate_text = cells[1].text.strip()
                                        rate_match = re.search(r'(\d+\.?\d*)', rate_text)
                                        if rate_match:
                                            try:
                                                rate_value = float(rate_match.group(1))
                                                if 0.01 <= rate_value <= 15.0:
                                                    basic_rates[period] = rate_text
                                                    processed_any_rate = True
                                                    self.logger.info(f"      → 기본금리: {rate_text}")
                                            except:
                                                continue
                                    elif len(cells) >= 3:
                                        # 기본금리 + 최고금리가 있는 테이블
                                        basic_rate_text = cells[1].text.strip()
                                        max_rate_text = cells[-1].text.strip()
                                        
                                        # 기본금리
                                        rate_match = re.search(r'(\d+\.?\d*)', basic_rate_text)
                                        if rate_match:
                                            try:
                                                rate_value = float(rate_match.group(1))
                                                if 0.01 <= rate_value <= 15.0:
                                                    basic_rates[period] = basic_rate_text
                                                    processed_any_rate = True
                                                    self.logger.info(f"      → 기본금리: {basic_rate_text}")
                                            except:
                                                pass
                                        
                                        # 최고금리
                                        rate_match = re.search(r'(\d+\.?\d*)', max_rate_text)
                                        if rate_match:
                                            try:
                                                rate_value = float(rate_match.group(1))
                                                if 0.01 <= rate_value <= 15.0:
                                                    max_rates[period] = max_rate_text
                                                    processed_any_rate = True
                                                    self.logger.info(f"      → 최고금리: {max_rate_text}")
                                            except:
                                                pass
                                else:
                                    self.logger.info(f"    ❌ 무효한 기간: {period}")
                        except Exception as e:
                            self.logger.warning(f"    ⚠️ 행 {row_idx} 처리 실패: {e}")
                            continue
                    
                    # 첫 번째 유효한 금리 테이블에서 데이터를 찾았으면 중단
                    if processed_any_rate:
                        self.logger.info(f"🎯 첫 번째 금리 테이블에서 데이터 추출 완료")
                        break
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ 테이블 {table_idx+1} 처리 실패: {e}")
                    continue
            
            result = {
                'basic_rates': basic_rates if basic_rates else '정보 없음',
                'max_rates': max_rates if max_rates else '정보 없음'
            }
            
            self.logger.info(f"✅ 금리 정보 추출 완료 - 기본금리: {len(basic_rates)}개, 최고금리: {len(max_rates)}개")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 금리 정보 추출 실패: {e}")
            return {'basic_rates': '정보 없음', 'max_rates': '정보 없음'}
    
    def _is_valid_rate_period(self, period: str) -> bool:
        """유효한 금리 기간인지 확인 - 중도해지 관련 키워드 강화"""
        if not period or len(period.strip()) == 0:
            return False
        
        period_lower = period.lower()
        
        # 제외할 키워드들 (중도해지 관련 키워드 추가)
        exclude_keywords = [
            '만기후', '만기 후', '해지', '중도', '위반', '연체', 
            '항목', '구분', '합계', '총', '평균', '기본금리', '최고금리',
            '우대', '추가', '가산', '혜택', '중도해지', '해지이율',
            '해지금리', '조기해지', '해약', '파기'
        ]
        
        for keyword in exclude_keywords:
            if keyword in period_lower:
                return False
        
        # 포함되어야 할 키워드들 (기간 관련)
        include_keywords = ['년', '개월', '월', '제', '일']
        has_period_keyword = any(keyword in period for keyword in include_keywords)
        
        # 숫자가 포함되어 있는지 확인
        has_number = bool(re.search(r'\d+', period))
        
        # 유효한 기간 패턴인지 확인
        valid_patterns = [
            r'\d+개월',  # 12개월, 24개월 등
            r'\d+년',    # 1년, 2년 등
            r'\d+일',    # 30일, 90일 등
            r'\d+제',    # 1제, 2제 등
        ]
        
        has_valid_pattern = any(re.search(pattern, period) for pattern in valid_patterns)
        
        return (has_period_keyword and has_number) or has_valid_pattern
    
    def _structure_period_rates(self, interest_rates) -> List[Dict[str, Any]]:
        """기간별금리 구조화"""
        period_rates = []
        
        try:
            if isinstance(interest_rates, dict):
                basic_rates_data = interest_rates.get('basic_rates', {})
                max_rates_data = interest_rates.get('max_rates', {})
                
                # 기본금리가 있는 경우
                if basic_rates_data != '정보 없음' and isinstance(basic_rates_data, dict):
                    for period, rate_str in basic_rates_data.items():
                        rate_value = self._extract_clean_rate_value(rate_str)
                        if rate_value is not None:
                            period_data = {
                                '기간': period,
                                '기본금리': rate_value
                            }
                            
                            # 해당 기간의 최고금리가 있는지 확인
                            if max_rates_data != '정보 없음' and isinstance(max_rates_data, dict):
                                max_rate_str = max_rates_data.get(period)
                                if max_rate_str:
                                    max_rate_value = self._extract_clean_rate_value(max_rate_str)
                                    if max_rate_value is not None:
                                        period_data['최고금리'] = max_rate_value
                            
                            period_rates.append(period_data)
                
                # 최고금리만 있는 기간들 추가
                if max_rates_data != '정보 없음' and isinstance(max_rates_data, dict):
                    for period, rate_str in max_rates_data.items():
                        # 이미 추가된 기간인지 확인
                        existing = next((pr for pr in period_rates if pr['기간'] == period), None)
                        if not existing:
                            rate_value = self._extract_clean_rate_value(rate_str)
                            if rate_value is not None:
                                period_data = {
                                    '기간': period,
                                    '최고금리': rate_value
                                }
                                period_rates.append(period_data)
        
        except Exception as e:
            self.logger.error(f"기간별금리 구조화 실패: {e}")
        
        return period_rates
    
    def _extract_clean_rate_value(self, rate_str: str) -> Optional[float]:
        """금리 문자열에서 숫자 값 추출"""
        try:
            if not rate_str or not isinstance(rate_str, str):
                return None
            
            rate_match = re.search(r'(\d+\.?\d*)', rate_str)
            if rate_match:
                rate_value = float(rate_match.group(1))
                if 0.01 <= rate_value <= 15.0:
                    return rate_value
            
            return None
            
        except (ValueError, TypeError):
            return None
    
    def crawl_category_products(self, category_name: str) -> List[Dict[str, Any]]:
        """특정 카테고리의 모든 상품 크롤링"""
        try:
            self.logger.info(f"\n📂 === '{category_name}' 카테고리 크롤링 시작 ===")
            
            category_products = []
            
            if not self.navigate_to_category(category_name):
                self.logger.error(f"❌ '{category_name}' 카테고리로 이동 실패")
                return []
            
            products = self.get_page_products(category_name)
            
            if not products:
                self.logger.warning(f"⚠️ '{category_name}' 카테고리에서 상품을 찾을 수 없습니다")
                return []
            
            new_products = [p for p in products if p['product_key'] not in self.processed_products]
            self.logger.info(f"📦 새로운 상품: {len(new_products)}개")
            
            for i, product in enumerate(new_products):
                try:
                    self.logger.info(f"🔍 상품 {i+1}/{len(new_products)}: '{product['title']}' 처리 중...")
                    
                    if product['product_key'] in self.processed_products:
                        continue
                    
                    # 상품 클릭
                    current_page_products = self.get_page_products(category_name)
                    current_product = None
                    for cp in current_page_products:
                        if cp['product_key'] == product['product_key']:
                            current_product = cp
                            break
                    
                    if not current_product:
                        self.processed_products.add(product['product_key'])
                        continue
                    
                    current_product['element'].click()
                    time.sleep(3)
                    
                    # 정보 추출
                    product_info = self.extract_product_info(
                        current_product['title'], 
                        current_product['product_key'],
                        category_name,
                        current_product.get('list_basic_rate'),
                        current_product.get('list_max_rate')
                    )
                    
                    category_products.append(product_info)
                    self.all_products.append(product_info)
                    
                    # 카테고리로 돌아가기
                    if not self.navigate_to_category(category_name):
                        self.navigate_to_deposits_page()
                        if not self.navigate_to_category(category_name):
                            break
                    
                except Exception as e:
                    self.logger.error(f"❌ 상품 '{product['title']}' 처리 실패: {e}")
                    self.processed_products.add(product['product_key'])
                    continue
            
            self.logger.info(f"✅ '{category_name}' 카테고리 크롤링 완료!")
            return category_products
            
        except Exception as e:
            self.logger.error(f"❌ '{category_name}' 카테고리 크롤링 중 오류: {e}")
            return []
    
    def crawl_all_categories(self) -> List[Dict[str, Any]]:
        """모든 카테고리 크롤링"""
        try:
            self.logger.info("🚀 수협은행 카테고리별 크롤링 시작!")
            
            for i, category in enumerate(self.categories, 1):
                category_name = category['name']
                self.logger.info(f"\n📂 [{i}/{len(self.categories)}] '{category_name}' 크롤링 시작")
                
                category_products = self.crawl_category_products(category_name)
                self.logger.info(f"✅ [{i}/{len(self.categories)}] '{category_name}' 완료 ({len(category_products)}개 상품)")
                
                if i < len(self.categories):
                    time.sleep(3)
            
            self.logger.info(f"\n🏁 전체 크롤링 완료! 총 {len(self.all_products)}개 상품")
            return self.all_products
            
        except Exception as e:
            self.logger.error(f"❌ 크롤링 중 오류: {e}")
            return self.all_products
    
    def save_to_json(self, filename: Optional[str] = None) -> str:
        """결과를 JSON 파일로 저장"""

        try:
            dotenv.load_dotenv()
            directory_path = os.getenv("JSON_RESULT_PATH")
            os.makedirs(directory_path, exist_ok=True)

            if not filename:
                # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # filename = f"suhyup_category_products_{timestamp}.json"
                filename = f"SH_SUHYUP.json"
            file_path = os.path.join(directory_path, filename)

            # 중복 제거
            unique_products = {}
            for product in self.all_products:
                product_name = product.get('상품명', '')
                if product_name not in unique_products:
                    unique_products[product_name] = product
            
            final_products = list(unique_products.values())
            
            # 통계 계산
            success_count = sum(1 for p in final_products if '기본금리' in p)
            
            category_stats = {}
            for product in final_products:
                category = product.get('상품카테고리', '알 수 없음')
                category_stats[category] = category_stats.get(category, 0) + 1
            
            result_data = {
                'crawl_info': {
                    'bank_name': '수협은행',
                    'crawl_date': datetime.now().isoformat(),
                    'crawl_method': '카테고리별 크롤링',
                    'target_categories': [cat['name'] for cat in self.categories],
                    'total_products': len(final_products),
                    'success_count': success_count,
                    'category_stats': category_stats
                },
                'products': final_products
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ JSON 파일 저장 완료: {filename}")
            self.logger.info(f"📊 총 {len(final_products)}개 상품")
            self.logger.info(f"📂 카테고리별 통계: {category_stats}")
            
            return filename
            
        except Exception as e:
            self.logger.error(f"❌ JSON 파일 저장 실패: {e}")
            return ""
    
    def close(self):
        """드라이버 종료"""
        if self.driver:
            self.driver.quit()
            self.logger.info("✅ 드라이버 종료 완료")

    def start(self):
        try:
            self.navigate_to_deposits_page()

            products = self.crawl_all_categories()
            saved_file = self.save_to_json()

            self.logger.info(f"\n🎉 크롤링 완료!")
            self.logger.info(f"📁 저장된 파일: {saved_file}")
            self.logger.info(f"📊 수집된 상품 수: {len(products)}개")

            if products:
                self.logger.info(f"\n📋 샘플 상품:")
                self.logger.info(f"상품명: {products[0].get('상품명')}")
                self.logger.info(f"상품카테고리: {products[0].get('상품카테고리')}")
                self.logger.info(f"기본금리: {products[0].get('기본금리')}")
                self.logger.info(f"최대금리: {products[0].get('최대금리')}")

        except Exception as e:
            self.logger.error(f"❌ 실행 중 오류: {e}")

        self.close()
