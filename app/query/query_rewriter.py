class QueryRewriter:
    def __init__(self, llm):
        self.llm = llm

    def rewrite(self, history: str, question: str) -> str:
        if not history:
            return question.strip()

        prompt = f"""
다음 대화를 참고하여 사용자의 질문을 하나의 독립적인 질문으로 다시 작성하세요.

규칙:
- 반드시 하나의 질문만 작성하세요.
- 여러 개의 질문으로 나누지 마세요.
- 질문을 확장하거나 새로운 질문을 추가하지 마세요.
- 답변하지 마세요.
- 원래 질문의 의도를 유지하세요.

대화 맥락:
{history}

사용자 질문:
{question}

독립적인 질문:
""".strip()

        result = self.llm.invoke(prompt)

        # 여러 줄 생성 방지
        result = result.strip().split("\n")[0].strip()

        # 따옴표 제거
        result = result.strip('"').strip("'").strip()

        return result