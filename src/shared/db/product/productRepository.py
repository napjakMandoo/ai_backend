import datetime
import logging
import uuid

from src.app.dto.request.request_ai_dto import ai_payload_dto, product_dto, product_period_dto
from src.shared.db.bank.BankRepository import BankRepository
from src.shared.db.util.MysqlUtil import MysqlUtil
from typing import List, Dict
from pymysql.cursors import DictCursor

'''
  "products": [
    {
      "uuid": "어쩌구 저쩌구",
      "name": "청년 도약 적금",
      "base_rate" : 2.4,
      "max_rate" : 5.2,
      "type" : "Savings" ,
      "max_amount" : 500000000,
      "min_amount" : 1000000,
      "max_amount_per_month" : -1,
      "min_amount_per_month" : -1,
      "max_amount_per_day" : 5000000,
      "min_amount_per_day": 10000,
      "tax_benefit" : "비과세종합저축",
      "product_period": [
        {
          "period" : "[-,3]",
          "basic_rate" : 2.2
        },
        {
          "period" : "[3,6]",
          "basic_rate" : 2.3
        },
        {
          "period" : "[6, -]",
          "basic_rate" : 2.4
        }
      ]
    },
'''

class ProductRepository:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mysqlUtil = MysqlUtil()
        self.BankRepository = BankRepository()

    def build_ai_payload(self, connection, top_n: int = 20) -> ai_payload_dto:
        SQL = """
              WITH topN AS (SELECT bp.product_uuid, \
                                   bp.name, \
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
              SELECT t.product_uuid, \
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
                     pp.period     AS product_period, \
                     pp.bank_rate AS product_basic_rate
              FROM topN t
                       JOIN product_period pp
                            ON pp.product_uuid = t.product_uuid
              ORDER BY t.maximum_rate DESC, t.product_uuid, pp.period \
              """

        with connection.cursor(DictCursor) as cursor:
            cursor.execute(SQL, (top_n,))
            rows = cursor.fetchall()

        products: Dict[str, product_dto] = {}

        for r in rows:
            pid = r["product_uuid"]

            if pid not in products:
                products[pid] = product_dto(
                    uuid=pid,
                    name=r["name"],
                    base_rate=float(r["basic_rate"]),
                    max_rate=float(r["max_rate"]),
                    type=r["type"],
                    max_amount=int(r["max_amount"]),
                    min_amount=int(r["min_amount"]),
                    max_amount_per_month=int(r["max_amount_per_month"]) if r[
                                                                               "max_amount_per_month"] is not None else -1,
                    min_amount_per_month=int(r["min_amount_per_month"]) if r["min_amount_per_month"] is not None else 0,
                    max_amount_per_day=int(r["max_amount_per_day"]),
                    min_amount_per_day=int(r["min_amount_per_day"]),
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

    def check_is_deleted(self, bank_name:str, new_products_name:set, connection):

        self.logger.info("=====삭제 작업 시작=====")

        cursor = connection.cursor()
        try:
            bank_uuid = self.BankRepository.get_uuid_by_bank_name(bank_name=bank_name)
            if bank_uuid is None:
                self.logger.error(f"Bank UUID 가 없음: {bank_name}")
                return

            bank_uuid_bytes = bank_uuid.bytes
            existing_products_name = set()

            cursor.execute("select name from bank_product where bank_uuid=%s", (bank_uuid_bytes,))
            for row in cursor.fetchall():
                existing_products_name.add(row[0])

            deleted_target_set = existing_products_name.difference(new_products_name)
            self.logger.info(f"중복된 상품 수 : {len(deleted_target_set)}")
            if deleted_target_set:
                cursor.execute("update bank_product set deleted_at = %s where name in %s",
                               (datetime.datetime.now(), tuple(deleted_target_set)))
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

        product_name:str = product_data.product_name
        product_basic_rate:float = product_data.product_basic_rate
        product_max_rate:float = product_data.product_max_rate
        product_type:str = product_data.product_type
        product_url_links:str = product_data.product_url_links
        product_info: str = "\\".join(product_data.product_info) # list[str] 형태로 반환되나 "\"로 합쳐서 넣음
        product_maximum_amount:int = product_data.product_maximum_amount
        product_minimum_amount:int = product_data.product_minimum_amount
        product_maximum_amount_per_day:int= product_data.product_maximum_amount_per_day
        product_minimum_amount_per_day:int = product_data.product_minimum_amount_per_day
        product_maximum_amount_per_month:int = product_data.product_maximum_amount_per_day
        product_minimum_amount_per_month:int = product_data.product_minimum_amount_per_day
        product_sub_target: str = product_data.product_sub_target
        product_sub_amount: str = product_data.product_sub_amount
        product_sub_way: str = product_data.product_sub_way
        product_sub_term: str = product_data.product_sub_term
        product_tax_benefit: str = product_data.product_tax_benefit
        product_preferential_info: str = product_data.product_preferential_info

        preferential_conditions_detail_header: list[str] = product_data.preferential_conditions_detail_header
        preferential_conditions_detail_detail: list[str] = product_data.preferential_conditions_detail_detail
        preferential_conditions_detail_interest_rate: list[float] = product_data.preferential_conditions_detail_interest_rate
        preferential_conditions_detail_keyword: list[str] = product_data.preferential_conditions_detail_keyword

        product_period_period: list[str] = product_data.product_period_period
        product_period_base_rate: list[float] = product_data.product_period_base_rate

        if self.check_duplicate_product(product_name=product_name, connection=connection):
            self.logger.info("이미 존재하는 상품입니다.")
            return

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
            ###################################################################################
            self.logger.info("preferential_condition_detail 테이블 데이터 삽입 시작")
            preferential_condition_detail_insert_sql = ("INSERT INTO preferential_condition_detail (detail_uuid, product_uuid, header, detail,  interest_rate, keyword) VALUES (%s, %s, %s, %s, %s, %s)")

            for i in range(len(preferential_conditions_detail_header)):
                preferential_condition_detail_uuid = uuid.uuid4().bytes
                header = preferential_conditions_detail_header[i]
                detail = preferential_conditions_detail_detail[i]
                interest_rate = preferential_conditions_detail_interest_rate[i]
                keyword = preferential_conditions_detail_keyword[i]

                params = (preferential_condition_detail_uuid, product_uuid, header, detail, interest_rate, keyword)
                cursor.execute(preferential_condition_detail_insert_sql, params)

            self.logger.info("preferential_condition_detail 테이블 데이터 삽입 끝")
            ###################################################################################
            self.logger.info("product_period 테이블 데이터 삽입 시작")

            period_insert_sql = ("INSERT INTO product_period (period_uuid, product_uuid, period, bank_rate) VALUES (%s, %s, %s, %s)")

            for i in range(len(product_period_period)):
                period_uuid = uuid.uuid4().bytes
                period = product_period_period[i]
                base_rate = product_period_base_rate[i]

                params = (period_uuid, product_uuid, period, base_rate)
                cursor.execute(period_insert_sql, params)

            self.logger.info("product_period 테이블 데이터 삽입 끝")
            connection.commit()


        except Exception as e:
            self.logger.error(f"상품 데이터 삽입 에러 발생: roll back: {e}")
            self.logger.error(f"product_uuid: {product_uuid}, bank_uuid: {bank_uuid}, product_basic_rate:{product_period_base_rate}")
            self.logger.error(f"product_maximum_amount: {product_maximum_amount}, product_maximum_amount_per_month: {product_maximum_amount_per_month}, product_maximum_amount_per_day:{product_maximum_amount_per_day}")
            self.logger.error(f"product_minimum_amount: {product_minimum_amount}, product_minimum_amount_per_month: {product_minimum_amount_per_month}, product_minimum_amount_per_day:{product_minimum_amount_per_day}")
            self.logger.error(f"product_name: {product_name}, product_info: {product_info}, product_preferential_info:{product_preferential_info}")
            self.logger.error(f"product_sub_amount: {product_sub_amount}, product_sub_target: {product_sub_target}, product_sub_term:{product_sub_term}")
            self.logger.error(f"product_sub_way: {product_sub_way}, product_tax_benefit: {product_tax_benefit}, product_url_links:{product_url_links}, product_type:{product_type}")
            self.logger.error(f"preferential_conditions_detail_header: {preferential_conditions_detail_header}, preferential_conditions_detail_detail: {preferential_conditions_detail_detail}")
            self.logger.error(f"preferential_conditions_detail_interest_rate: {preferential_conditions_detail_interest_rate}, preferential_conditions_detail_keyword: {preferential_conditions_detail_keyword}")
            self.logger.error(f"product_period_period: {product_period_period}, product_period_base_rate: {product_period_base_rate}")
            raise e
        finally:
            cursor.close()


