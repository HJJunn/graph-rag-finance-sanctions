from neo4j import GraphDatabase
from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings

from app.config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD
)


def build_violation_embeddings():

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    embedder = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    with driver.session() as session:

        result = session.run("""
            MATCH (v:ViolationCase)
            WHERE v.embedding IS NULL
            AND v.content IS NOT NULL

            RETURN elementId(v) AS id,
                   v.violation_name AS title,
                   v.parent_title AS parent_title,
                   v.sub_title AS sub_title,
                   v.content AS content
        """)

        records = result.data()

        print(f"총 {len(records)}개 임베딩 생성 시작")

        for idx, r in enumerate(records):

            node_id = r["id"]

            text = "\n".join([
                f"[위반명] {r.get('title','')}",
                f"[대분류] {r.get('parent_title','')}",
                f"[중분류] {r.get('sub_title','')}",
                f"[본문] {r.get('content','')}"
            ]).strip()

            vector = embedder.embed_query(text)

            session.run("""
                MATCH (v:ViolationCase)
                WHERE elementId(v) = $id
                SET v.embedding = $embedding
            """, {
                "id": node_id,
                "embedding": vector
            })

            if (idx + 1) % 10 == 0:
                print(f"{idx+1}/{len(records)} 완료")

    print("임베딩 생성 완료 🚀")