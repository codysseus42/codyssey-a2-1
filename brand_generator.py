import json, os, traceback
from datetime import datetime
from io import BytesIO
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
def log_warning(out_dir: Path, stage_name: str, message: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} [{stage_name}] {message}\n"
    with open(out_dir / "warning.txt", "a", encoding="utf-8") as f:
        f.write(line)

def save_palette_image(palette_data: dict, out_dir: Path) -> None:
    main = palette_data.get("main")
    subs = palette_data.get("sub") or []
    swatches = []
    if main is not None:
        swatches.append((main, 2))
    for s in subs:
        swatches.append((s, 1))
    total_units = sum(width for _, width in swatches)
    fig, ax = plt.subplots(figsize=(total_units * 1.5, 3))
    x = 0
    for color, width in swatches:
        ax.add_patch(plt.Rectangle((x, 0), width, 1, color=color["hex"]))
        ax.text(x + width / 2, -0.15, f"{color['name']}\n{color['hex']}",
                ha="center", va="top", fontsize=10)
        x += width
    ax.set_xlim(0, total_units)
    ax.set_ylim(-0.6, 1)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_dir / "color_palette.png")
    plt.close(fig)

def run_stage(stage_name: str, payload: dict, out_dir: Path) -> dict | None:
    try:
        prompt = load_prompt(stage_name,payload)
        try:
            result = gp.generate_text(prompt)
        except RuntimeError as e:
            print(f"[{stage_name}] API 호출 실패: {e}")
            return None
        if gp.LAST_FALLBACK_USED is not None:
            log_warning(out_dir, stage_name, f"폴백 모델 사용: {gp.LAST_FALLBACK_USED}")
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
    except Exception as e:
        log_warning(out_dir, stage_name, f"{type(e).__name__}: {e}")
        print(f"[{stage_name}] 예상치 못한 오류: {e}")
        return None

def main():
    out = None
    try:
        load_dotenv()
        brief_path = "./brief_sample/brief_cafe.json"
        brief = load_brief(brief_path)
        out = Path("./output") / Path(brief_path).stem
        out.mkdir(parents=True, exist_ok=True)
        (out / "pipeline").mkdir(exist_ok=True)

        context = {"brief": brief}

        print("[1/6] 브랜드 네이밍 생성 중...")
        naming = run_stage("naming", brief, out)
        if naming is None:
            naming = run_stage("naming", brief, out)
        if naming is None:
            print("[naming] 재시도 후에도 실패했습니다. 다음 단계로 진행합니다.")
        elif naming.get("names") is not None:
            context["names"] = naming["names"]
            for i, n in enumerate(naming["names"], 1):
                print(f"  {i}. {n['ko']} ({n['en']}) - {n['meaning']}")

        print("[2/6] 슬로건 생성 중...")
        slogan = run_stage("slogan", context, out)
        if slogan is not None and slogan.get("slogans") is not None:
            context["slogans"] = slogan["slogans"]
            for i, s in enumerate(slogan["slogans"], 1):
                print(f"  {i}. {s}")

        print("[3/6] 브랜드 스토리 생성 중...")
        story = run_stage("story", context, out)
        if story is not None and story.get("story") is not None:
            context["story"] = story["story"]
            print(f"  {story['story']} ({len(story['story'])}자)")

        print("[4/6] 컬러 팔레트 생성 중...")
        palette = run_stage("palette", context, out)
        if palette is not None:
            palette_data = {}
            if palette.get("main") is not None:
                palette_data["main"] = palette["main"]
            if palette.get("sub") is not None:
                palette_data["sub"] = palette["sub"]
            if palette_data:
                context["palette"] = palette_data
                save_palette_image(palette_data, out)
            if palette.get("main") is not None:
                m = palette["main"]
                print(f"  메인: {m['hex']} ({m['name']}) - {m['role']}")
            if palette.get("sub") is not None:
                for s in palette["sub"]:
                    print(f"  서브: {s['hex']} ({s['name']}) - {s['role']}")

        print("[5/6] 로고 컨셉 생성 중...")
        logo = run_stage("logo", context, out)
        if logo is not None and logo.get("logo_prompts") is not None:
            print("[6/6] 로고 이미지 생성 중...")
            logos = []
            total = len(logo["logo_prompts"])
            for i, item in enumerate(logo["logo_prompts"], 1):
                print(f"  {item['id']} [{i}/{total}] 생성 중...")
                try:
                    image_bytes = gp.generate_image(item["prompt"])
                except RuntimeError as e:
                    print(f"[logo] {item['id']} 이미지 생성 실패: {e}")
                    log_warning(out, item["id"], f"이미지 생성 실패: {e}")
                    continue
                if gp.LAST_FALLBACK_USED is not None:
                    log_warning(out, item["id"], f"폴백 모델 사용: {gp.LAST_FALLBACK_USED}")
                filename = f"{item['id']}.png"
                image = Image.open(BytesIO(image_bytes))
                image.save(out / filename)
                logos.append(filename)
            context["logos"] = logos

        print(context)
    except Exception as e:
        if out is not None:
            log_warning(out, "main", traceback.format_exc())
        print(f"[main] 예상치 못한 오류: {e}")
        raise

if __name__ == "__main__":
    main()