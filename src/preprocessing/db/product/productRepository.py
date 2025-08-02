import logging
import uuid
from src.preprocessing.db.bank.BankRepository import BankRepository
from src.preprocessing.db.util.MysqlUtil import MysqlUtil


class ProductRepository:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mysqlUtil = MysqlUtil()
        self.BankRepository = BankRepository()

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


    def check_duplicate_product(self, product_name, connection):
        cursor = connection.cursor()
        cursor.execute("select name from bank_product where name=%s", product_name)
        row = cursor.fetchone()
        if row:
            return True
        else:
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
            bank_uuid = self.BankRepository.get_uuid_by_bank_name(bank_name=bank_name).bytes

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
                product_uuid, bank_uuid, product_basic_rate, product_max_rate,
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


