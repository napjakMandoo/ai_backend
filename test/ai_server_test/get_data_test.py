import time
import logging
import sys
import os
from datetime import datetime
from pydantic import ValidationError

from src.app.dto.request.request_front_dto import request_combo_dto
from src.app.service.ai_service import ai_service


class AITestRunner:
    DEFAULT_CASES = [
        # ("낮은가격-Short-3000만원-1", {"amount": 30_000_000, "period": "SHORT"}),
        # ("낮은가격-Short-3000만원-2", {"amount": 30_000_000, "period": "SHORT"}),
        # ("낮은가격-Mid-3000만원-1", {"amount": 30_000_000, "period": "MID"}),
        # ("낮은가격-Mid-3000만원-2", {"amount": 30_000_000, "period": "MID"}),
        ("낮은가격-Long-3000만원-1", {"amount": 30_000_000, "period": "LONG"}),
        ("낮은가격-Long-3000만원-2", {"amount": 30_000_000, "period": "LONG"}),

        # ("적당한가격-Short-30000만원-1", {"amount": 300_000_000, "period": "SHORT"}),
        # ("적당한가격-Short-30000만원-2", {"amount": 300_000_000, "period": "SHORT"}),
        ("적당한가격-Mid-30000만원-1", {"amount": 300_000_000, "period": "MID"}),
        ("적당한가격-Mid-30000만원-2", {"amount": 300_000_000, "period": "MID"}),
        # ("적당한가격-Long-30000만원-1", {"amount": 300_000_000, "period": "LONG"}),
        # ("적당한가격-Long-30000만원-2", {"amount": 300_000_000, "period": "LONG"}),

        # ("많은 가격-Short-1500000만원-1", {"amount": 1_500_000_000, "period": "SHORT"}),
        # ("많은 가격-Short-1500000만원-2", {"amount": 1_500_000_000, "period": "SHORT"}),
        # ("많은 가격-Mid-1500000만원-1", {"amount": 1_500_000_000, "period": "MID"}),
        # ("많은 가격-Mid-1500000만원-2", {"amount": 1_500_000_000, "period": "MID"}),
        # ("많은 가격-Long-1500000만원-1", {"amount": 1_500_000_000, "period": "LONG"}),
        # ("많은 가격-Long-1500000만원-2", {"amount": 1_500_000_000, "period": "LONG"}),
    ]
    # DEFAULT_MODELS = ["gemini-2.5-flash", "gpt-5-mini"]
    DEFAULT_MODELS = ["gpt-5-mini", "gpt-5-nano"]

    # , "gpt-5"

    def __init__(self, cases: list[tuple[str, dict]] = None, models: list[str] = None, log_level: str = "INFO",
                 log_to_file: bool = True, log_dir: str = "logs"):
        self.test_cases = cases if cases is not None else self.DEFAULT_CASES
        self.ai_models = models if models is not None else self.DEFAULT_MODELS
        self.log_level = getattr(logging, log_level.upper())
        self.log_to_file = log_to_file
        self.log_dir = log_dir

        # 로그 파일 경로 설정 (실행 시작 시간 기준)
        self.start_datetime = datetime.now()
        if self.log_to_file:
            self.log_file_path = self._setup_log_file()

        # 전역 로깅 설정
        self._setup_global_logging()

        self.logger = self._setup_runner_logger()
        self.service = self._initialize_service()

    def _setup_log_file(self) -> str:
        """로그 파일 경로를 설정하고 디렉토리를 생성합니다."""
        # 로그 디렉토리 생성
        os.makedirs(self.log_dir, exist_ok=True)

        # 로그 파일명: ai_test_YYYYMMDD_HHMMSS.log
        timestamp = self.start_datetime.strftime('%Y%m%d_%H%M%S')
        log_filename = f"ai_test_{timestamp}.log"
        log_file_path = os.path.join(self.log_dir, log_filename)

        return log_file_path

    def _setup_global_logging(self):
        """AITestRunner의 로그만 출력되도록 설정합니다."""
        # 루트 로거 설정 - 높은 레벨로 설정하여 다른 모듈 로그 차단
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.CRITICAL)  # 다른 모듈들은 CRITICAL만 출력

        # 기존 핸들러 제거 (중복 방지)
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # 포맷터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

        # 콘솔 핸들러 설정
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)  # 핸들러는 모든 레벨 허용
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # 파일 핸들러 설정 (옵션)
        if self.log_to_file:
            file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)  # 핸들러는 모든 레벨 허용
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            # 파일 로깅 시작 메시지
            print(f"📄 로그 파일: {self.log_file_path}")

        # 다른 모듈들의 로그를 억제 - CRITICAL 레벨로 설정
        modules_to_suppress = [
            'src.app.service.ai_service',
            'src.app.dto.request.request_front_dto',
            'src.app',  # src.app 하위 모든 모듈
            'httpx',  # HTTP 클라이언트 로그
            'openai',  # OpenAI 클라이언트 로그
            'google',  # Google AI 클라이언트 로그
            'httpcore',
            'urllib3.connectionpool',
            'requests.packages.urllib3.connectionpool',
            'pydantic',  # Pydantic 검증 로그
            'asyncio',  # 비동기 관련 로그
        ]

        for module_name in modules_to_suppress:
            logger = logging.getLogger(module_name)
            logger.setLevel(logging.CRITICAL)  # CRITICAL만 출력
            logger.propagate = True

        # 완전히 비활성화하고 싶은 모듈들 (로그 출력 안함)
        modules_to_disable = [
            'httpcore.http11',
            'httpcore.connection',
            'urllib3.util.retry',
            'charset_normalizer',
        ]

        for module_name in modules_to_disable:
            logger = logging.getLogger(module_name)
            logger.disabled = True

    def _setup_runner_logger(self) -> logging.Logger:
        """테스트 러너용 로거를 설정합니다."""
        logger_name = f"AITestRunner_{id(self)}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(self.log_level)  # 사용자가 설정한 레벨 사용
        # 전역 설정의 핸들러를 사용하므로 별도 핸들러는 추가하지 않음
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

    def calculate_correct_active_count(self, month: int, products) -> int:
        """
        CORRECTED: active_product_count 계산 로직
        현금흐름 기준으로 실제 납입이 발생하는 상품 수를 계산
        """
        count = 0
        for product in products:
            if product.type == "deposit":
                # 예금: 시작 월(0-based)에만 카운트
                if month == (product.start_month - 1):
                    count += 1
            elif product.type == "savings":
                # 적금: 전체 납입 기간 동안 카운트
                if (product.start_month - 1) <= month <= (product.end_month - 1):
                    count += 1
        return count

    def validate_timeline_active_count(self, combo, timeline_errors: list):
        """Timeline의 active_product_count 검증"""
        if not hasattr(combo, 'timeline') or not combo.timeline:
            return

        for t in combo.timeline:
            # 수정된 로직으로 계산
            correct_active_count = self.calculate_correct_active_count(t.month, combo.product)

            if correct_active_count != t.active_product_count:
                # 상세한 오류 메시지 생성
                error_detail = f"월 {t.month}: active_product_count 오류"
                error_detail += f"\n      예상: {correct_active_count}개 (현금흐름 기준)"
                error_detail += f"\n      실제: {t.active_product_count}개"
                error_detail += f"\n      상세 분석:"

                for prod_idx, product in enumerate(combo.product, 1):
                    should_be_active = False
                    reason = ""

                    if product.type == "deposit":
                        if t.month == (product.start_month - 1):
                            should_be_active = True
                            reason = "예금 시작월(납입)"
                        else:
                            reason = "예금 비납입월"
                    elif product.type == "savings":
                        if (product.start_month - 1) <= t.month <= (product.end_month - 1):
                            should_be_active = True
                            reason = "적금 납입기간"
                        else:
                            reason = "적금 비납입기간"

                    status = "활성" if should_be_active else "비활성"
                    error_detail += f"\n        상품{prod_idx}({product.type}): {status} - {reason}"

                timeline_errors.append(error_detail)

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

                    prev_cumulative_payment = t.cumulative_payment
                    prev_cumulative_interest = t.cumulative_interest

                # 수정된 active_product_count 검증
                self.validate_timeline_active_count(combo, timeline_errors)

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
                        # 멀티라인 에러 메시지 처리
                        for line in error.split('\n'):
                            self.logger.warning(f"      {line}" if line.strip() else "")
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
            self.logger.info("📝 DTO 생성 시작...")
            dto_start = time.time()
            request_dto = request_combo_dto(**payload)
            dto_end = time.time()
            self.logger.info(f"✅ DTO 생성 완료. 소요 시간: {dto_end - dto_start:.3f}초")

            self.logger.info(f"🤖 AI 서비스 호출 시작... (모델: {model})")
            ai_start = time.time()
            data = self.service.get_data(request=request_dto, model=model)
            ai_end = time.time()
            self.logger.info(f"✅ AI 처리 완료. 소요 시간: {ai_end - ai_start:.3f}초")

            self.logger.info(f"📋 응답 검증 요약:")
            self.logger.info(f"   - 조합 개수: {len(data.combination)}")
            self.logger.info(f"   - 총 투자금액: {self.format_currency(data.total_payment)}")
            try:
                ratio = data.total_payment / int(payload["amount"]) * 100
                self.logger.info(f"   - 요청 금액 대비: {ratio:.1f}%")
            except (KeyError, ZeroDivisionError):
                pass

            self.print_formatted_result(data)

        except ValidationError as ve:
            self.logger.error(f"❌ ValidationError 발생 (입력 자체 불량)")
            self.logger.error(f"상세 오류: {ve}")
        except Exception as e:
            self.logger.error(f"❌ 실행 중 예외 발생: {type(e).__name__}: {str(e)}")
            self.logger.exception("상세 스택 트레이스:")

    def run(self):
        total_start_time = time.time()
        self.logger.info(f"🚀 전체 테스트 시작: {self.start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.log_to_file:
            self.logger.info(f"📄 로그 파일: {self.log_file_path}")
        self.logger.info(f"📊 테스트 설정:")
        self.logger.info(f"   - 테스트 케이스: {len(self.test_cases)}개")
        self.logger.info(f"   - AI 모델: {self.ai_models}")
        self.logger.info(f"   - 로그 레벨: {logging.getLevelName(self.log_level)}")
        self.logger.info(f"   - 파일 저장: {'예' if self.log_to_file else '아니오'}")
        self.logger.info("=" * 80)

        for model in self.ai_models:
            self.logger.info(f"\n{'=' * 20} 모델: {model} 테스트 시작 {'=' * 20}")
            for name, payload in self.test_cases:
                self._run_single_case(name, payload, model)

        total_end_time = time.time()
        self.logger.info("\n" + "=" * 80)
        self.logger.info("🎉 모든 테스트 완료.")
        self.logger.info(f"⏱️ 총 실행 시간: {total_end_time - total_start_time:.3f}초")
        if self.log_to_file:
            self.logger.info(f"📄 로그 저장 위치: {os.path.abspath(self.log_file_path)}")
        self.logger.info("=" * 80)


if __name__ == "__main__":
    # 사용법 예시들:

    # 1) 기본 설정 - 로그 파일에 저장 + INFO 레벨
    # runner = AITestRunner()

    # 2) DEBUG 레벨로 상세 로그 + 파일 저장
    # runner = AITestRunner(log_level="DEBUG")

    # 3) 콘솔 출력만 하고 파일 저장 안함
    # runner = AITestRunner(log_to_file=False)

    # 4) 커스텀 로그 디렉토리 지정
    # runner = AITestRunner(log_dir="test_results")

    # 5) WARNING 레벨로 중요한 것만 + 특정 디렉토리
    # runner = AITestRunner(log_level="WARNING", log_dir="logs/warnings")

    runner = AITestRunner(log_level="DEBUG", log_dir="test_logs")
    runner.run()