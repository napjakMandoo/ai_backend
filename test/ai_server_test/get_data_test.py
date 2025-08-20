import time
from datetime import datetime
from pydantic import ValidationError
from src.app.dto.request.request_front_dto import request_combo_dto
from src.app.service.ai_service import ai_service


def format_currency(amount: int) -> str:
    return f"{amount:,}원"


def print_formatted_result(data):
    print("📊 AI 추천 결과")
    print("=" * 80)
    print(f"💰 총 투자금액: {format_currency(data.total_payment)}")
    print(f"📅 투자 기간: {data.period_months}개월")
    print(f"🎯 추천 조합 수: {len(data.combination)}개\n")

    for idx, combo in enumerate(data.combination, 1):
        print(f"💡 추천 조합 #{idx}")
        print(f"   ID: {combo.combination_id}")
        print(f"   📈 예상 수익률: {combo.expected_rate}% (연환산 세후)")
        print(f"   💵 예상 세후 이자: {format_currency(combo.expected_interest_after_tax)}")
        print(f"   📦 포함 상품 수: {len(combo.product)}개\n")

        combo_total_payment = 0
        combo_total_interest = 0

        # UUID 중복 및 기본 검증을 위한 수집
        used_uuids = []

        for prod_idx, product in enumerate(combo.product, 1):
            used_uuids.append(product.uuid)
            print(f"   📋 상품 {prod_idx}")
            print(f"      🏦 은행: {product.bank_name}")
            print(f"      📄 상품명: {product.product_name}")
            print(f"      🔖 UUID: {product.uuid}")
            print(f"      📊 유형: {product.type}")
            print(f"      📉 원본 기본금리(base_rate): {product.base_rate}%")
            print(f"      💹 원본 최대금리(max_rate): {product.max_rate}%")
            print(f"      ✅ 적용 금리(product_max_rate): {product.product_max_rate}%")
            print(f"      ℹ️  참고 기본(product_base_rate): {product.product_base_rate}%")
            print(f"      📅 기간: {product.start_month}월 ~ {product.end_month}월")

            # 기본 일관성 검증
            if product.end_month < product.start_month:
                print("      ⚠️ 기간 오류: end_month가 start_month보다 작습니다.")

            # 적용 금리가 원본 범위 밖이면 경고
            if not (min(product.base_rate, product.max_rate)
                    <= product.product_max_rate
                    <= max(product.base_rate, product.max_rate)):
                print("      ⚠️ 적용 금리가 원본 base~max 범위를 벗어납니다.")

            # 총 납입/이자 합산
            product_total_payment = sum((plan.payment or 0) for plan in (product.monthly_plan or []))
            product_total_interest = sum((plan.total_interest or 0) for plan in (product.monthly_plan or []))

            combo_total_payment += product_total_payment
            combo_total_interest += product_total_interest

            print(f"      💰 총 납입액: {format_currency(product_total_payment)}")
            print(f"      💸 총 이자: {format_currency(product_total_interest)}\n")

            # 월별 상세
            if product.monthly_plan:
                print(f"      📅 월별 상세:")
                for plan in product.monthly_plan:
                    print(f"         {plan.month}월: 납입 {format_currency(plan.payment)}, "
                          f"이자 {format_currency(plan.total_interest)}")
                print()
            else:
                print(f"      📅 월별 상세: (없음)\n")

        # 조합 단위 합계 및 기본 검증
        print(f"   📊 조합 총계:")
        print(f"      총 납입액: {format_currency(combo_total_payment)}")
        print(f"      총 이자: {format_currency(combo_total_interest)}")
        if combo_total_interest != combo.expected_interest_after_tax:
            print(f"      ⚠️ 경고: 계산 총이자({format_currency(combo_total_interest)}) "
                  f"≠ 응답 예상이자({format_currency(combo.expected_interest_after_tax)})")

        # UUID 중복 체크
        if len(used_uuids) != len(set(used_uuids)):
            print(f"      ❌ UUID 중복 발견: {used_uuids}")
        else:
            print(f"      ✅ UUID 중복 없음")

        print("─" * 80)
        print()


def run_case(service: ai_service, case_name: str, payload: dict):
    """단일 케이스 실행 + 시간 측정 + 결과 출력/에러 출력"""
    print("\n" + "=" * 80)
    print(f"🧪 테스트 케이스: {case_name}")
    print("=" * 80)
    print(f"입력: {payload}")

    try:
        dto_start = time.time()
        dto = request_combo_dto(**payload)  # Pydantic 검증
        dto_end = time.time()
        print(f"DTO 생성 시간: {dto_end - dto_start:.3f}초")

        ai_start = time.time()
        data = service.get_data(dto)
        ai_end = time.time()
        print(f"AI 처리 시간: {ai_end - ai_start:.3f}초")

        # 응답 요약 검증
        print(f"✅ 응답 검증 요약:")
        print(f"   - 조합 개수: {len(data.combination)}")
        print(f"   - 총 투자금액: {format_currency(data.total_payment)}")
        try:
            ratio = data.total_payment / int(payload["amount"]) * 100
            print(f"   - 요청 금액 대비: {ratio:.1f}%")
        except Exception:
            pass
        print()

        print_formatted_result(data)

    except ValidationError as ve:
        print("❌ ValidationError 발생 (입력 자체 불량)")
        print(ve)
    except Exception as e:
        print("❌ 실행 중 예외 발생")
        print(repr(e))


if __name__ == "__main__":
    total_start_time = time.time()
    start_datetime = datetime.now()
    print(f"테스트 시작 시간: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    init_start = time.time()
    service = ai_service()
    init_end = time.time()
    print(f"서비스 초기화 시간: {init_end - init_start:.3f}초")

    # ✅ 테스트 케이스 모음 (Enum 대문자 사용)
    cases = [
        ("Basic-Short-1000만원", {"amount": 10_000_000, "period": "SHORT"}),
        ("Basic-Short-1000만원", {"amount": 10_000_000, "period": "SHORT"}),
        ("Basic-Short-1000만원", {"amount": 10_000_000, "period": "SHORT"}),
        ("Basic-Short-1000만원", {"amount": 10_000_000, "period": "SHORT"}),
        ("Basic-Short-1000만원", {"amount": 10_000_000, "period": "SHORT"}),
    ]

    for name, payload in cases:
        run_case(service, name, payload)

    total_end_time = time.time()
    print("\n" + "=" * 50)
    print(f"전체 실행 시간: {total_end_time - total_start_time:.3f}초")
    print("=" * 50)
