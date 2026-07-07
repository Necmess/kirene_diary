# 키레네 로컬 일기 에이전트

《붕괴: 스타레일》 키레네와 하루를 되돌아보는 대화를 나누면, 키레네가 일기를 대신 써서 저장해준다.

## 실행

```bash
ollama serve
ollama pull gemma4:e4b
python main.py
```

Discord로 실행하려면 `discord.py`가 필요하다.

```bash
pip install -r requirements-discord.txt
python discord_bot.py
```

## 테스트

로컬 모델 없이 코드 구조만 검증한다.

```bash
python -m unittest discover -s tests
```

## 사용

키레네와 오늘 있었던 일을 자유롭게 얘기한 뒤 `/일기`를 입력하면 대화 내용으로 일기 초안을 만든다. 초안이 괜찮으면 `/저장`으로 저장한다.

- `/일기` 또는 `/diary` — 지금까지의 대화로 일기 초안 생성
- `/저장` 또는 `/save` — 마지막 일기 초안 저장
- `/초안삭제` 또는 `/discard` — 마지막 일기 초안 삭제
- `/도움말` 또는 `/help` — 명령어 목록 확인
- `/기억` 또는 `/memory` — 저장된 장기 기억과 일기 인덱스 확인
- `/최근` 또는 `/recent` — 최근 일기 인덱스 확인
- `/일기검색 검색어` 또는 `/search query` — 일기 인덱스 검색
- `/도구` 또는 `/tools` — 외부 도구 연결 상태 확인
- `/노션검색 검색어` 또는 `/notion query` — Notion MCP 검색
- `/노션읽기 페이지` 또는 `/notion-read page` — Notion MCP 페이지 읽기
- `/할일추가 내용` 또는 `/todo text` — Notion MCP 할 일 추가
- `/확인` 또는 `/confirm` — 대기 중인 외부 쓰기 작업 실행
- `/취소` 또는 `/cancel` — 대기 중인 외부 쓰기 작업 취소
- `/이름 홍길동` 또는 `/name Hong` — 사용자 이름 저장
- `/기억추가 내용` 또는 `/remember text` — 장기 기억 메모 추가
- `/선호추가 내용` 또는 `/prefer text` — 선호하는 응답 방식 추가
- `/회피추가 내용` 또는 `/avoid text` — 피해야 할 응답 방식 추가
- `/세션초기화` 또는 `/reset` — 현재 대화 세션 초기화
- `/종료`, `/exit`, `/quit` — 저장 없이 종료

## 구조

- `main.py` — CLI 입출력
- `discord_bot.py` — Discord 봇 실행 진입점
- `hermes/agent.py` — Hermes 오케스트레이터. 페르소나, 메모리, 모델, 도구를 조율
- `hermes/app.py` — CLI/Discord가 공유하는 에이전트·저장소 팩토리
- `hermes/commands.py` — `/일기`, `/기억`, `/검색` 같은 명령 파싱
- `hermes/config.py` — `.env`와 환경변수 기반 설정
- `hermes/discord_app.py` — Discord 메시지 어댑터
- `hermes/llm.py` — 로컬 LLM 클라이언트. 기본값은 Ollama chat API
- `hermes/mcp_client.py` — 분리된 MCP 프로세스와 통신하는 최소 클라이언트
- `hermes/memory.py` — 현재 세션 대화 메모리
- `hermes/tool_router.py` — 외부 도구 호출 정책과 라우팅
- `hermes/tools.py` — 에이전트가 사용하는 도구. 현재는 일기 저장 도구
- `hermes/wiki.py` — 옵시디언 위키 노트 생성, 태그 추출
- `hermes/embeddings.py` — 관련 일기 검색용 로컬 임베딩 클라이언트
- `persona.py` — 키레네 시스템 프롬프트·일기 지시문
- `storage.py` — 저장소 추상화. `LocalMarkdownStorage` / `NotionStorage`

## Hermes 구조

