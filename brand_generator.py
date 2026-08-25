import json, traceback
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
            log_warning(out_dir, stage_name, f"API 호출 실패: {e}")
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
            log_warning(out_dir, stage_name, f"JSON 파싱 실패: {e} (원본: pipeline/error/{stage_name}_raw.txt)")
            print(f"[{stage_name}] JSON 파싱 실패: {e}")
            return None
        path = out_dir / "pipeline" / f"{stage_name}.json"
        path.write_text(json.dumps(jsonResult, ensure_ascii=False, indent=2),encoding="utf-8")

        if jsonResult.get("status") == 'error':
            log_warning(out_dir, stage_name, f"진행 불가: {jsonResult.get('error')}")
            print(f"[{stage_name}] 진행불가: {jsonResult.get('error')}")
            return None
        return jsonResult
    except Exception as e:
        log_warning(out_dir, stage_name, f"{type(e).__name__}: {e}")
        print(f"[{stage_name}] 예상치 못한 오류: {e}")
        return None

def build_brand_result(brief: dict, naming: dict | None, slogan: dict | None, story: dict | None,
                        palette_data: dict | None, logos: list | None, failed_stages: list,
                        out_dir: Path) -> None:
    result = {
        "generated_at": datetime.now().isoformat(),
        "brief": brief,
        "names": naming.get("names") if naming is not None else None,
    }
    if naming is not None and naming.get("comparison") is not None:
        result["comparison"] = naming["comparison"]
    result["slogans"] = slogan.get("slogans") if slogan is not None else None
    if story is not None and story.get("story") is not None:
        result["story"] = {"text": story["story"], "char_count": len(story["story"])}
    else:
        result["story"] = None
    if palette_data:
        result["palette"] = {**palette_data, "image": "color_palette.png"}
    else:
        result["palette"] = None
    result["logos"] = logos
    result["failed_stages"] = failed_stages

    path = out_dir / "brand_result.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    out = None
    try:
        load_dotenv()
        print("=== 브랜드 아이덴티티 생성기 ===")
        while True:
            brief_path = input("브리프 파일 경로를 입력하세요 (엔터: ./brief_sample/brief_cafe.json, 0: 종료): ").strip()
            if brief_path == "0":
                print("프로그램을 종료합니다.")
                return
            if brief_path == "":
                brief_path = "./brief_sample/brief_cafe.json"
            try:
                brief = load_brief(brief_path)
                break
            except ValueError as e:
                print(e)

        out_input = input("출력 폴더를 입력하세요 (엔터: ./output): ").strip()
        if out_input == "":
            out_input = "./output"
        out = Path(out_input) / Path(brief_path).stem
        out.mkdir(parents=True, exist_ok=True)

        pipeline_dir = out / "pipeline"
        if pipeline_dir.exists():
            for f in pipeline_dir.rglob("*"):
                if f.is_file():
                    f.unlink()
        for f in out.glob("*.png"):
            f.unlink()
        warning_path = out / "warning.txt"
        if warning_path.exists():
            warning_path.unlink()

        pipeline_dir.mkdir(exist_ok=True)

        context = {"brief": brief}
        failed_stages = []

        print("[1/6] 브랜드 네이밍 생성 중...")
        naming = run_stage("naming", brief, out)
        if naming is None:
            naming = run_stage("naming", brief, out)
        if naming is None:
            print("[naming] 재시도 후에도 실패했습니다. 다음 단계로 진행합니다.")
            failed_stages.append("naming")
        elif naming.get("names") is not None:
            context["names"] = naming["names"]
            names_count = len(naming["names"])
            if not (3 <= names_count <= 5):
                msg = f"names 개수 {names_count}, 규격 3~5"
                log_warning(out, "naming", msg)
                print(f"[naming] {msg}")
            for i, n in enumerate(naming["names"], 1):
                print(f"  {i}. {n['ko']} ({n['en']}) - {n['meaning']}")
        else:
            failed_stages.append("naming")

        print("[2/6] 슬로건 생성 중...")
        slogan = run_stage("slogan", context, out)
        if slogan is not None and slogan.get("slogans") is not None:
            context["slogans"] = slogan["slogans"]
            slogans_count = len(slogan["slogans"])
            if slogans_count != 3:
                msg = f"slogans 개수 {slogans_count}, 규격 3"
                log_warning(out, "slogan", msg)
                print(f"[slogan] {msg}")
            for i, s in enumerate(slogan["slogans"], 1):
                print(f"  {i}. {s}")
        else:
            failed_stages.append("slogan")

        print("[3/6] 브랜드 스토리 생성 중...")
        story = run_stage("story", context, out)
        if story is not None and story.get("story") is not None:
            context["story"] = story["story"]
            story_len = len(story["story"])
            if not (200 <= story_len <= 400):
                msg = f"story 길이 {story_len}자, 규격 300자 내외"
                log_warning(out, "story", msg)
                print(f"[story] {msg}")
            print(f"  {story['story']} ({len(story['story'])}자)")
        else:
            failed_stages.append("story")

        print("[4/6] 컬러 팔레트 생성 중...")
        palette_data = None
        palette = run_stage("palette", context, out)
        if palette is not None:
            palette_data = {}
            if palette.get("main") is not None:
                palette_data["main"] = palette["main"]
            if palette.get("sub") is not None:
                palette_data["sub"] = palette["sub"]
                sub_count = len(palette["sub"])
                if not (2 <= sub_count <= 3):
                    msg = f"sub 개수 {sub_count}, 규격 2~3"
                    log_warning(out, "palette", msg)
                    print(f"[palette] {msg}")
            if palette_data:
                context["palette"] = palette_data
                save_palette_image(palette_data, out)
            else:
                palette_data = None
            if palette.get("main") is not None:
                m = palette["main"]
                print(f"  메인: {m['hex']} ({m['name']}) - {m['role']}")
            if palette.get("sub") is not None:
                for s in palette["sub"]:
                    print(f"  서브: {s['hex']} ({s['name']}) - {s['role']}")
        if palette_data is None:
            failed_stages.append("palette")

        print("[5/6] 로고 컨셉 생성 중...")
        logo = run_stage("logo", context, out)
        logos = None
        if logo is not None and logo.get("logo_prompts") is not None:
            print("[6/6] 로고 이미지 생성 중...")
            logos = []
            total = len(logo["logo_prompts"])
            if total != 3:
                msg = f"logo_prompts 개수 {total}, 규격 3"
                log_warning(out, "logo", msg)
                print(f"[logo] {msg}")
            fail_count = 0
            for i, item in enumerate(logo["logo_prompts"], 1):
                print(f"  {item['id']} [{i}/{total}] 생성 중...")
                try:
                    image_bytes = gp.generate_image(item["prompt"])
                except RuntimeError as e:
                    print(f"[logo] {item['id']} 이미지 생성 실패: {e}")
                    log_warning(out, item["id"], f"이미지 생성 실패: {e}")
                    fail_count += 1
                    continue
                if gp.LAST_FALLBACK_USED is not None:
                    log_warning(out, item["id"], f"폴백 모델 사용: {gp.LAST_FALLBACK_USED}")
                filename = f"{item['id']}.png"
                image = Image.open(BytesIO(image_bytes))
                image.save(out / filename)
                logos.append({"file": filename, "concept": item.get("concept")})
            if fail_count > 0:
                summary = f"로고 시안 {fail_count}개 생성 실패, {len(logos)}개 저장됨"
                print(f"[logo] {summary}")
                log_warning(out, "logo", summary)
            if not logos:
                failed_stages.append("logo")
                logos = None
            context["logos"] = logos
        else:
            failed_stages.append("logo")

        build_brand_result(brief, naming, slogan, story, palette_data, logos, failed_stages, out)
        if failed_stages:
            print(f"완료 (실패한 단계: {', '.join(failed_stages)}). {out} 폴더를 확인하세요.")
        else:
            print(f"완료! {out} 폴더를 확인하세요.")
        if (out / "warning.txt").exists():
            print(f"경고가 기록되었습니다: {out / 'warning.txt'}")
        error_dir = out / "pipeline" / "error"
        if error_dir.exists() and any(f.is_file() for f in error_dir.iterdir()):
            print(f"파싱 실패 응답 원본: {error_dir}/")
    except Exception as e:
        if out is not None:
            log_warning(out, "main", traceback.format_exc())
        print(f"[main] 예상치 못한 오류: {e}")
        raise

if __name__ == "__main__":
    main()