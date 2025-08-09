from src.shared.db.product.productRepository import ProductRepository
from src.shared.db.util.MysqlUtil import MysqlUtil

if __name__ == "__main__":
    util = MysqlUtil()
    connection = util.get_connection()
    repository = ProductRepository()
    repository.build_ai_payload(connection=connection)