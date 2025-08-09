import logging

from flask import Flask, jsonify, request
from pydantic import ValidationError

from src.app.dto.request.request_front_dto import request_combo_dto
from src.app.dto.response.response_front_dto import response_front_dto, monthly_plan_dto, product_dto, combo_dto

app = Flask(__name__)


def build_sample_response(amount: int, period_str: str) -> response_front_dto:
    monthly_plan = [
        monthly_plan_dto(month=0, payment=amount, total_interest=0),
        monthly_plan_dto(month=1, payment=0, total_interest=int(amount * 0.0006)),  # 예시 이자
        monthly_plan_dto(month=2, payment=0, total_interest=int(amount * 0.0012)),
    ]

    product1 = product_dto(
        product_uuid="uuid-001",
        bank_name="JEJU",
        product_name="청년 사랑 적금 A",
        product_max_rate=7.0,
        product_base_rate=3.0,
        start_month=0,
        end_month=6,
        monthly_plan=monthly_plan,
    )

    product2 = product_dto(
        product_uuid="uuid-002",
        bank_name="JEJU",
        product_name="청년 사랑 적금 B",
        product_max_rate=6.5,
        product_base_rate=2.8,
        start_month=0,
        end_month=7,
        monthly_plan=monthly_plan,
    )

    combo1 = combo_dto(
        combination_id="combo_001",
        expected_rate=6.00,
        expected_interest_after_tax=int(amount * 0.006 * 6 / 12),  # 매우 단순 예시
        product=[product1, product2],
    )

    combo2 = combo_dto(
        combination_id="combo_002",
        expected_rate=5.80,
        expected_interest_after_tax=int(amount * 0.0058 * 6 / 12),
        product=[product2],
    )

    return response_front_dto(
        total_payment=amount,
        period_months=6,
        combo=[combo1, combo2],
    )

@app.route("/ai/dummy", methods=['GET'])
def ai_dummy():
    if not request.is_json:
        return jsonify({'error': 'request is not json'}), 400

    try:
        dto = request_combo_dto(**request.get_json())
        period_str = dto.period.value if hasattr(dto.period, "value") else str(dto.period)

        resp_dto = build_sample_response(amount=dto.amount, period_str=period_str)

        payload = resp_dto.model_dump() if hasattr(resp_dto, "model_dump") else resp_dto.dict()
        return jsonify(payload), 200

    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

@app.route('/ai/recommend', methods=['GET'])
def ai_recommend():
    if not request.is_json:
        return jsonify({'error': 'request is not json'}), 400

    try:
        dto = request_combo_dto(**request.get_json())
        print(dto.period)
        print(dto.amount)
        return jsonify({'message': 'success'}), 200

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.info("==========앱 시작 ===========")
    app.run(host='0.0.0.0', port=5000, debug=True)
