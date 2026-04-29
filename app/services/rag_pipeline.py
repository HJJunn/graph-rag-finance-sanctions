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
        try:
            print("\nSTEP 0: pipeline start")

            # 1. 대화 히스토리
            history = memory.build_history_text()
            print("STEP 1: history loaded")

            # 2. Query Rewrite
            standalone = self.rewriter.rewrite(history, question)
            print("STEP 2: rewrite done:", standalone)

            # 3. 표기 정규화
            normalized_standalone = normalize_entity_text(standalone)
            print("STEP 3: normalize done:", normalized_standalone)

            # 4. Retriever 실행
            print("STEP 4: before retrieval")
            result = self.retriever.search(query_text=normalized_standalone)
            print("STEP 5: after retrieval")

            items = normalize_items(result)

            print("\n========== RETRIEVAL DEBUG ==========")
            print("Query:", normalized_standalone)
            print("Retriever:", type(result).__name__)
            print("Docs:", len(items))
            print("=====================================\n")

            if len(items) == 0:
                answer = "검색 결과에는 해당 질문에 대한 내용이 없습니다."
                memory.add_turn(question, answer)

                return {
                    "answer": answer,
                    "rewritten_question": standalone,
                    "normalized_question": normalized_standalone,
                    "used_nodes": [],
                    "used_edges": [],
                    "retriever_used": type(self.retriever).__name__,
                }

            # 5. 그래프 ID 추출
            print("STEP 6: before extract_graph_ids")
            retrieved_nodes, retrieved_edges = extract_graph_ids(items)
            print("STEP 7: after extract_graph_ids")
            print("retrieved_nodes:", retrieved_nodes)
            print("retrieved_edges:", retrieved_edges)

            # 6. Search Results 생성
            print("STEP 8: before build_search_results")
            context = build_search_results(items, top_k=5)
            print("STEP 9: after build_search_results")
            print("CONTEXT PREVIEW:", context[:500])

            # 7. 프롬프트 구성
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
{normalized_standalone}

Search Results:
{context}
""".strip()
                }
            ]

            # 8. 답변 생성
            print("STEP 10: before LLM")
            answer = self.generate_answer(messages)
            print("STEP 11: after LLM")
            print("ANSWER:", answer[:500])

            if not answer.strip():
                answer = "검색 결과를 기반으로 답변을 생성하지 못했습니다."

            # 9. citation 파싱
            refs = extract_refs(answer)
            citation_nodes = map_refs_to_nodes(items, refs)

            # 10. citation 기반 노드 + retrieval 기반 노드 합치기
            used_nodes = sorted(set(citation_nodes + retrieved_nodes))
            used_edges = retrieved_edges

            print("STEP 12: final used_nodes:", used_nodes)
            print("STEP 13: final used_edges:", used_edges)

            # 11. memory 저장
            memory.add_turn(question, answer)

            return {
                "answer": answer,
                "rewritten_question": standalone,
                "normalized_question": normalized_standalone,
                "used_nodes": used_nodes,
                "used_edges": used_edges,
                "retriever_used": type(self.retriever).__name__,
            }

        except Exception as e:
            import traceback
            traceback.print_exc()

            return {
                "answer": f"서버 내부 오류: {repr(e)}",
                "rewritten_question": "",
                "normalized_question": "",
                "used_nodes": [],
                "used_edges": [],
                "retriever_used": "error",
            }