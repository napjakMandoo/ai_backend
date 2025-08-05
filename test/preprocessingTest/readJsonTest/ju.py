import json

file_path = "/src/crawler/resultData/JEJU.json"  # 읽을 JSON 파일
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)              # dict 또는 list 로 로드

# 사용 예시
for i in data:
    print(i)
