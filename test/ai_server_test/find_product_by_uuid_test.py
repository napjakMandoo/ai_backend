from src.shared.db.bank.BankRepository import BankRepository
from src.shared.db.product.productRepository import ProductRepository
from src.shared.db.util.MysqlUtil import MysqlUtil

if __name__ == "__main__":
    bankRepository = BankRepository()
    data = bankRepository.get_bank_data()
    for d in data:
        print(d)

    # MySQLUtil = MysqlUtil()
    # connection = MySQLUtil.get_connection()
    # repository = ProductRepository()
    # uuid = repository.print_product_by_uuid(connection=connection,product_uuid="68842d6b-9496-4cb3-9f78-e56d1c20ae3d")
    #
    #
    # print(uuid)