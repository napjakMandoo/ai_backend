import logging
import json

from flask import Flask, jsonify, request
from pydantic import ValidationError

from src.app.dto.request.request_front_dto import request_combo_dto
from src.app.service.ai_service import ai_service

app = Flask(__name__)


@app.route("/ai/recommend", methods=["POST"])
def ai_recommend():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    try:
        request_data = request.get_json()
        request_dto = request_combo_dto(**request_data)

        ai_service_instance = ai_service()

        result = ai_service_instance.get_data(request_dto)

        try:
            result_dict = result.model_dump()
        except AttributeError:
            try:
                result_dict = result.dict()
            except AttributeError:
                result_dict = result

        return jsonify({
            "status": "success",
            "data": result_dict
        }), 200

    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        app.logger.exception("ai_recommend failed")
        if app.debug:
            return jsonify({"error": "internal_error", "detail": str(e)}), 500
        return jsonify({"error": "internal_error"}), 500

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.info("==========앱 시작 ===========")
    app.run(host='0.0.0.0', port=5000, debug=True)
