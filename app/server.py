from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict

from app.db.neo4j_driver import get_driver
from app.llm.openai_llm import OpenAIChatLLM
from app.memory.conversation_memory import ConversationMemory
from app.query.query_rewriter import QueryRewriter
from app.retrievers.build_retrievers import build_retrievers
from app.services.rag_pipeline import RAGPipeline


# --------------------------------------------------
# FastAPI 생성
# --------------------------------------------------

app = FastAPI()

# --------------------------------------------------
# 전역 객체 생성
# --------------------------------------------------

driver = get_driver()
router_llm = OpenAIChatLLM()
retriever = build_retrievers(driver, router_llm)
rewriter = QueryRewriter(router_llm)
pipeline = RAGPipeline(retriever, rewriter)
memory_store: Dict[str, ConversationMemory] = {}


# --------------------------------------------------
# Memory helper
# --------------------------------------------------

def get_memory(user_id: str) -> ConversationMemory:

    if user_id not in memory_store:
        memory_store[user_id] = ConversationMemory(max_turns=6)

    return memory_store[user_id]


# --------------------------------------------------
# Request / Response Schema
# --------------------------------------------------

class QueryRequest(BaseModel):

    user_id: str
    question: str


class QueryResponse(BaseModel):

    answer: str
    rewritten_question: str
    normalized_question: str = ""
    used_nodes: list[str]
    used_edges: list[str]
    retriever_used: str


# --------------------------------------------------
# Query API
# --------------------------------------------------
@app.post("/query", response_model=QueryResponse)
def query_graph(req: QueryRequest):
    try:
        memory = get_memory(req.user_id)

        result = pipeline.run(
            question=req.question,
            user_id=req.user_id,
            memory=memory
        )

        print("PIPELINE RESULT:", result)
        print("RESULT TYPE:", type(result))

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()

        return {
            "answer": f"서버 내부 오류: {repr(e)}",
            "rewritten_question": "",
            "used_nodes": [],
            "used_edges": [],
            "retriever_used": "error"
        }


# --------------------------------------------------
# Graph visualization API
# --------------------------------------------------

@app.get("/graph")
def get_graph():

    with driver.session() as session:

        nodes = []
        edges = []

        node_result = session.run("""
        MATCH (n)
        RETURN elementId(n) as id, labels(n)[0] as label, n
        LIMIT 500
        """)

        for r in node_result:

            node_obj = dict(r["n"])

            title = (
                node_obj.get("name")
                or node_obj.get("title")
                or node_obj.get("violation_name")
                or node_obj.get("legal_basis")
                or str(r["n"])
            )

            nodes.append({
                "id": r["id"],
                "label": r["label"],
                "title": title,
                "properties": node_obj
            })


        edge_result = session.run("""
        MATCH (a)-[r]->(b)
        RETURN elementId(r) as id,
            elementId(a) as source,
            elementId(b) as target,
            type(r) as relationship
        LIMIT 1000
        """)

        for r in edge_result:

            edges.append({
            "id": r["id"],
            "source": r["source"],
            "target": r["target"],
            "relationship": r["relationship"]
        })

    return {"nodes": nodes, "edges": edges}


# --------------------------------------------------
# frontend 정적 파일
# --------------------------------------------------

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")