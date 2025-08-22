import time
import logging
from datetime import datetime
from pydantic import ValidationError

from src.app.dto.request.request_front_dto import request_combo_dto
from src.app.service.ai_service import ai_service


class AITestRunner:
    DEFAULT_CASES = [
        ("낮은가격-Short-3000만원-1", {"amount": 30_000_000, "period": "SHORT"}),
        ("낮은가격-Short-3000만원-2", {"amount": 30_000_000, "period": "SHORT"}),
        # ("낮은가격-Mid-3000만원-1", {"amount": 30_000_000, "period": "MID"}),
        # ("낮은가격-Mid-3000만원-2", {"amount": 30_000_000, "period": "MID"}),
        # ("낮은가격-Long-3000만원-1", {"amount": 30_000_000, "period": "LONG"}),
        # ("낮은가격-Long-3000만원-2", {"amount": 30_000_000, "period": "LONG"}),
        #
        # ("적당한가격-Short-30000만원-1", {"amount": 300_000_000, "period": "SHORT"}),
        # ("적당한가격-Short-30000만원-2", {"amount": 300_000_000, "period": "SHORT"}),
        # ("적당한가격-Mid-30000만원-1", {"amount": 300_000_000, "period": "MID"}),
        # ("적당한가격-Mid-30000만원-2", {"amount": 300_000_000, "period": "MID"}),
        # ("적당한가격-Long-30000만원-1", {"amount": 300_000_000, "period": "LONG"}),
        # ("적당한가격-Long-30000만원-2", {"amount": 300_000_000, "period": "LONG"}),
        #
        # ("많은 가격-Short-1500000만원-1", {"amount": 1_500_000_000, "period": "SHORT"}),
        # ("많은 가격-Short-1500000만원-2", {"amount": 1_500_000_000, "period": "SHORT"}),
        # ("많은 가격-Mid-1500000만원-1", {"amount": 1_500_000_000, "period": "MID"}),
        # ("많은 가격-Mid-1500000만원-2", {"amount": 1_500_000_000, "period": "MID"}),
        # ("많은 가격-Long-1500000만원-1", {"amount": 1_500_000_000, "period": "LONG"}),
        # ("많은 가격-Long-1500000만원-2", {"amount": 1_500_000_000, "period": "LONG"}),
    ]
    DEFAULT_MODELS = ["gemini-2.5-flash", "gpt-5-mini"]
    # , "gpt-5"

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

            combo_total_payment = 0
            combo_total_interest = 0
            used_uuids = []

            for prod_idx, product in enumerate(combo.product, 1):
                used_uuids.append(product.uuid)
                self.logger.info(f"   📋 상품 {prod_idx}")
                self.logger.info(f"      🏦 은행: {product.bank_name}")
                self.logger.info(f"      📄 상품명: {product.product_name} | UUID: {product.uuid}")
                self.logger.info(f"      📊 유형: {product.type} | 기간: {product.start_month}월 ~ {product.end_month}월")
                self.logger.info(f"      📉 원본 금리(base~max): {product.base_rate}% ~ {product.max_rate}%")
                self.logger.info(f"      ✅ 적용 금리(product_max_rate): {product.product_max_rate}%")
                self.logger.info(f"      💼 할당 금액: {self.format_currency(product.allocated_amount)}")

                if product.end_month < product.start_month:
                    self.logger.warning(
                        f"      ⚠️ 기간 오류: end_month({product.end_month}) < start_month({product.start_month})")

                if not (min(product.base_rate, product.max_rate) <= product.product_max_rate <= max(product.base_rate,
                                                                                                    product.max_rate)):
                    self.logger.warning(f"      ⚠️ 적용 금리가 원본 base~max 범위를 벗어납니다.")

                p_payment = sum((p.payment or 0) for p in (product.monthly_plan or []))
                p_interest = sum((p.total_interest or 0) for p in (product.monthly_plan or []))
                combo_total_payment += p_payment
                combo_total_interest += p_interest

                if product.type == "deposit" and p_payment != product.allocated_amount:
                    self.logger.warning(
                        f"      ⚠️ deposit 할당금액 불일치: allocated={self.format_currency(product.allocated_amount)}, payments={self.format_currency(p_payment)}")

                if product.type == "savings":
                    expected_allocated = p_payment  # savings는 총 납입액이 할당 금액
                    if abs(product.allocated_amount - expected_allocated) > 1:  # 1원 오차 허용
                        self.logger.warning(
                            f"      ⚠️ savings 할당금액 불일치: allocated={self.format_currency(product.allocated_amount)}, expected={self.format_currency(expected_allocated)}")

                self.logger.info(
                    f"      💰 총 납입액: {self.format_currency(p_payment)} | 💸 총 이자: {self.format_currency(p_interest)}\n")

            if hasattr(combo, 'timeline') and combo.timeline:
                self.logger.info("   📅 Timeline 분석:")
                self.logger.info("   " + "─" * 60)
                self.logger.info(f"   {'월':^5} | {'월 납입액':>12} | {'활성상품':>8} | {'누적 납입액':>12} | {'누적 이자':>12}")
                self.logger.info("   " + "─" * 60)

                prev_cumulative_payment = 0
                prev_cumulative_interest = 0
                timeline_errors = []

                for t in combo.timeline:
                    self.logger.info(f"   {t.month:^5} | {self.format_currency(t.total_monthly_payment):>12} | "
                                     f"{t.active_product_count:>8} | {self.format_currency(t.cumulative_payment):>12} | "
                                     f"{self.format_currency(t.cumulative_interest):>12}")

                    # Timeline 검증
                    # 1. 누적 납입액은 감소할 수 없음
                    if t.cumulative_payment < prev_cumulative_payment:
                        timeline_errors.append(f"월 {t.month}: 누적 납입액 감소")

                    # 2. 누적 이자는 감소할 수 없음 (일반적으로)
                    if t.cumulative_interest < prev_cumulative_interest:
                        timeline_errors.append(f"월 {t.month}: 누적 이자 감소")

                    # 3. 활성 상품 수 검증
                    active_count = sum(1 for p in combo.product
                                       if p.start_month <= t.month + 1 <= p.end_month)
                    if active_count != t.active_product_count:
                        timeline_errors.append(
                            f"월 {t.month}: 활성 상품 수 불일치 (계산={active_count}, 응답={t.active_product_count})")

                    prev_cumulative_payment = t.cumulative_payment
                    prev_cumulative_interest = t.cumulative_interest

                self.logger.info("   " + "─" * 60)

                # Timeline 최종값 검증
                if combo.timeline:
                    last_timeline = combo.timeline[-1]

                    # 최종 누적 납입액 == 총 납입액
                    if last_timeline.cumulative_payment != combo_total_payment:
                        timeline_errors.append(
                            f"최종 누적납입액({self.format_currency(last_timeline.cumulative_payment)}) ≠ 총납입액({self.format_currency(combo_total_payment)})")

                    # 최종 누적 이자 == 예상 세후 이자
                    if last_timeline.cumulative_interest != combo.expected_interest_after_tax:
                        timeline_errors.append(
                            f"최종 누적이자({self.format_currency(last_timeline.cumulative_interest)}) ≠ 예상이자({self.format_currency(combo.expected_interest_after_tax)})")

                if timeline_errors:
                    self.logger.warning("   ⚠️ Timeline 검증 오류:")
                    for error in timeline_errors:
                        self.logger.warning(f"      - {error}")
                else:
                    self.logger.info("   ✅ Timeline 검증 통과")

                self.logger.info("")

            self.logger.info(f"   📊 조합 총계:")
            self.logger.info(f"      총 납입액: {self.format_currency(combo_total_payment)}")
            self.logger.info(f"      총 이자: {self.format_currency(combo_total_interest)}")

            if abs(combo_total_interest - combo.expected_interest_after_tax) > 1:  # 1원 오차 허용
                self.logger.warning(
                    f"      ⚠️ 이자 불일치: 계산({self.format_currency(combo_total_interest)}) ≠ 응답({self.format_currency(combo.expected_interest_after_tax)})")
            else:
                self.logger.info(f"      ✅ 이자 계산 일치")

            if combo_total_payment > 0:
                calculated_rate = (combo_total_interest / combo_total_payment) * (12 / data.period_months) * 100
                if abs(calculated_rate - combo.expected_rate) > 0.01:  # 0.01% 오차 허용
                    self.logger.warning(f"      ⚠️ 수익률 불일치: 계산({calculated_rate:.2f}%) ≠ 응답({combo.expected_rate}%)")
                else:
                    self.logger.info(f"      ✅ 수익률 계산 일치")

            if len(used_uuids) != len(set(used_uuids)):
                duplicate_uuids = [uuid for uuid in used_uuids if used_uuids.count(uuid) > 1]
                self.logger.error(f"      ❌ UUID 중복 발견: {set(duplicate_uuids)}")
            else:
                self.logger.info(f"      ✅ UUID 중복 없음")

            self.logger.info("─" * 80 + "\n")

            self.logger.info("🔍 전체 검증 요약")
            self.logger.info("=" * 80)

            all_uuids = []
            for combo in data.combination:
                for product in combo.product:
                    all_uuids.append(product.uuid)

            if len(all_uuids) != len(set(all_uuids)):
                duplicate_global = [uuid for uuid in set(all_uuids) if all_uuids.count(uuid) > 1]
                self.logger.error(f"❌ 전체 조합에서 UUID 중복: {duplicate_global}")
            else:
                self.logger.info(f"✅ 모든 조합에서 UUID 중복 없음 (총 {len(all_uuids)}개 상품)")

            max_combo_payment = max((sum(sum(p.payment or 0 for p in prod.monthly_plan or [])
                                         for prod in combo.product) for combo in data.combination), default=0)
            if max_combo_payment > data.total_payment:
                self.logger.warning(
                    f"⚠️ 조합 납입액({self.format_currency(max_combo_payment)}) > 총 투자금액({self.format_currency(data.total_payment)})")

            self.logger.info("=" * 80)

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