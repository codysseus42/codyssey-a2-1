# 규칙

- 새로운 추상화를 도입하지 않는다. 클래스, 데코레이터, 베이스 클래스를 만들지 않는다.
- 기존 함수의 구조와 시그니처를 그대로 따른다. 리팩터링하지 않는다.
- 프롬프트는 prompts/*.txt에서 읽는다. 코드에 하드코딩하지 않는다.
- API 호출은 gemini_provider의 generate_text / generate_image만 사용한다.
- 파일 읽기/쓰기에 encoding="utf-8", json.dumps에 ensure_ascii=False를 붙인다.
- 경로는 pathlib의 Path와 / 연산자를 쓴다. 문자열 결합을 하지 않는다.
- 스테이지 실패 시 None을 반환하고 파이프라인은 다음 단계를 계속 진행한다.
- 주석과 출력 메시지는 한국어로 쓴다.
- 요청하지 않은 파일을 만들지 않는다
- 라이브러리를 새로 추가하지 않는다. 표준 라이브러리, requests, python-dotenv, matplotlib, pillow만 쓴다.
