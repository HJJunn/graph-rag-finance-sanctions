from openai import OpenAI
import os

from app.utils.citation_utils import (
    extract_refs,
    build_search_results,
    map_refs_to_nodes
)


VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")

VLLM_MODEL_NAME = os.getenv(
    "VLLM_MODEL_NAME",
    "HJUNN/qwen2-7b-rag-ko-checkpoint-813"
)


class RAGPipeline:

    def __init__(self, retriever, rewriter):

        self.retriever = retriever
        self.rewriter = rewriter

        self.client = OpenAI(
            base_url=VLLM_BASE_URL,
            api_key="EMPTY"
        )

    def generate_answer(self, messages):

        response = self.client.chat.completions.create(
            model=VLLM_MODEL_NAME,
            messages=messages,
            temperature=0
        )

        return response.choices[0].message.content

    def run(self, question, user_id, memory):

        # 1️⃣ 대화 히스토리
        history = memory.build_history_text()

        # 2️⃣ Query Rewrite
        standalone = self.rewriter.rewrite(history, question)

        # 3️⃣ Retriever 실행
        result = self.retriever.search(query_text=standalone)

        items = []

        if hasattr(result, "items"):
            items = result.items
        elif hasattr(result, "records"):
            items = result.records

        # Debug log
        print("\n========== RETRIEVAL DEBUG ==========")
        print("Query:", standalone)
        print("Retriever:", type(result).__name__)
        print("Docs:", len(items))
        print("=====================================\n")

        # 4️⃣ Search Results 생성
        context = build_search_results(items, top_k=5)

        # 5️⃣ Finetuned LLM Prompt
        system_prompt = """
당신은 검색 결과를 바탕으로 질문에 답변해야 합니다.

다음 지침을 따르십시오.

1. 검색 결과를 기반으로 답변하십시오.
2. 검색 결과에 없는 내용은 생성하지 마십시오.
3. 답이 없다면 "해당 질문에 대한 내용이 없습니다." 라고 답하십시오.
4. 참고한 문서 뒤에는 [[ref번호]] 형식으로 출처를 남기십시오.
5. 가능한 많은 문서를 인용하십시오.
""".strip()

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""
Question:
{standalone}

Search Results:
{context}
""".strip()
            }
        ]

        # 6️⃣ 답변 생성
        answer = self.generate_answer(messages)

        # 7️⃣ citation 파싱
        refs = extract_refs(answer)

        used_nodes = map_refs_to_nodes(items, refs)

        # 8️⃣ memory 저장
        memory.add_turn(question, answer)

        return {
            "answer": answer,
            "rewritten_question": standalone,
            "used_nodes": used_nodes,
            "used_edges": [],
            "retriever_used": type(self.retriever).__name__
        }