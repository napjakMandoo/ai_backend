import uuid

from src.ai.preprocessing.db.bank.BankRepository import BankRepository
import logging

from src.ai.preprocessing.db.bank.MysqlUtil import MysqlUtil

class BankRepositoryTest:
    
    delete_bank_query = "delete from bank"

    def __init__(self):
        self.mysqlUtil = MysqlUtil()

    def get_uuid_by_bank_name_test(self, bank_name):

        repository = BankRepository()
        uuid = repository.get_uuid_by_bank_name(bank_name)
        return uuid

    def save_bank_test(self):
        connection = self.mysqlUtil.get_connection()
        cursor = connection.cursor()
        cursor.execute(self.delete_bank_query)
        connection.commit()
        cursor.close()
        connection.close()

        repository = BankRepository()
        repository.save_bank()

        connection = self.mysqlUtil.get_connection()
        cursor = connection.cursor()
        select_bank_all_query = "select * from bank"
        cursor.execute(select_bank_all_query)

        cursor.close()
        connection.close()

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )

    test = BankRepositoryTest()
    test.save_bank_test()

    name_test = test.get_uuid_by_bank_name_test("KDB")
    print(name_test)