이 프로젝트에서 Hermes는 단일 스크립트가 모든 일을 처리하지 않고, 아래 계층을 분리하는 로컬 에이전트 구조를 뜻한다.

- Message: 모델에 전달되는 역할별 메시지
- Memory: 현재 세션 대화 기록
- Model: 로컬 LLM 호출
- Tools: 파일 저장, 추후 Notion 같은 외부 작업
- Orchestrator: 입력을 받아 메모리에 넣고, 모델 응답을 만들고, 필요한 도구를 호출

## 안전 조약

키레네 페르소나는 안전 조약보다 우선하지 않는다. 사용자가 자해, 자살, 죽고 싶다는 표현, 구체적인 방법 탐색, 유서 작성 요청을 하면 역할극이나 낭만적인 은유로 받지 않고 위기 대응 문구를 우선한다.

기본 원칙:

- 자해 방법, 치명성, 준비물, 은폐 방법, 실행 계획은 제공하지 않는다.
- 루프물, 기억, 죽음 같은 캐릭터 설정을 사용자의 현실 자해와 섞어 낭만화하지 않는다.
- 위기 신호가 있으면 혼자 있지 않게 하고 긴급 도움과 위기 상담 자원으로 연결한다.
- 일기에도 자해 실행 세부사항은 남기지 않고 감정과 안전 계획 중심으로 정리한다.

## 설정

- `CYRENE_MODEL` 환경변수로 모델 변경 가능 (기본: `gemma4:e4b`)
- `CYRENE_LLM_URL` 환경변수로 Ollama 호환 chat API 주소 변경 가능
- `CYRENE_MAX_TOKENS` 환경변수로 응답 길이 변경 가능 (기본: `1024`)
- `CYRENE_MEMORY_DIR` 환경변수로 장기 메모리 디렉터리 변경 가능 (기본: `memory`)
- `CYRENE_SAFETY_REGION` 위기 지원 지역 문구. `KR`, `US`, `GLOBAL` (기본: `GLOBAL`)
- `CYRENE_STORAGE` 저장소 선택. `local` 또는 `notion` (기본: `local`)
- `CYRENE_DIARY_DIR` 로컬 일기 저장 디렉터리 (기본: `diary`)
- `NOTION_TOKEN`, `NOTION_DATABASE_ID` Notion 저장소 사용 시 필요
- `DISCORD_BOT_TOKEN` Discord 봇 실행 시 필요
- `DISCORD_COMMAND_PREFIX` Discord에서 봇을 부를 접두어 (기본: `!키레네`)
- `CYRENE_NOTION_TOOL` Notion 외부 도구 사용 방식. `disabled` 또는 `mcp` (기본: `disabled`)
- `CYRENE_MCP_NOTION_URL` 분리된 Notion MCP 서버 URL
- `CYRENE_MCP_TIMEOUT` MCP 요청 타임아웃 초
- `CYRENE_MCP_NOTION_SEARCH_TOOL` Notion MCP 검색 도구명
- `CYRENE_MCP_NOTION_READ_TOOL` Notion MCP 페이지 읽기 도구명
- `CYRENE_MCP_NOTION_TODO_TOOL` Notion MCP 할 일 생성 도구명
- `CYRENE_OBSIDIAN_DIR` 옵시디언 볼트 경로. 설정하면 위키 브레인 기능 활성화 (기본: 비활성)
- `CYRENE_EMBED_MODEL` 관련 일기 검색에 쓸 임베딩 모델 (기본: `nomic-embed-text`)
- `CYRENE_EMBED_URL` Ollama 호환 임베딩 API 주소 (기본: `http://localhost:11434/api/embeddings`)

`.env.example`은 다른 작업 컴퓨터에서 사용할 설정 예시다. `.env` 파일이 있으면 앱 시작 시 자동으로 읽는다. 이미 셸에 설정된 환경변수는 `.env`보다 우선한다.

## Notion 연동

Notion 데이터베이스에는 최소한 아래 속성이 필요하다.

