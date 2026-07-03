# 키레네 로컬 일기 에이전트

《붕괴: 스타레일》 키레네와 하루를 되돌아보는 대화를 나누면, 키레네가 일기를 대신 써서 저장해준다.

## 실행

```bash
ollama serve
ollama pull gemma3:4b
python main.py
```

## 테스트

로컬 모델 없이 코드 구조만 검증한다.

```bash
python -m unittest discover -s tests
```

## 사용

키레네와 오늘 있었던 일을 자유롭게 얘기한 뒤 `/일기`를 입력하면 대화 내용으로 일기를 생성해 `diary/YYYY-MM-DD.md`에 저장한다.

- `/일기` 또는 `/diary` — 지금까지의 대화로 일기를 생성하고 저장
- `/도움말` 또는 `/help` — 명령어 목록 확인
- `/기억` 또는 `/memory` — 저장된 장기 기억과 일기 인덱스 확인
- `/최근` 또는 `/recent` — 최근 일기 인덱스 확인
- `/일기검색 검색어` 또는 `/search query` — 일기 인덱스 검색
- `/이름 홍길동` 또는 `/name Hong` — 사용자 이름 저장
- `/기억추가 내용` 또는 `/remember text` — 장기 기억 메모 추가
- `/선호추가 내용` 또는 `/prefer text` — 선호하는 응답 방식 추가
- `/회피추가 내용` 또는 `/avoid text` — 피해야 할 응답 방식 추가
- `/종료`, `/exit`, `/quit` — 저장 없이 종료

## 구조

- `main.py` — CLI 입출력과 명령 처리
- `hermes/agent.py` — Hermes 오케스트레이터. 페르소나, 메모리, 모델, 도구를 조율
- `hermes/llm.py` — 로컬 LLM 클라이언트. 기본값은 Ollama chat API
- `hermes/memory.py` — 현재 세션 대화 메모리
- `hermes/tools.py` — 에이전트가 사용하는 도구. 현재는 일기 저장 도구
- `persona.py` — 키레네 시스템 프롬프트·일기 지시문
- `storage.py` — 저장소 추상화. `LocalMarkdownStorage`(현재) / `NotionStorage`(스텁)

## Hermes 구조

이 프로젝트에서 Hermes는 단일 스크립트가 모든 일을 처리하지 않고, 아래 계층을 분리하는 로컬 에이전트 구조를 뜻한다.

- Message: 모델에 전달되는 역할별 메시지
- Memory: 현재 세션 대화 기록
- Model: 로컬 LLM 호출
- Tools: 파일 저장, 추후 Notion 같은 외부 작업
- Orchestrator: 입력을 받아 메모리에 넣고, 모델 응답을 만들고, 필요한 도구를 호출

## Notion 연동 (나중에)

`storage.py`의 `NotionStorage` docstring에 구현 가이드가 있다. 구현 후 `main.py`에서 한 줄만 바꾸면 된다:

```python
storage = NotionStorage(token=os.environ["NOTION_TOKEN"], database_id=os.environ["NOTION_DATABASE_ID"])
```

## 설정

- `CYRENE_MODEL` 환경변수로 모델 변경 가능 (기본: `gemma3:4b`)
- `CYRENE_LLM_URL` 환경변수로 Ollama 호환 chat API 주소 변경 가능
- `CYRENE_MAX_TOKENS` 환경변수로 응답 길이 변경 가능 (기본: `1024`)
- `CYRENE_MEMORY_DIR` 환경변수로 장기 메모리 디렉터리 변경 가능 (기본: `memory`)

`.env.example`은 다른 작업 컴퓨터에서 사용할 설정 예시다. `.env` 파일이 있으면 앱 시작 시 자동으로 읽는다. 이미 셸에 설정된 환경변수는 `.env`보다 우선한다.

## 메모리 파일

개인 데이터 파일은 Git에 올리지 않는다.

- `memory/profile.json` — 사용자 프로필 장기 기억
- `memory/diary_index.json` — 과거 일기 요약 인덱스

저장소에는 구조 참고용 예시만 포함한다.

- `memory/profile.example.json`
- `memory/diary_index.example.json`

`/일기`로 저장하면 `memory/diary_index.json`에 날짜, 저장 위치, 짧은 요약이 자동으로 기록된다. 요약은 현재 모델을 추가 호출하지 않고 일기 본문 앞부분에서 만든다.
