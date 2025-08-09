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
        self.logger.info("AI service initialized")

    def get_data(self, request: request_combo_dto):
        self.logger.info(f"Starting AI recommendation process for amount: {request.amount}, period: {request.period}")
        
        connection = self.mysqlUtil.get_connection()
        self.logger.debug("Database connection established")

        try:
            period_str = (
                request.period.value if hasattr(request.period, "value")
                else str(request.period)
            )
            self.logger.info(f"Period extracted: {period_str}")

            if period_str == "SHORT":
                top_n = 20
            elif period_str == "MID":
                top_n = 40
            elif period_str == "LONG":
                top_n = 60
            else:
                self.logger.error(f"Invalid period value: {period_str}")
                raise ValueError(f"Invalid period: {period_str}")

            self.logger.info(f"Selected top_n products: {top_n} for period {period_str}")

            self.logger.info("Building AI payload from database")
            product_repository = ProductRepository()
            payload = product_repository.build_ai_payload(
                connection=connection,
                top_n=top_n
            )
            self.logger.info(f"AI payload built successfully with {len(payload.products)} products")

            merged_data = {
                "request_info": request.model_dump(mode="json"),
                "db_payload": payload.model_dump(mode="json")
            }
            self.logger.debug(f"Data merged for AI processing: request_amount={request.amount}")

            self.logger.info("Sending data to AI for recommendation generation")
            result = self.ai.create_preferential_json(content=merged_data)
            self.logger.info("AI recommendation generation completed successfully")
            
            return result

        except Exception as e:
            self.logger.error(f"Error in AI service processing: {str(e)}")
            raise
        finally:
            try:
                connection.close()
                self.logger.debug("Database connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing database connection: {str(e)}")
