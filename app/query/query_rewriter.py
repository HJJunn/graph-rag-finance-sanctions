class QueryRewriter:

    def __init__(self, llm):
        self.llm = llm

    def rewrite(self, history, question):

        prompt = f"""
다음 대화를 참고하여 사용자의 질문을 **독립적인 질문으로 다시 작성하세요.**

주의:
- 질문만 작성
- 답변하지 마세요
대화 맥락:
{history}

사용자 질문:
{question}

독립적인 질문:
"""

        messages = [
            {"role": "user", "content": prompt}
        ]

        return self.llm.generate(messages)
    