- `Name` — title
- `Date` — date

`.env`에서 저장소를 바꾼다.

```env
CYRENE_STORAGE=notion
NOTION_TOKEN=secret_xxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 옵시디언 위키 (두뇌)

일기 원문은 여전히 `CYRENE_STORAGE`가 가리키는 곳(Notion 또는 로컬 마크다운)에 저장된다. 옵시디언은 그 일기 원문을 대신하는 게 아니라, 태그와 "관련 일기" 링크로 서로 연결된 키레네의 두뇌 역할을 한다.

`CYRENE_OBSIDIAN_DIR`을 옵시디언 볼트 폴더로 지정하면, `/저장`으로 일기를 저장할 때마다:

1. 로컬 모델에게 짧은 키워드 태그를 몇 개 뽑아달라고 요청한다.
2. (`CYRENE_EMBED_MODEL`이 pull되어 있으면) 임베딩을 계산해서 과거 일기 중 의미적으로 비슷한 항목을 찾는다.
3. `{볼트}/일기/YYYY-MM-DD.md`에 요약, 태그, 관련 일기 `[[위키링크]]`, (Notion 저장이면) 원문 링크를 적는다.
4. `{볼트}/태그/태그이름.md` 페이지를 만들어서, 옵시디언 백링크로 "이 태그가 붙은 일기들"을 볼 수 있게 한다.

임베딩 모델이 없어도 태그/노트 생성은 그대로 동작하고, 관련 일기 링크만 비게 된다.

```bash
ollama pull nomic-embed-text
```

```env
CYRENE_OBSIDIAN_DIR=/path/to/ObsidianVault/키레네
```

## Discord 사용

Discord에서는 접두어 뒤에 말을 붙인다.

```text
!키레네 오늘은 코드 작업을 했어
!키레네 /일기
!키레네 /저장
!키레네 /기억
!키레네 /할일추가 내일 MCP 연결 확인
!키레네 /확인
```

봇 멘션으로도 호출할 수 있다.

## MCP 프로세스 분리

Discord 봇과 Notion MCP 서버는 같은 머신에 있어도 다른 프로세스로 둔다.

```text
discord_bot.py
→ HermesAgent
→ MCP client
→ Notion MCP server
→ Notion API
```

봇 프로세스는 Discord 토큰과 LLM 설정을 갖고, Notion MCP 프로세스는 Notion 토큰을 갖는다. 이렇게 하면 Notion 권한 경계가 분리되고, 나중에 Calendar/File/Todo 같은 MCP 서버를 추가하기 쉽다.

봇 쪽 `.env` 예:

```env
DISCORD_BOT_TOKEN=xxx
CYRENE_NOTION_TOOL=mcp
CYRENE_MCP_NOTION_URL=http://localhost:8765
```

MCP 서버 쪽 `.env` 예:

```env
NOTION_TOKEN=secret_xxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

현재 코드는 `tools/call` 형태의 JSON-RPC HTTP 요청을 보내는 최소 클라이언트 틀을 제공한다. 실제 MCP 서버의 transport와 도구명은 본 작업 환경에서 맞춘다.

기본 도구 정책:

- Notion 읽기/검색 허용
- Notion 생성 허용
- Notion 수정 비활성화
- Notion 삭제/보관 비활성화

실제 연결 절차는 `RUNBOOK.md`를 따른다.

## 메모리 파일

개인 데이터 파일은 Git에 올리지 않는다.

- `memory/profile.json` — 사용자 프로필 장기 기억
- `memory/diary_index.json` — 과거 일기 요약 인덱스

저장소에는 구조 참고용 예시만 포함한다.

- `memory/profile.example.json`
- `memory/diary_index.example.json`

`/저장`으로 저장하면 `memory/diary_index.json`에 날짜, 저장 위치, 짧은 요약이 자동으로 기록된다. 요약은 현재 모델을 추가 호출하지 않고 일기 본문 앞부분에서 만든다.
