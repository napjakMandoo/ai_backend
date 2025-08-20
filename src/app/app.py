import logging
import json
from logging.handlers import RotatingFileHandler
import sys

from flask import Flask, jsonify, request
from pydantic import ValidationError

from src.app.dto.request.request_front_dto import request_combo_dto
from src.app.service.ai_service import ai_service

app = Flask(__name__)

def setup_logging():
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s:%(lineno)d - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)

    return root_logger


@app.route("/recommendations", methods=["GET"])
def ai_recommend():
    logger = logging.getLogger(__name__)
    logger.info("AI recommendation request received")
    
    try:
        # GET 요청에서 쿼리 파라미터 읽기
        amount = request.args.get('amount', type=int)
        period = request.args.get('period')
        
        request_data = {
            'amount': amount,
            'period': period
        }
        logger.info(f"Request data parsed successfully: {request_data}")
        # 수정 GET 메소드 맞게
        
        request_dto = request_combo_dto(**request_data)
        logger.info(f"Request DTO created: amount={request_dto.amount}, period={request_dto.period}")

        logger.info("Initializing AI service")
        ai_service_instance = ai_service()

        logger.info("Calling AI service to get recommendations")
        result = ai_service_instance.get_data(request_dto)
        logger.info("AI service returned result successfully")

        try:
            result_dict = result.model_dump()
            logger.debug("Result converted using model_dump()")
        except AttributeError:
            try:
                result_dict = result.dict()
                logger.debug("Result converted using dict()")
            except AttributeError:
                result_dict = result
                logger.debug("Result used as-is (already dict)")

        #logger.info(f"Returning successful response with {len(result_dict.get('combination', []))} combinations")
        combination_count = len(result_dict.get('combination', [])) if result_dict else 0
        
        
        logger.info(f"Returning successful response with {combination_count} combinations")
        return jsonify({
            "status": "success",
            "data": result_dict
        }), 200

    except ValidationError as e:
        logger.error(f"Validation error: {e.errors()}")
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        logger.exception("Unexpected error in ai_recommend")
        if app.debug:
            return jsonify({"error": "internal_error", "detail": str(e)}), 500
        return jsonify({"error": "internal_error"}), 500


if __name__ == "__main__":
    logger = setup_logging()
    logger.info("========== Application Starting ===========")

    app.run(host='0.0.0.0', port=5000, debug=True)