"""키레네 로컬 일기 에이전트.

사용법:
    ollama serve
    ollama pull gemma3:4b
    python main.py

명령어:
    /일기   지금까지의 대화로 일기를 생성하고 저장
    /기억   저장된 장기 기억과 일기 인덱스 확인
    /이름   사용자 이름 저장
    /기억추가   장기 기억 메모 추가
    /선호추가   선호하는 응답 방식 추가
    /회피추가   피해야 할 응답 방식 추가
    /종료   저장 없이 종료
"""

from hermes import HermesAgent, LocalLLMClient, LocalLLMError
from hermes.config import load_settings
from hermes.memory import DiaryIndexMemory, ProfileMemory
from persona import GREETING
from storage import LocalMarkdownStorage

PINK = "\033[95m"
DIM = "\033[2m"
RESET = "\033[0m"


def cyrene_says(text: str) -> None:
    print(f"\n{PINK}키레네{RESET} {text}\n")


def write_diary(agent: HermesAgent) -> None:
    if not agent.can_write_diary():
        cyrene_says("아직 아무 얘기도 못 들었는걸? 오늘 있었던 일부터 들려줘♪")
        return
    print(f"{DIM}(키레네가 일기를 쓰는 중…){RESET}")
    entry, location = agent.write_diary()
    print("\n" + "=" * 50)
    print(entry)
    print("=" * 50)
    cyrene_says(f"오늘의 기억, 여기 남겨뒀어 → {location}\n또 만나자, 약속이다? 잊어버리면 안 돼♪")


def handle_memory_command(agent: HermesAgent, user_input: str) -> bool:
    commands = {
        "/이름 ": agent.set_user_name,
        "/name ": agent.set_user_name,
        "/기억추가 ": agent.remember_note,
        "/remember ": agent.remember_note,
        "/선호추가 ": agent.remember_preference,
        "/prefer ": agent.remember_preference,
        "/회피추가 ": agent.remember_avoidance,
        "/avoid ": agent.remember_avoidance,
    }
    for prefix, action in commands.items():
        if user_input.startswith(prefix):
            value = user_input[len(prefix) :].strip()
            if not value:
                print(f"{DIM}저장할 내용을 함께 입력해주세요.{RESET}")
                return True
            action(value)
            print(f"{DIM}기억에 저장했습니다.{RESET}")
            return True
    return False


def main() -> None:
    settings = load_settings()
    llm = LocalLLMClient(
        model=settings.model,
        url=settings.llm_url,
        max_tokens=settings.max_tokens,
    )
    agent = HermesAgent(
        llm=llm,
        storage=LocalMarkdownStorage(),
        profile_memory=ProfileMemory(f"{settings.memory_dir}/profile.json"),
        diary_index=DiaryIndexMemory(f"{settings.memory_dir}/diary_index.json"),
    )

    cyrene_says(GREETING)

    while True:
        try:
            user_input = input("나 > ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not user_input:
            continue
        if user_input in ("/종료", "/exit", "/quit"):
            cyrene_says("이 몸은 작별을 좋아하지 않아. 차라리… 여운을 남기는 건 어떨까?")
            break
        if user_input in ("/기억", "/memory"):
            print("\n" + agent.memory_report() + "\n")
            continue
        if handle_memory_command(agent, user_input):
            continue
        if user_input in ("/일기", "/diary"):
            try:
                write_diary(agent)
            except LocalLLMError as e:
                print(f"{DIM}{e}{RESET}")
            break

        try:
            reply = agent.respond(user_input)
        except LocalLLMError as e:
            print(f"{DIM}{e}{RESET}")
            continue
        cyrene_says(reply)


if __name__ == "__main__":
    main()
