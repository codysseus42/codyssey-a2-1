import json, os, sys, base64
from pathlib import Path
import requests
from dotenv import load_dotenv
from PIL import Image


load_dotenv()

def menu():
    print("\n=== 브랜드 생성기 ===")
    print("종료하려면 0을 입력하세요.")

def apiText(prompt,jsonBrief):
   URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
   r = requests.post(
    URL,
    headers={"x-goog-api-key": os.environ["API_KEY"]},
    json={"contents": [{"parts": [{"text": prompt}]}]},
    timeout=60,
    )
   print(r.status_code)
   print(json.dumps(r.json(), ensure_ascii=False, indent=2))

def main():
    api_key = os.environ.get("API_KEY")
    if not api_key:
        print(".env 파일에 API_KEY를 설정하세요.(.env.example 참고)")
        sys.exit(1)


    while True:
        menu()
        filePath = input("브리프 파일 경로를 입력하세요 종료하시려면 0을 입력해주세요.: ").strip()
        if not filePath:
            print("브리프 파일 경로가 입력되지 않았습니다.")
            continue
        else:
            if filePath.isdigit():
                filePath = int(filePath)
                if filePat == 0:
                    break
        #여기서 실제 파일 존재 여부 파일 형식 파싱을 진행
            outputPath = input("출력파일 경로를 입력하세요 (엔터 시 ./output): ").strip()
            if not outputPath:
                print("출력 파일 경로가 입력되지 않았습니다.")
                continue
            else:
                #여기서 또 점검
                outputPath +="/output"

    print("프로그램을 종료합니다.")            

if __name__ == "__main__":
    main()