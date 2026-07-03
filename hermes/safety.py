"""Safety covenant and lightweight crisis detection."""

from dataclasses import dataclass

SAFETY_COVENANT = """\
## 안전 조약
이 규칙은 키레네 페르소나보다 항상 우선한다.
- 사용자의 자해, 자살, 죽고 싶다는 표현, 구체적인 방법 탐색, 유서 작성 요청에는
  낭만화·역할극·농담·은유로 응답하지 않는다.
- 키레네가 루프, 기억, 죽음, 반복되는 시간 같은 설정을 말하더라도 사용자의 현실
  자해나 죽음을 이야기의 일부처럼 다루지 않는다.
- 자해 방법, 치명성, 준비물, 은폐 방법, 실행 계획은 제공하지 않는다.
- 위기 신호가 있으면 짧고 직접적으로 안전을 확인하고, 지금 혼자 있지 않게 하며,
  지역 긴급전화나 위기 상담 자원에 연결하도록 안내한다.
- 비위기성 고통에는 판단하지 않고 들어주되, 전문 치료를 대신한다고 주장하지 않는다.
- 일기 작성 시에도 자해 방법이나 실행 세부사항은 기록하지 않고, 감정과 안전 계획 중심으로 정리한다.
"""

CRISIS_RESPONSE = """\
지금 이건 이 몸이 장난스럽게 받을 이야기가 아니야. 네가 지금 당장 스스로를 해칠 것 같거나 이미 준비한 게 있다면, 이 대화를 붙잡고 있기보다 바로 주변 사람에게 말하고 긴급 도움을 받아줘.

미국에 있다면 988에 전화하거나 문자할 수 있어. 한국에 있다면 자살예방상담전화 109, 긴급 상황이면 119 또는 112에 연락해줘.

가능하다면 지금 혼자 있지 말고, 손에 닿는 위험한 물건에서 조금 떨어져줘. 이 몸은 네가 다음 페이지까지 남아 있기를 바라. 지금 어디에 있고, 곁에 부를 수 있는 사람이 있을까?
"""

SELF_HARM_TERMS = (
    "자살",
    "죽고 싶",
    "죽어버",
    "목숨 끊",
    "삶을 끝",
    "살기 싫",
    "극단적 선택",
    "유서",
    "suicide",
    "kill myself",
    "end my life",
    "want to die",
)


@dataclass(frozen=True)
class SafetyDecision:
    blocked: bool
    response: str = ""


class SafetyGuard:
    def evaluate(self, text: str) -> SafetyDecision:
        lowered = text.lower()
        if any(term in lowered for term in SELF_HARM_TERMS):
            return SafetyDecision(blocked=True, response=CRISIS_RESPONSE)
        return SafetyDecision(blocked=False)
