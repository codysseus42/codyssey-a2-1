import json, os
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
import gemini_provider as gp

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
    try:
        jsonResult = json.loads(result)
    except json.JSONDecodeError as e:
        errorPath = out_dir / "pipeline" / "error"
        errorPath.mkdir(parents=True,exist_ok=True)
        (errorPath /f"{stage_name}_raw.txt").write_text(result, encoding="utf-8")
        print(f"[{stage_name}] JSON 파싱 실패: {e}")
        return None
    path = out_dir / "pipeline" / f"{stage_name}.json"
    path.write_text(json.dumps(jsonResult, ensure_ascii=False, indent=2),encoding="utf-8")

    if jsonResult.get("status") == 'error':
        print(f"[{stage_name}] 진행불가: {jsonResult.get('error')}")
        return None
    return jsonResult

def main():
    load_dotenv()
    brief_path = "./brief_sample/brief_cafe.json"
    brief = load_brief(brief_path)
    out = Path("./output") / Path(brief_path).stem
    out.mkdir(parents=True, exist_ok=True)
    (out / "pipeline").mkdir(exist_ok=True)

    context = {"brief": brief}

    print("[1/5] 브랜드 네이밍 생성 중...")
    naming = run_stage("naming", brief, out)
    if naming is None:
        naming = run_stage("naming", brief, out)
    if naming is None:
        print("[naming] 재시도 후에도 실패했습니다. 다음 단계로 진행합니다.")
    elif naming.get("names") is not None:
        context["names"] = naming["names"]

    print("[2/5] 슬로건 생성 중...")
    slogan = run_stage("slogan", context, out)
    if slogan is not None and slogan.get("slogans") is not None:
        context["slogans"] = slogan["slogans"]

    print("[3/5] 브랜드 스토리 생성 중...")
    story = run_stage("story", context, out)
    if story is not None and story.get("story") is not None:
        context["story"] = story["story"]

    print("[4/5] 컬러 팔레트 생성 중...")
    palette = run_stage("palette", context, out)
    if palette is not None:
        palette_data = {}
        if palette.get("main") is not None:
            palette_data["main"] = palette["main"]
        if palette.get("sub") is not None:
            palette_data["sub"] = palette["sub"]
        if palette_data:
            context["palette"] = palette_data

    print(context)    

if __name__ == "__main__":
    main()