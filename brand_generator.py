import json, os, sys, base64
from pathlib import Path
import requests
from dotenv import load_dotenv
from PIL import Image
import gemini_provider as gp


load_dotenv()

REQUIRED = ["industry", "target", "keywords"]

def load_brief(filePath) -> dict:
    path = Path(filePath)
    if not path.exists():
        raise ValueError("파일이 없습니다.")
    try:
        brief = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 형식이 올바르지 않습니다: {e}")
    if not isinstance(brief, dict):
        raise ValueError("브리프는 JSON 객체 하나여야 합니다")
    missing = [k for k in REQUIRED if not brief.get(k)]
    if missing:
        raise ValueError(f"필수 항목이 없습니다: {', '.join(missing)}")
    if not isinstance(brief["keywords"], list):
        raise ValueError(f"keywords는 배열이어야 합니다. 현재 값: {brief['keywords']}")
    return brief
def load_prompt(stage_name: str, payload: dict) -> str:
    template = Path(f"./prompts/{stage_name}.txt").read_text(encoding="utf-8")
    if "{{입력}}" not in template:# 입력 값을 넣을 {{입력}} 이 없을 경우 검사
        raise ValueError(f"prompts/{stage_name}.txt에 {{{{입력}}}} 자리표시자가 없습니다")
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
    return template.replace("{{입력}}", payload_text)
def run_stage(stage_name: str, payload: dict, out_dir: Path) -> dict | None: 
    prompt = load_prompt(stage_name,payload)
    result = gp.generate_text(prompt)
    path = out_dir / "pipeline" / f"{stage_name}.txt"
    path.write_text(result,encoding="utf-8")
    try:
        jsonResult = json.loads(result)
    except json.JSONDecodeError as e:
        print(f"[{stage_name}] JSON 파싱 실패: {e}")
        return None
    if jsonResult.get("status") == 'error':
        print(f"[{stage_name}] 진행불가: {jsonResult.get('error')}")
        return None
    return jsonResult

def main():
    load_dotenv()
    brief = load_brief("./brief_sample/brief_cafe.json")
    out = Path("./output")
    out.mkdir(parents=True, exist_ok=True)
    (out / "pipeline").mkdir(exist_ok=True)

    naming = run_stage("naming", brief, out)
    print(naming)

#def menu():
#    print("\n=== 브랜드 생성기 ===")
#    print("종료하려면 0을 입력하세요.")

# def main():
#     api_key = os.environ.get("API_KEY")
#     if not api_key:
#         print(".env 파일에 API_KEY를 설정하세요.(.env.example 참고)")
#         sys.exit(1)
#     while True:
#         # menu()
#         filePath = input("브리프 파일 경로를 입력하세요 종료하시려면 0을 입력해주세요.: ").strip()
#         brief = load_brief(filePath)
#         else:
#             if filePath.isdigit():
#                 filePath = int(filePath)
#                 if filePat == 0:
#                     break
        
#             outputPath = input("출력파일 경로를 입력하세요 (엔터 시 ./output): ").strip()
#             if not outputPath:
#                 outputPath ="./output"
#             else:

#     print("프로그램을 종료합니다.")          

if __name__ == "__main__":
    main()