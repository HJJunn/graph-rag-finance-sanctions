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
    def invoke(self, prompt: str):

        messages = [
            {"role": "user", "content": prompt}
        ]

        result = self.chat(messages)

        return result["message"]["content"]
    
    def __call__(self, prompt):

        result = self.chat(
            [{"role": "user", "content": prompt}]
        )

        return result["message"]["content"]