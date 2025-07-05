from ai.LlmUtil import LlmUtil

util = LlmUtil()

test_str = "가족사랑 우대이율 (연 0.2%p)	신규(또는 재예치) 시 가입고객을 포함하여 KB국민은행에 가족고객으로 등록된 가족수가 3인 이상인 경우"
result = util.create_preferential_json(test_str)
print(result)

test_str = "자동이체 우대이율 (최대 연 0.1%p)	계약기간 중 KB국민은행 계좌간 자동이체로 이 적금에 입금된 입금건수가 8회 이상인 경우"
result = util.create_preferential_json(test_str)
print(result)

test_str = " 아동수당 우대이율 (연 0.1%p)	계약기간 중 본인명의의 KB Young Youth 통장으로 아동수당을 3회 이상 수령한 경우"
result = util.create_preferential_json(test_str)
print(result)
test_str = "주택청약종합저축 우대이율 (청년 주택드림 청약통장 포함) (최대 연 0.4%p)	계약기간 중 KB국민은행에서 주택청약종합저축을 신규 가입한 경우 (연 0.3%p) 만기일 기준으로 KB국민은행의 주택청약종합저축을 보유하고 있는 경우 (연 0.1%p)"
result = util.create_preferential_json(test_str)
print(result)

test_str = "[5] 우리아이성장축하 및 지문등록우대이율 (최대 연 0.5%p)	①신규(또는 재예치) 시 고객 연령이 만0세, 7세, 13세, 16세, 19세인 경우 해당 연령이 속한 계약기간에 대하여 연0.5%p 우대 ②계약기간 중 지문등록 후 경찰서장 발급의 [아동 등 사전신고증]을 계약기간의 만기일 전일까지 제출하는 경우 연0.1%p(단, 지문등록 우대이율은 계약기간 중 1회만 등록 가능하며, 재예치된 계좌는 재예치시마다 다시 등록하고 제출한 경우 우대이율 적용 가능) ※①과②모두 충족시에도 최대 연 0.5%p"
result = util.create_preferential_json(test_str)
print(result)

test_str = "① 저탄소 실천 적금 보유 우대이율 : 0.10%p - 이 예금의 해지 시 저탄소 실천 적금 보유하고 있는 경우 적용 - 만기일 당일 해지분은 우대이율 적용"
result = util.create_preferential_json(test_str)
print(result)

test_str ="② 비대면 채널 가입 또는 종이통장 미발행 우대이율 : 0.10%p      - 비대면 채널을 통해 이 예금을 가입하거나 만기일까지 종이통장을 미발행하는 경우 적용- 단, 종이통장 미발행 우대이율은 개인 및 개인사업자만 적용가능(법인 불가)"
result = util.create_preferential_json(test_str)
print(result)




