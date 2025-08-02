import json
#
# woori = "/home/jeonggiju/hanium/ai_backend/src/preprocessing/crawling/crawler/woori/woori_bank_products.json"      # 읽을 JSON 파일
# with open(woori, "r", encoding="utf-8") as f:
#     data = json.load(f)
#
# print(type(data))
# print(data)
# #
#
hana = "/home/jeonggiju/hanium/ai_backend/src/preprocessing/crawling/crawler/hana/hana_bank_products.json"
with open(hana, "r", encoding="utf-8") as f:
    data = json.load(f)

print(data)
for i in data:
    print(i)
#
# #
# kb = "/home/jeonggiju/hanium/ai_backend/src/preprocessing/crawling/crawler/kb/kb_products.json"
# with open(kb, "r", encoding="utf-8") as f:
#     data = json.load(f)
#
# print(type(data))
# print(data)
#
# #
# nh="/home/jeonggiju/hanium/ai_backend/src/preprocessing/crawling/crawler/nh/nh_bank_products.json"
# with open(nh, "r", encoding="utf-8") as f:
#     data = json.load(f)
#
# print(type(data))
# print(data)
#
