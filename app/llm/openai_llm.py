from openai import OpenAI


class OpenAIChatLLM:

    def __init__(self, model="gpt-4o-mini"):
        self.client = OpenAI()
        self.model = model

    def chat(self, messages):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0
        )

        return {
            "message": {
                "content": response.choices[0].message.content
            }
        }

    # ✅ messages 기반 호출 (retriever 호환)
    def generate(self, messages):
        return self.chat(messages)["message"]["content"]

    # ✅ prompt 기반 호출 (rewrite용)
    def invoke(self, prompt: str):
        messages = [{"role": "user", "content": prompt}]
        return self.generate(messages)

    # ✅ shortcut
    def __call__(self, prompt):
        return self.invoke(prompt)