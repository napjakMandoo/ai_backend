


import json

sh = "/home/jeonggiju/hanium/ai_backend/src/preprocessing/crawling/crawler/sh/suhyup_category_products_20250730_170125.json"
with open(sh, "r", encoding="utf-8") as f:
    data = json.load(f)              # dict 또는 list 로 로드

# 사용 예시
for i in data["products"]:
    print(i)
