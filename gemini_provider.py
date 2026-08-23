import os, base64, requests, time

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
TEXT_MODEL_FALLBACK = os.environ.get("TEXT_MODEL_FALLBACK", "gemini-3.6-flash")
IMAGE_MODEL_FALLBACK = os.environ.get("IMAGE_MODEL_FALLBACK", "gemini-3.1-flash-lite-image")
BASE_URL = os.environ.get("BASE_URL", "https://generativelanguage.googleapis.com/v1beta/models")
LAST_FALLBACK_USED = None


 #url을 만드는 데 필요한 설정 값을 env에 추가 해주시고 URL을 만들어 주세요. 현재 google gemini api기준으로 작성 하였습니다. 

def _call(model, body, timeout=60, fallback=None):
    global LAST_FALLBACK_USED
    LAST_FALLBACK_USED = None
    url = f"{BASE_URL}/{model}:generateContent"
    try:
        r = requests.post(
            url,
            headers={"x-goog-api-key": os.environ["API_KEY"]},
            json=body,
            timeout=timeout,
        )
    except (requests.Timeout, requests.ConnectionError):
        print(f"[_call] {model} 요청 실패, 2초 대기 후 같은 모델({model})로 재시도합니다.")
        time.sleep(2)
        return requests.post(
            url,
            headers={"x-goog-api-key": os.environ["API_KEY"]},
            json=body,
            timeout=timeout,
        )

    if r.status_code in (429, 500, 503) and fallback:
        print(f"[_call] {model} 응답 {r.status_code}, 2초 대기 후 {fallback} 모델로 재시도합니다.")
        time.sleep(2)
        LAST_FALLBACK_USED = fallback
        fallback_url = f"{BASE_URL}/{fallback}:generateContent"
        r = requests.post(
            fallback_url,
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
    r = _call(TEXT_MODEL, body, fallback=TEXT_MODEL_FALLBACK)
    if r.status_code != 200:
        raise RuntimeError(f"generate_text 호출 실패: 상태 코드 {r.status_code}, 응답 {r.text[:300]}")
    data = r.json()
    if "candidates" not in data:
        raise RuntimeError(f"generate_text 응답에 candidates가 없습니다: {r.text[:300]}")
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p["text"] for p in parts if "text" in p)

def generate_image(prompt :str) -> bytes:
    #필요하시면 해당 내용부분을 바꾸신 provider
    body = {"contents": [{"parts": [{"text": prompt}]}],
             "generationConfig": {
                                    "responseModalities": ["IMAGE"],
                                   "imageConfig": {"aspectRatio": "1:1"}
                                 }        
           }
    r = _call(IMAGE_MODEL, body, fallback=IMAGE_MODEL_FALLBACK)
    if r.status_code != 200:
        raise RuntimeError(f"generate_image 호출 실패: 상태 코드 {r.status_code}, 응답 {r.text[:300]}")
    data = r.json()
    if "candidates" not in data:
        raise RuntimeError(f"generate_image 응답에 candidates가 없습니다: {r.text[:300]}")
    parts = data["candidates"][0]["content"]["parts"]
    for p in parts:
         if "inlineData" in p:
          #  print(p["inlineData"]["mimeType"]) # 이미지 파일 타입확인 모델에 따라 요청으로 바꿀수 없는 경우도 있어서 외부에서 png전환
            return base64.b64decode(p["inlineData"]["data"])
    keys = [list(p.keys()) for p in parts]
    raise RuntimeError(f"generate_image 응답에 이미지 데이터가 없습니다: {keys}") 