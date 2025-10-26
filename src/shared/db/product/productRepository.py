import datetime
import logging
import uuid

from src.app.dto.request.request_ai_dto import ai_payload_dto, product_dto, product_period_dto
from src.shared.db.bank.BankRepository import BankRepository
from src.shared.db.util.MysqlUtil import MysqlUtil
from typing import List, Dict
from pymysql.cursors import DictCursor
import re
import ast
import datetime

class ProductRepository:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mysqlUtil = MysqlUtil()
        self.BankRepository = BankRepository()

    def build_ai_payload(self, connection, top_n: int = 20) -> ai_payload_dto:
        SQL = """
              WITH topN AS (SELECT bp.product_uuid, \
                                   bp.name, \
                                   bp.bank_uuid, \
                                   bp.basic_rate, \
                                   bp.max_rate, \
                                   bp.type, \
                                   bp.maximum_amount, \
                                   bp.maximum_amount_per_month, \
                                   bp.maximum_amount_per_day, \
                                   bp.minimum_amount, \
                                   bp.minimum_amount_per_month, \
                                   bp.minimum_amount_per_day, \
                                   bp.tax_benefit, \
                                   bp.preferential_info, \
                                   bp.sub_amount, \
                                   bp.sub_target, \
                                   bp.sub_term, \
                                   bp.sub_way \
                            FROM bank_product bp \
                            WHERE bp.deleted_at IS NULL \
                            ORDER BY bp.max_rate DESC
                  LIMIT %s
                  )
              SELECT BIN_TO_UUID(t.product_uuid) AS product_uuid,
                     b.bank_name                 AS bank_name,
                     t.name, \
                     t.basic_rate, \
                     t.max_rate, \
                     t.type, \
                     t.maximum_amount, \
                     t.maximum_amount_per_month, \
                     t.maximum_amount_per_day, \
                     t.minimum_amount, \
                     t.minimum_amount_per_month, \
                     t.minimum_amount_per_day, \
                     t.tax_benefit, \
                     t.preferential_info, \
                     t.sub_amount, \
                     t.sub_target, \
                     t.sub_term, \
                     t.sub_way, \
                     pp.period                   AS product_period, \
                     pp.bank_rate                AS product_basic_rate
              FROM topN t
                       JOIN product_period pp
                            ON pp.product_uuid = t.product_uuid
                       JOIN bank b
                            ON b.bank_uuid = t.bank_uuid
              ORDER BY t.max_rate DESC, t.product_uuid, pp.period \
              """
        with connection.cursor(DictCursor) as cursor:
            cursor.execute(SQL, (top_n,))
            rows = cursor.fetchall()

        products: Dict[str, product_dto] = {}

        for r in rows:
            pid = r["product_uuid"]

            if pid not in products:
                products[pid] = product_dto(
                    product_uuid=pid,
                    name=r["name"],
                    base_rate=float(r["basic_rate"]),
                    max_rate=float(r["max_rate"]),
                    type=r["type"],
                    bank_name=r["bank_name"],

                    maximum_amount=int(r["maximum_amount"]),
                    minimum_amount=int(r["minimum_amount"]),
                    maximum_amount_per_month=int(r["maximum_amount_per_month"]) if r[
                                                                                       "maximum_amount_per_month"] is not None else -1,
                    minimum_amount_per_month=int(r["minimum_amount_per_month"]) if r[
                                                                                       "minimum_amount_per_month"] is not None else 0,
                    maximum_amount_per_day=int(r["maximum_amount_per_day"]) if r[
                                                                                   "maximum_amount_per_day"] is not None else -1,
                    minimum_amount_per_day=int(r["minimum_amount_per_day"]) if r[
                                                                                   "minimum_amount_per_day"] is not None else 0,

                    tax_benefit=r["tax_benefit"] or "",
                    preferential_info=r["preferential_info"] or "",
                    sub_amount=r["sub_amount"] or "",
                    sub_term=r["sub_term"] or "",
                    product_period=[],
                )

            products[pid].product_period.append(
                product_period_dto(
                    period=r["product_period"],
                    basic_rate=float(r["product_basic_rate"]),
                )
            )

        return ai_payload_dto(
            tax_rate=15.0,  # 고정
            products=list(products.values())
        )

    # 테스트 용도
    def print_product_by_uuid(self, product_uuid: str, connection):
        uid_bytes = uuid.UUID(product_uuid).bytes  # 문자열 UUID -> 16바이트
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT * FROM bank_product WHERE product_uuid = %s",
                (uid_bytes,)
            )
            for row in cursor.fetchall():
                print(row)
        finally:
            cursor.close()

    # 테스트 용도
    def delete_all_product(self):
        self.logger.info("상품 관련 데이터 삭제 시작")
        delete_all_product_period_query = "delete from product_period"
        delete_all_product_detail_query = "delete from preferential_condition_detail"
        delete_all_product_query = "delete from bank_product"

        mysql_connection = self.mysqlUtil.get_connection()
        mysql_cursor = mysql_connection.cursor()
        mysql_cursor.execute(delete_all_product_detail_query)
        mysql_cursor.execute(delete_all_product_period_query)
        mysql_cursor.execute(delete_all_product_query)
        mysql_connection.commit()
        mysql_cursor.close()
        mysql_connection.close()
        self.logger.info("상품 관련 데이터 삭제 끝")

    def check_is_deleted(self, bank_name: str, new_products_name: set, connection):
        self.logger.info("=====삭제 작업 시작=====")
        cursor = connection.cursor()
        try:
            bank_uuid = self.BankRepository.get_uuid_by_bank_name(bank_name=bank_name)
            if bank_uuid is None:
                self.logger.error(f"Bank UUID 가 없음: {bank_name}")
                return

            bank_uuid_bytes = bank_uuid.bytes

            cursor.execute("SELECT name FROM bank_product WHERE bank_uuid = %s", (bank_uuid_bytes,))
            existing_products_name = {row[0] for row in cursor.fetchall()}
            for name in existing_products_name:
                print(name)

            deleted_target_set = existing_products_name.difference(new_products_name)
            self.logger.info(f"삭제 대상 상품 수: {len(deleted_target_set)}")

            if deleted_target_set:
                placeholders = ', '.join(['%s'] * len(deleted_target_set))
                query = f"UPDATE bank_product SET deleted_at = %s WHERE name IN ({placeholders})"
                cursor.execute(query, (datetime.datetime.now(), *deleted_target_set))
                connection.commit()
                self.logger.info("삭제 상태 업데이트 완료")
            else:
                self.logger.info("삭제 대상 없음, 업데이트 생략")

        except Exception as e:
            connection.rollback()
            self.logger.exception("삭제 처리 중 오류 발생, 롤백 수행")
        finally:
            cursor.close()
            self.logger.info("=====삭제 작업 끝=====")

    def check_duplicate_product(self, product_name, connection):

        self.logger.info("중복 상품 검사 시작")
        cursor = connection.cursor()
        cursor.execute("select name from bank_product where name=%s", product_name)
        row = cursor.fetchone()
        if row:
            self.logger.info("중복 상품 검사 끝")
            cursor.close()
            return True
        else:
            self.logger.info("중복 상품 검사 끝")
            cursor.close()
            return False

    def save_one_product(self, product_data, bank_name, connection):
        self.logger.info("상품 데이터 삽입 시작")

        validation_result = self._validate_product_data_safe(product_data)
        if not validation_result['valid']:
            self.logger.warning(f"데이터 검증 실패로 상품 삽입 건너뜀: {validation_result['reason']}")
            return False
        product_name: str = product_data.product_name
        product_basic_rate: float = product_data.product_basic_rate
        product_max_rate: float = product_data.product_max_rate

        if product_basic_rate <= 0 or product_max_rate <= 0:
            self.logger.warning(
                f"금리가 0 이하로 상품 삽입 건너뜀 - 상품명: {product_name}, 기본금리: {product_basic_rate}, 최대금리: {product_max_rate}")
            return False

        product_type: str = product_data.product_type
        product_url_links: str = BankRepository().get_url_by_bank_name(bank_name=bank_name)
        product_info: str = "\\".join(product_data.product_info) if isinstance(product_data.product_info,
                                                                               list) else str(product_data.product_info)
        self.logger.info("=== INFO 필드 데이터 로깅 ===")
        self.logger.info(f"원본 product_info 타입: {type(product_data.product_info)}")
        self.logger.info(f"원본 product_info 값: {product_data.product_info}")
        self.logger.info(f"처리된 product_info (DB 저장용): {product_info}")
        self.logger.info(f"처리된 product_info 길이: {len(product_info) if product_info else 0}자")
        if product_info and len(product_info) > 100:
            self.logger.info(f"product_info 미리보기 (처음 100자): {product_info[:100]}...")
        self.logger.info("=== INFO 필드 로깅 끝 ===")

        product_maximum_amount: int = product_data.product_maximum_amount
        product_minimum_amount: int = product_data.product_minimum_amount

        product_maximum_amount_per_day: int = product_data.product_maximum_amount_per_day
        product_minimum_amount_per_day: int = product_data.product_minimum_amount_per_day
        product_maximum_amount_per_month: int = product_data.product_maximum_amount_per_month
        product_minimum_amount_per_month: int = product_data.product_minimum_amount_per_month

        product_sub_target: str = product_data.product_sub_target
        product_sub_amount: str = product_data.product_sub_amount
        product_sub_way: str = product_data.product_sub_way
        product_sub_term: str = product_data.product_sub_term
        product_tax_benefit: str = product_data.product_tax_benefit
        product_preferential_info: str = product_data.product_preferential_info

        preferential_conditions_detail_header: list[str] = validation_result['safe_preferential']['header']
        preferential_conditions_detail_detail: list[str] = validation_result['safe_preferential']['detail']
        preferential_conditions_detail_interest_rate: list[float] = validation_result['safe_preferential']['rate']
        preferential_conditions_detail_keyword: list[str] = validation_result['safe_preferential']['keyword']

        product_period_period: list[str] = validation_result['safe_period']['period']
        product_period_base_rate: list[float] = validation_result['safe_period']['rate']

        if self.check_duplicate_product(product_name=product_name, connection=connection):
            self.logger.info("이미 존재하는 상품입니다.")
            return True  # 중복이므로 성공으로 간주

        try:
            connection.begin()
            cursor = connection.cursor()
            product_uuid = uuid.uuid4().bytes
            bank_uuid = self.BankRepository.get_uuid_by_bank_name(bank_name=bank_name)
            if bank_uuid is None:
                error_msg = f"Bank UUID가 존재하지 않음: {bank_name}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            bank_uuid_bytes = bank_uuid.bytes

            self.logger.info("bank_product 테이블 데이터 삽입 시작")
            product_insert_sql = (
                "INSERT INTO bank_product ("
                "  product_uuid, bank_uuid, basic_rate, max_rate, maximum_amount,"
                "  maximum_amount_per_day, maximum_amount_per_month, minimum_amount,"
                "  minimum_amount_per_day, minimum_amount_per_month, info, name,"
                "  preferential_info, sub_amount, sub_target, sub_term, sub_way,"
                "  tax_benefit, url_link, type"
                ") VALUES ("
                "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
                " %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
                ")"
            )

            params = (
                product_uuid, bank_uuid_bytes, product_basic_rate, product_max_rate,
                product_maximum_amount, product_maximum_amount_per_day,
                product_maximum_amount_per_month, product_minimum_amount,
                product_minimum_amount_per_day, product_minimum_amount_per_month,
                product_info, product_name, product_preferential_info,
                product_sub_amount, product_sub_target, product_sub_term,
                product_sub_way, product_tax_benefit, product_url_links,
                product_type
            )

            cursor.execute(product_insert_sql, params)
            self.logger.info("bank_product 테이블 데이터 삽입 끝")

            self.logger.info("preferential_condition_detail 테이블 데이터 삽입 시작")

            if preferential_conditions_detail_header:
                preferential_condition_detail_insert_sql = (
                    "INSERT INTO preferential_condition_detail "
                    "(detail_uuid, product_uuid, header, detail, interest_rate, keyword) "
                    "VALUES (%s, %s, %s, %s, %s, %s)"
                )

                for i in range(len(preferential_conditions_detail_header)):
                    preferential_condition_detail_uuid = uuid.uuid4().bytes
                    header = preferential_conditions_detail_header[i]
                    detail = preferential_conditions_detail_detail[i]
                    interest_rate = preferential_conditions_detail_interest_rate[i]
                    keyword = preferential_conditions_detail_keyword[i]

                    params = (preferential_condition_detail_uuid, product_uuid, header, detail, interest_rate, keyword)
                    cursor.execute(preferential_condition_detail_insert_sql, params)

                self.logger.info(f"preferential_condition_detail {len(preferential_conditions_detail_header)}개 삽입 완료")
            else:
                self.logger.info("우대조건이 없어 preferential_condition_detail 삽입 건너뜀")

            self.logger.info("product_period 테이블 데이터 삽입 시작")

            if product_period_period and product_period_base_rate:
                period_insert_sql = (
                    "INSERT INTO product_period (period_uuid, product_uuid, period, bank_rate) "
                    "VALUES (%s, %s, %s, %s)"
                )

                for i in range(len(product_period_period)):
                    period_uuid = uuid.uuid4().bytes
                    period = product_period_period[i]
                    base_rate = product_period_base_rate[i]

                    params = (period_uuid, product_uuid, period, base_rate)
                    cursor.execute(period_insert_sql, params)

                self.logger.info(f"product_period {len(product_period_period)}개 삽입 완료")
            else:
                self.logger.info("기간 데이터가 없어 product_period 삽입 건너뜀")

            connection.commit()
            self.logger.info("상품 데이터 삽입 성공")
            return True

        except Exception as e:
            self.logger.error(f"상품 데이터 삽입 에러 발생: roll back: {e}")
            self._log_detailed_error_info(
                product_uuid, bank_uuid, product_basic_rate, product_period_base_rate,
                product_maximum_amount, product_maximum_amount_per_month, product_maximum_amount_per_day,
                product_minimum_amount, product_minimum_amount_per_month, product_minimum_amount_per_day,
                product_name, product_info, product_preferential_info,
                product_sub_amount, product_sub_target, product_sub_term,
                product_sub_way, product_tax_benefit, product_url_links, product_type,
                preferential_conditions_detail_header, preferential_conditions_detail_detail,
                preferential_conditions_detail_interest_rate, preferential_conditions_detail_keyword,
                product_period_period,
            )
            connection.rollback()
            return False  # 실패
        finally:
            cursor.close()

    def _normalize_period_data(self, period_data) -> list[str]:

        if not period_data:
            return []

        # 단일 문자열을 리스트로 통일
        if isinstance(period_data, str):
            period_data = [period_data]

        normalized = []
        for raw_period in period_data:
            text = str(raw_period).strip()

            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1].strip()

            if re.fullmatch(r'\[\s*-?\d+\s*,\s*-?\d+\s*\]', text):
                fixed = re.sub(r'-1', '-', text)  # -1 → -
                normalized.append(fixed)
                continue

            if re.fullmatch(r'\d+\s*,\s*-?\d+', text):
                parts = [p.strip().replace('-1', '-') for p in text.split(',')]
                normalized.append(f"[{parts[0]}, {parts[1]}]")
                continue

            if text.startswith('[') and text.endswith(']'):
                try:
                    parsed = ast.literal_eval(text)
                    if isinstance(parsed, list) and len(parsed) == 2:
                        left = str(parsed[0]).strip().replace('-1', '-')
                        right = str(parsed[1]).strip().replace('-1', '-')
                        if re.fullmatch(r'[\d-]+', left) and re.fullmatch(r'[\d-]+', right):
                            normalized.append(f"[{left}, {right}]")
                            continue
                except Exception:
                    pass  # eval 실패 → 무시

            if re.fullmatch(r'\d+', text):
                normalized.append(f"[{text}, {text}]")
                continue

            self.logger.warning(f"⚠️ 잘못된 period 형식 감지: {text} → 건너뜀")
            continue

        return normalized

    def _validate_product_data_safe(self, product_data) -> dict:
        """
        product_data의 안전 검증 수행 (유연하게 스킵 가능)
        period 부분에 _normalize_period_data()를 적용해 형식 통일
        """

        self.logger.info("상품 데이터 안전 검증 시작")

        result = {
            'valid': True,
            'reason': '',
            'safe_preferential': {'header': [], 'detail': [], 'rate': [], 'keyword': []},
            'safe_period': {'period': [], 'rate': []}
        }

        # 1️⃣ 필수 필드 검증
        required_fields = ['product_name', 'product_basic_rate', 'product_max_rate', 'product_type']
        for field in required_fields:
            if not hasattr(product_data, field) or getattr(product_data, field) is None:
                result['valid'] = False
                result['reason'] = f"필수 필드 누락: {field}"
                return result

        # 2️⃣ 우대조건 검증
        pref_arrays = {
            'header': getattr(product_data, 'preferential_conditions_detail_header', []) or [],
            'detail': getattr(product_data, 'preferential_conditions_detail_detail', []) or [],
            'rate': getattr(product_data, 'preferential_conditions_detail_interest_rate', []) or [],
            'keyword': getattr(product_data, 'preferential_conditions_detail_keyword', []) or []
        }

        pref_lengths = [len(arr) for arr in pref_arrays.values()]
        if pref_lengths and not all(length == pref_lengths[0] for length in pref_lengths):
            self.logger.warning(f"우대조건 배열 길이 불일치로 건너뜀: {pref_lengths}")
            result['safe_preferential'] = {'header': [], 'detail': [], 'rate': [], 'keyword': []}
        else:
            safe_details = []
            for detail in pref_arrays['detail']:
                if detail and len(detail) > 200:
                    truncated = detail[:197] + '...'
                    self.logger.warning(f"우대조건 상세 내용 자동 잘라내기: {len(detail)} → {len(truncated)}자")
                    safe_details.append(truncated)
                else:
                    safe_details.append(detail)

            result['safe_preferential'] = {
                'header': pref_arrays['header'],
                'detail': safe_details,
                'rate': pref_arrays['rate'],
                'keyword': pref_arrays['keyword']
            }

        # 3️⃣ 기간(period) 검증
        period_data = getattr(product_data, 'product_period_period', []) or []
        rate_data = getattr(product_data, 'product_period_base_rate', []) or []

        normalized_period = self._normalize_period_data(period_data)
        valid_periods = []

        for p in normalized_period:
            # 한글 포함 → 무효 처리
            if any(word in p for word in ['미만', '이상', '이하', '개월', '년']):
                self.logger.warning(f"❌ 치명적인 period 형식 발견: {p} → 전체 무효 처리")
                normalized_period = []
                valid_periods = []
                break

            # 정규식으로 최종 검증 ([숫자|-], [숫자|-])
            if re.fullmatch(r'\[\s*(\d+|-)\s*,\s*(\d+|-)\s*\]', p):
                valid_periods.append(p)
            else:
                self.logger.warning(f"❌ 비정상 period 필터링됨: {p}")

        # 길이 불일치 시 rate도 동일하게 스킵
        if len(valid_periods) != len(rate_data):
            self.logger.warning(f"기간/금리 배열 길이 불일치 → 전체 무효화: period={len(valid_periods)}, rate={len(rate_data)}")
            result['safe_period'] = {'period': [], 'rate': []}
        else:
            result['safe_period'] = {'period': valid_periods, 'rate': rate_data}

        # 4️⃣ 텍스트 길이 검증
        text_limits = {
            'product_name': 100,
            'product_sub_target': 300,
            'product_sub_amount': 200,
            'product_sub_way': 200,
            'product_sub_term': 200,
            'product_tax_benefit': 500,
            'product_preferential_info': 1000
        }

        for field, limit in text_limits.items():
            if hasattr(product_data, field):
                value = getattr(product_data, field)
                if value and isinstance(value, str) and len(value) > limit:
                    self.logger.warning(f"{field} 길이 초과 (처리는 계속): {len(value)} > {limit}")

        self.logger.info("상품 데이터 안전 검증 완료")
        return result

    def _validate_product_data(self, product_data) -> None:

        self.logger.info("상품 데이터 검증 시작")

        required_fields = ['product_name', 'product_basic_rate', 'product_max_rate', 'product_type']
        for field in required_fields:
            if not hasattr(product_data, field) or getattr(product_data, field) is None:
                raise ValueError(f"필수 필드 누락: {field}")

        pref_arrays = {
            'header': getattr(product_data, 'preferential_conditions_detail_header', []) or [],
            'detail': getattr(product_data, 'preferential_conditions_detail_detail', []) or [],
            'rate': getattr(product_data, 'preferential_conditions_detail_interest_rate', []) or [],
            'keyword': getattr(product_data, 'preferential_conditions_detail_keyword', []) or []
        }

        pref_lengths = [len(arr) for arr in pref_arrays.values()]
        if not all(length == pref_lengths[0] for length in pref_lengths):
            self.logger.error(f"우대조건 배열 길이 불일치: {pref_lengths}")
            self.logger.error(f"header: {len(pref_arrays['header'])}, detail: {len(pref_arrays['detail'])}")
            self.logger.error(f"rate: {len(pref_arrays['rate'])}, keyword: {len(pref_arrays['keyword'])}")
            raise ValueError(f"우대조건 배열 길이가 일치하지 않음: {pref_lengths}")

        period_data = getattr(product_data, 'product_period_period', []) or []
        rate_data = getattr(product_data, 'product_period_base_rate', []) or []

        if isinstance(period_data, str):
            period_length = 1
        else:
            period_length = len(period_data) if period_data else 0

        rate_length = len(rate_data) if rate_data else 0

        if period_length != rate_length:
            self.logger.error(f"기간/금리 배열 길이 불일치: period={period_length}, rate={rate_length}")
            self.logger.error(f"period_data: {period_data}")
            self.logger.error(f"rate_data: {rate_data}")
            raise ValueError(f"기간/금리 배열 길이가 일치하지 않음: period={period_length}, rate={rate_length}")

        if period_data:
            if isinstance(period_data, list):
                for i, period in enumerate(period_data):
                    if any(word in str(period) for word in ['미만', '이상', '이하', '개월', '년']):
                        self.logger.error(f"잘못된 period 형식 발견: index={i}, value='{period}'")
                        raise ValueError(f"period에 한국어 포함됨: '{period}' (index: {i})")
            elif isinstance(period_data, str):
                if any(word in period_data for word in ['미만', '이상', '이하', '개월', '년']):
                    self.logger.error(f"잘못된 period 형식 발견: '{period_data}'")
                    raise ValueError(f"period에 한국어 포함됨: '{period_data}'")

        text_limits = {
            'product_name': 100,
            'product_sub_target': 300,
            'product_sub_amount': 200,
            'product_sub_way': 200,
            'product_sub_term': 200,
            'product_tax_benefit': 500,
            'product_preferential_info': 1000
        }

        for field, limit in text_limits.items():
            if hasattr(product_data, field):
                value = getattr(product_data, field)
                if value and isinstance(value, str) and len(value) > limit:
                    self.logger.warning(f"{field} 길이 초과: {len(value)} > {limit}")
                    # 자동 잘라내기 (선택사항)
                    # setattr(product_data, field, value[:limit-3] + '...')

        # 6. preferential_conditions_detail_detail 개별 항목 길이 검증
        detail_array = pref_arrays['detail']
        for i, detail in enumerate(detail_array):
            if detail and len(detail) > 200:
                self.logger.error(f"preferential_conditions_detail_detail[{i}] 길이 초과: {len(detail)} > 200")
                self.logger.error(f"내용: '{detail}'")
                raise ValueError(f"우대조건 상세 내용이 너무 김 (index {i}): {len(detail)} > 200자")

        self.logger.info("상품 데이터 검증 완료")

    def _normalize_period_data(self, period_data) -> list[str]:
        if not period_data:
            return []

        if isinstance(period_data, str):
            return [period_data]
        elif isinstance(period_data, list):
            return period_data
        else:
            self.logger.warning(f"예상치 못한 period 데이터 타입: {type(period_data)}")
            return [str(period_data)]

    def _log_detailed_error_info(self, product_uuid, bank_uuid, product_basic_rate, product_period_base_rate,
                                 product_maximum_amount, product_maximum_amount_per_month,
                                 product_maximum_amount_per_day,
                                 product_minimum_amount, product_minimum_amount_per_month,
                                 product_minimum_amount_per_day,
                                 product_name, product_info, product_preferential_info,
                                 product_sub_amount, product_sub_target, product_sub_term,
                                 product_sub_way, product_tax_benefit, product_url_links, product_type,
                                 preferential_conditions_detail_header, preferential_conditions_detail_detail,
                                 preferential_conditions_detail_interest_rate, preferential_conditions_detail_keyword,
                                 product_period_period):

        self.logger.error("=== 상품 데이터 삽입 실패 상세 정보 ===")
        self.logger.error(f"product_uuid: {product_uuid}, bank_uuid: {bank_uuid}")
        self.logger.error(f"product_basic_rate: {product_basic_rate}, period_base_rate: {product_period_base_rate}")
        self.logger.error(
            f"amounts - max: {product_maximum_amount}, max_month: {product_maximum_amount_per_month}, max_day: {product_maximum_amount_per_day}")
        self.logger.error(
            f"amounts - min: {product_minimum_amount}, min_month: {product_minimum_amount_per_month}, min_day: {product_minimum_amount_per_day}")
        self.logger.error(f"기본 정보 - name: '{product_name}', type: '{product_type}', url: '{product_url_links}'")
        self.logger.error(f"설명 - info: '{product_info}', preferential_info: '{product_preferential_info}'")
        self.logger.error(
            f"가입조건 - target: '{product_sub_target}', amount: '{product_sub_amount}', term: '{product_sub_term}', way: '{product_sub_way}'")
        self.logger.error(f"세제혜택: '{product_tax_benefit}'")

        # 🚨 CRITICAL: 배열 길이 정보 추가
        self.logger.error("=== 배열 길이 정보 ===")
        self.logger.error(
            f"preferential arrays - header: {len(preferential_conditions_detail_header)}, detail: {len(preferential_conditions_detail_detail)}")
        self.logger.error(
            f"preferential arrays - rate: {len(preferential_conditions_detail_interest_rate)}, keyword: {len(preferential_conditions_detail_keyword)}")
        self.logger.error(
            f"period arrays - period: {len(product_period_period)}, base_rate: {len(product_period_base_rate)}")

        # 배열 내용 출력 (처음 3개만)
        self.logger.error(f"preferential_header (처음3개): {preferential_conditions_detail_header[:3]}")
        self.logger.error(
            f"preferential_detail (처음3개): {[d[:50] + '...' if len(d) > 50 else d for d in preferential_conditions_detail_detail[:3]]}")
        self.logger.error(f"period_period: {product_period_period}")
        self.logger.error(f"period_base_rate: {product_period_base_rate}")
        self.logger.error("=== 상세 정보 끝 ===")

        # ===== 에러 상황에서도 INFO 필드 로깅 =====
        self.logger.error("=== 에러 발생 시 INFO 필드 상세 로깅 ===")
        self.logger.error(f"product_info 타입: {type(product_info)}")
        self.logger.error(f"product_info 길이: {len(product_info) if product_info else 0}자")
        self.logger.error(f"product_info 전체 내용: {product_info}")
        self.logger.error("=== 에러 시 INFO 필드 로깅 끝 ===")