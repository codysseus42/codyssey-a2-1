import os, base64, requests

"""
Gemini API 호출 계층.

.env 설정:
  GEMINI_API_KEY    필수
  TEXT_MODEL        기본 gemini-3.7-flash
  IMAGE_MODEL       기본 gemini-3.1-flash-image
  BASE_URL   기본 https://generativelanguage.googleapis.com/v1beta/models

다른 프로바이더로 교체할 때 바꿀 곳:
  _call()           URL 조립과 인증 헤더
  generate_text()   요청 바디, 응답에서 텍스트 추출
  generate_image()  요청 바디, 응답에서 이미지 바이트 추출

호출부는 아래 두 시그니처만 사용한다:
  generate_text(prompt: str) -> str
  generate_image(prompt: str) -> bytes
"""

TEXT_MODEL = os.environ.get("TEXT_MODEL", "gemini-3.7-flash")
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gemini-3.1-flash-image")
BASE_URL = os.environ.get("BASE_URL", "https://generativelanguage.googleapis.com/v1beta/models")


 #url을 만드는 데 필요한 설정 값을 env에 추가 해주시고 URL을 만들어 주세요. 현재 google gemini api기준으로 작성 하였습니다. 

def _call(model, body, timeout=60):
    url = f"{BASE_URL}/{model}:generateContent"
    r = requests.post(
        url,
        headers={"x-goog-api-key": os.environ["API_KEY"]},
        json=body,
        timeout=timeout,
    )
    return r

def generate_text(prompt: str) -> str:
    #필요하시면 해당 내용부분을 바꾸신 provider
    body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                                    "responseMimeType": "application/json"
                                }
           }
    r = _call(TEXT_MODEL, body)
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p["text"] for p in parts if "text" in p)

def generate_image(prompt :str) -> bytes:
    #필요하시면 해당 내용부분을 바꾸신 provider
    body = {"contents": [{"parts": [{"text": prompt}]}],
             "generationConfig": {
                                    "responseModalities": ["IMAGE"],
                                   "imageConfig": {"aspectRatio": "1:1"}
                                 }        
           }
    r = _call(IMAGE_MODEL, body)
    print(r.status_code)
    parts = r.json()["candidates"][0]["content"]["parts"]
    print([list(p.keys()) for p in parts])
    for p in parts:
         if "inlineData" in p:
            print(p["inlineData"]["mimeType"])
            return base64.b64decode(p["inlineData"]["data"]) 