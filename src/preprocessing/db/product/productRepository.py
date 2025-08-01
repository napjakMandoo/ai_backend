import logging
import uuid
from src.preprocessing.db.bank.BankRepository import BankRepository
from src.preprocessing.db.util.MysqlUtil import MysqlUtil


class ProductRepository:

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mysqlUtil = MysqlUtil()
        self.BankRepository = BankRepository()

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


        try:
            connection.begin()
            cursor = connection.cursor()
            # product_uuid 생성해야함
            product_uuid = uuid.uuid4().bytes

            # bank로 부터 uuid 가져와야함
            bank_uuid = self.BankRepository.get_uuid_by_bank_name(bank_name=bank_name).bytes

            sql = (
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

            cursor.execute(sql, params)
            connection.commit()
            self.logger.info("상품 데이터 삽입 끝")
        except Exception as e:
            self.logger.error(f"상품 데이터 삽입 에러 발생: roll back: {e}")
            self.logger.error(f"product_uuid: {product_uuid}, bank_uuid: {bank_uuid}, product_basic_rate:{product_period_base_rate}")
            self.logger.error(f"product_maximum_amount: {product_maximum_amount}, product_maximum_amount_per_month: {product_maximum_amount_per_month}, product_maximum_amount_per_day:{product_maximum_amount_per_day}")
            self.logger.error(f"product_minimum_amount: {product_minimum_amount}, product_minimum_amount_per_month: {product_minimum_amount_per_month}, product_minimum_amount_per_day:{product_minimum_amount_per_day}")
            self.logger.error(f"product_name: {product_name}, product_info: {product_info}, product_preferential_info:{product_preferential_info}")
            self.logger.error(f"product_sub_amount: {product_sub_amount}, product_sub_target: {product_sub_target}, product_sub_term:{product_sub_term}")
            self.logger.error(f"product_sub_way: {product_sub_way}, product_tax_benefit: {product_tax_benefit}, product_url_links:{product_url_links}, product_type:{product_type}")
            raise e
        finally:
            cursor.close()


