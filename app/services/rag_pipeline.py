from openai import OpenAI
import os
import re
import unicodedata

from app.utils.citation_utils import (
    extract_refs,
    build_search_results,
    map_refs_to_nodes,
    extract_graph_ids,
    normalize_items,
)


def normalize_entity_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)

    text = re.sub(r"㈜", "", text)
    text = re.sub(r"\(주\)", "", text)
    text = re.sub(r"주식회사", "", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


VLLM_BASE_URL = os.getenv("VLLM_BASE_URL")
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME")


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
            temperature=0,
            max_tokens=512
        )

        return response.choices[0].message.content or ""

    def run(self, question, user_id, memory):

        print("STEP 0: pipeline start")

        # 1️⃣ history
        history = memory.build_history_text()
        print("STEP 1: history loaded")

        # 2️⃣ rewrite
        standalone = self.rewriter.rewrite(history, question)
        print("STEP 2: rewrite done:", standalone)

        # 3️⃣ normalize
        normalized = normalize_entity_text(standalone)
        print("STEP 3: normalize done:", normalized)

        # 4️⃣ retrieval
        print("STEP 4: before retrieval")
        result = self.retriever.search(query_text=normalized)
        print("STEP 5: after retrieval")

        items = []

        if hasattr(result, "items"):
            items = result.items
        elif hasattr(result, "records"):
            items = result.records

        print("\n========== RETRIEVAL DEBUG ==========")
        print("Query:", standalone)
        print("Retriever:", type(result).__name__)
        print("Docs:", len(items))
        print("=====================================\n")

        if len(items) == 0:
            return {
                "answer": "검색 결과가 없습니다.",
                "used_nodes": [],
                "used_edges": [],
                "retriever_used": type(self.retriever).__name__
            }

        # 5️⃣ context 생성
        print("STEP 6: build context")
        context = build_search_results(items, top_k=5)

        # 6️⃣ LLM
        print("STEP 7: before LLM")
        answer = self.generate_answer([
            {"role": "system", "content": "검색 기반 답변"},
            {"role": "user", "content": f"Q:{normalized}\n\n{context}"}
        ])
        print("STEP 8: after LLM")

        # 7️⃣ ref → node 매핑
        refs = extract_refs(answer)
        used_nodes = map_refs_to_nodes(items, refs)

        print("STEP 9: used_nodes:", used_nodes)

        # 8️⃣ memory
        memory.add_turn(question, answer)

        return {
            "answer": answer,
            "rewritten_question": standalone,
            "normalized_question": normalized,
            "used_nodes": used_nodes,
            "used_edges": [],
            "retriever_used": type(self.retriever).__name__
        }