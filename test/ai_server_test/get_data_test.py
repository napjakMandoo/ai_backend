import time
import logging
from datetime import datetime
from pydantic import ValidationError

from src.app.dto.request.request_front_dto import request_combo_dto
from src.app.service.ai_service import ai_service


class AITestRunner:
    DEFAULT_CASES = [
        ("Basic-Short-1000만원-1", {"amount": 10_000_000, "period": "SHORT"}),
        ("Basic-Short-1000만원-2", {"amount": 10_000_000, "period": "SHORT"}),
        ("Basic-Short-1000만원-3", {"amount": 10_000_000, "period": "SHORT"}),
        ("Basic-Short-1000만원-4", {"amount": 10_000_000, "period": "SHORT"}),
        ("Basic-Short-1000만원-5", {"amount": 10_000_000, "period": "SHORT"}),
    ]
    DEFAULT_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro", "gpt-5", "gpt-5-mini"]

    def __init__(self, cases: list[tuple[str, dict]] = None, models: list[str] = None):
        self.test_cases = cases if cases is not None else self.DEFAULT_CASES
        self.ai_models = models if models is not None else self.DEFAULT_MODELS

        self.logger = self._setup_logger()

        self.service = self._initialize_service()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"AITestRunner_{id(self)}")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _initialize_service(self) -> 'ai_service':
        self.logger.info("서비스 초기화 중...")
        init_start = time.time()
        service = ai_service()
        init_end = time.time()
        self.logger.info(f"서비스 초기화 완료. 소요 시간: {init_end - init_start:.3f}초")
        return service

    @staticmethod
    def format_currency(amount: int) -> str:
        return f"{amount:,}원"

    def print_formatted_result(self, data):
        """AI 추천 결과를 형식에 맞게 상세히 출력하고 검증합니다."""
        self.logger.info("=" * 80)
        self.logger.info("📊 AI 추천 결과")
        self.logger.info("=" * 80)
        self.logger.info(f"💰 총 투자금액: {self.format_currency(data.total_payment)}")
        self.logger.info(f"📅 투자 기간: {data.period_months}개월")
        self.logger.info(f"🎯 추천 조합 수: {len(data.combination)}개\n")

        for idx, combo in enumerate(data.combination, 1):
            self.logger.info(f"💡 추천 조합 #{idx}")
            self.logger.info(f"   ID: {combo.combination_id}")
            self.logger.info(f"   📈 예상 수익률: {combo.expected_rate}% (연환산 세후)")
            self.logger.info(f"   💵 예상 세후 이자: {self.format_currency(combo.expected_interest_after_tax)}")
            self.logger.info(f"   📦 포함 상품 수: {len(combo.product)}개\n")

            combo_total_payment, combo_total_interest, used_uuids = 0, 0, []

            for prod_idx, product in enumerate(combo.product, 1):
                used_uuids.append(product.uuid)
                self.logger.info(f"   📋 상품 {prod_idx}")
                self.logger.info(f"      🏦 은행: {product.bank_name}")
                self.logger.info(f"      📄 상품명: {product.product_name} | UUID: {product.uuid}")
                self.logger.info(f"      📊 유형: {product.type} | 기간: {product.start_month}월 ~ {product.end_month}월")
                self.logger.info(f"      📉 원본 금리(base~max): {product.base_rate}% ~ {product.max_rate}%")
                self.logger.info(f"      ✅ 적용 금리(product_max_rate): {product.product_max_rate}%")

                if product.end_month < product.start_month:
                    self.logger.warning("      기간 오류: end_month가 start_month보다 작습니다.")
                if not (min(product.base_rate, product.max_rate) <= product.product_max_rate <= max(product.base_rate,
                                                                                                    product.max_rate)):
                    self.logger.warning("      적용 금리가 원본 base~max 범위를 벗어납니다.")

                p_payment = sum((p.payment or 0) for p in (product.monthly_plan or []))
                p_interest = sum((p.total_interest or 0) for p in (product.monthly_plan or []))
                combo_total_payment += p_payment
                combo_total_interest += p_interest

                self.logger.info(
                    f"      💰 총 납입액: {self.format_currency(p_payment)} | 💸 총 이자: {self.format_currency(p_interest)}\n")

            self.logger.info(f"   📊 조합 총계:")
            self.logger.info(f"      총 납입액: {self.format_currency(combo_total_payment)}")
            self.logger.info(f"      총 이자: {self.format_currency(combo_total_interest)}")
            if combo_total_interest != combo.expected_interest_after_tax:
                self.logger.warning(
                    f"      계산 총이자({self.format_currency(combo_total_interest)}) ≠ 응답 예상이자({self.format_currency(combo.expected_interest_after_tax)})")

            if len(used_uuids) != len(set(used_uuids)):
                self.logger.error(f"      UUID 중복 발견: {used_uuids}")
            else:
                self.logger.info(f"      ✅ UUID 중복 없음")

            self.logger.info("─" * 80 + "\n")

    def _run_single_case(self, case_name: str, payload: dict, model: str):
        """단일 테스트 케이스를 실행하고 결과를 로깅합니다."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info(f"🧪 테스트 케이스: {case_name} (모델: {model})")
        self.logger.info("=" * 80)
        self.logger.info(f"입력: {payload}")

        try:
            dto_start = time.time()
            request_dto = request_combo_dto(**payload)
            self.logger.info(f"DTO 생성 시간: {time.time() - dto_start:.3f}초")

            ai_start = time.time()
            data = self.service.get_data(request=request_dto, model=model)
            self.logger.info(f"AI 처리 시간: {time.time() - ai_start:.3f}초")

            self.logger.info(f"✅ 응답 검증 요약:")
            self.logger.info(f"   - 조합 개수: {len(data.combination)}")
            self.logger.info(f"   - 총 투자금액: {self.format_currency(data.total_payment)}")
            try:
                ratio = data.total_payment / int(payload["amount"]) * 100
                self.logger.info(f"   - 요청 금액 대비: {ratio:.1f}%")
            except (KeyError, ZeroDivisionError):
                pass

            self.print_formatted_result(data)

        except ValidationError as ve:
            self.logger.error(f"❌ ValidationError 발생 (입력 자체 불량)\n{ve}")
        except Exception:
            self.logger.exception("❌ 실행 중 예외 발생")

    def run(self):
        total_start_time = time.time()
        start_datetime = datetime.now()
        self.logger.info(f"전체 테스트 시작: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 50)

        for model in self.ai_models:
            self.logger.info(f"\n{'=' * 20} 모델: {model} 테스트 시작 {'=' * 20}")
            for name, payload in self.test_cases:
                self._run_single_case(name, payload, model)

        total_end_time = time.time()
        self.logger.info("\n" + "=" * 50)
        self.logger.info("모든 테스트 완료.")
        self.logger.info(f"총 실행 시간: {total_end_time - total_start_time:.3f}초")
        self.logger.info("=" * 50)


if __name__ == "__main__":
    runner = AITestRunner()
    runner.run()