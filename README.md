# 키레네 로컬 일기 에이전트

《붕괴: 스타레일》 키레네와 하루를 되돌아보는 대화를 나누면, 키레네가 일기를 대신 써서 저장해준다.

## 실행

```bash
ollama serve
ollama pull gemma3:4b
python main.py
```

## 사용

키레네와 오늘 있었던 일을 자유롭게 얘기한 뒤 `/일기`를 입력하면 대화 내용으로 일기를 생성해 `diary/YYYY-MM-DD.md`에 저장한다. `/종료`는 저장 없이 종료.

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
