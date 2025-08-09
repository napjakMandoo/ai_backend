'''
    1. input 데이터 정리
	2. output 데이터 정리
	3. AI한테 넘겨야할 정보
	4. AI한테 받아야할 정보
	5. 뽑아야할 후보군 결정
	6. 넘기기
	7. 받기
	8. 전달하기
	9. 테스트
'''
import logging

from src.app.dto.ai.ai_for_recommend import ai_for_recommend
from src.app.dto.request.request_front_dto import request_combo_dto
from src.shared.db.product.productRepository import ProductRepository
from src.shared.db.util.MysqlUtil import MysqlUtil

class ai_service:
    def __init__(self):
        self.mysqlUtil = MysqlUtil()
        self.logger = logging.getLogger(__name__)
        self.ai = ai_for_recommend()

    def get_data(self, request: request_combo_dto):
        connection = self.mysqlUtil.get_connection()

        try:
            period_str = (
                request.period.value if hasattr(request.period, "value")
                else str(request.period)
            )

            if period_str == "SHORT":
                top_n = 20
            elif period_str == "MID":
                top_n = 40
            elif period_str == "LONG":
                top_n = 60
            else:
                raise ValueError(f"Invalid period: {period_str}")

            product_repository = ProductRepository()
            payload = product_repository.build_ai_payload(
                connection=connection,
                top_n=top_n
            )

            merged_data = {
                "request_info": request.model_dump(mode="json"),
                "db_payload": payload.model_dump(mode="json")
            }

            result = self.ai.create_preferential_json(content=merged_data)
            return result

        finally:
            try:
                connection.close()
            except Exception:
                pass