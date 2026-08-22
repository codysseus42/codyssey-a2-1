import json, os, sys, base64
from pathlib import Path
import requests
from dotenv import load_dotenv
import gemini_provider as gp


def apiText(prompt,jsonBrief,apikey):

   text = prompt.replace("{{입력}}",jsonBrief)
   URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.0-flash:generateContent"
   r = requests.post(
    URL,
    headers={"x-goog-api-key": apikey},
    json={"contents": [{"parts": [{"text": text}]}]},
    timeout=60,
    )
   print(r.status_code)
   print(json.dumps(r.json(), ensure_ascii=False, indent=2))

def test_call():
    load_dotenv()
    prompt = """당신은 브랜드 네이밍 전문가다. 이 JSON의 brief를 입력으로 브랜드명 후보 3~5개를 생성한다.
각 후보에 한글 이름(ko), 영문 이름(en), 의미와 유래(meaning)를 쓴다.

status 규칙:
- brief의 industry, target, keywords 중 하나라도 없거나 비어 있으면
  {"status": "error", "message": "무엇이 왜 문제인지"}만 출력하고 끝낸다.
- tone이 없으면 keywords와 target에서 톤을 추론해 진행하고, status를 "warning"으로,
  message에 추론 사실과 추론한 톤을 쓴다.
- 문제가 없으면 status는 "ok"이고 message는 쓰지 않는다.
- 어떤 경우든 실제 적용한 톤을 tone_used에 쓴다.

처리 규칙:
- competitors가 있으면 경쟁사 이름의 어감·조어 방식과 우리 후보들의 차이를 comparison에 쓴다.
  그 회사의 사업 내용은 추측하지 않는다. 없으면 comparison을 만들지 않는다.
- notes가 있으면 반영하고, 없으면 무시한다.

네이밍 원칙:
- 2~5음절, 한 번 듣고 기억되는 이름. 발음이 쉬울 것.
- industry를 직접 말하지 않아도 연상될 것. keywords 중 최소 1개의 이미지를 담을 것.
- '에코', '그린', '네이처' 같은 상투적 접두어를 피할 것.
- 영문 이름(en)은 한글 이름의 음차 또는 자연스러운 의역으로, 한글과 나란히 써도 어색하지 않을 것.

출력은 JSON만. 코드펜스·설명 금지. 첫 글자 {, 마지막 글자 }.
형식: {"status": "...", "message": "...", "tone_used": "...", "names": [{"ko": "...", "en": "...", "meaning": "..."}], "comparison": [{"competitor": "...", "difference": "..."}]}

[브리프]
{{입력}}

"""
    jsonBrief = """{
        "industry": "친환경 화장품",
        "target": "20-30대 여성",
        "keywords": ["자연", "순수", "건강"],
        "tone": "따뜻하고 신뢰감 있는",
        "competitors": ["이니스프리", "아로마티카"]
        }"""
    # prompt = prompt.replace("{{입력}}",jsonBrief)   
    # txtResult=gp.generate_text(prompt)
    # print(txtResult)
    image_prompt = "minimalist flat vector logo, abstract geometric interpretation of a traditional Korean rice cake stamp pattern, simplified into clean geometric shapes, solid background color #F4EDE1, main shape in #8C5A2B, no text, no letters, no typography, flat vector style, solid background"
    data = gp.generate_image(image_prompt)
    print(type(data), len(data) if data else "None")
    if data:
            print(data[:4])   # b'\x89PNG' 면 PNG, b'\xff\xd8\xff' 면 JPEG
            Path("./test.png").write_bytes(data)
            print("saved")


if __name__ == "__main__":
    test_call()