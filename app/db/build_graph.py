import json
from pathlib import Path

from app.db.neo4j_driver import get_driver
from app.db.neo4j_db import (
    clear_database,
    create_constraints,
    create_graph_nodes
)

from app.retrievers.build_embeddings import build_violation_embeddings


JSON_PATH = "refined_fss_sanctions_data.json"


def build_graph():

    driver = get_driver()

    # -----------------------------
    # DB 초기화
    # -----------------------------
    with driver.session() as session:

        print("DB 초기화 중...")
        session.execute_write(clear_database)


    # -----------------------------
    # JSON 로드
    # -----------------------------
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        json_data = json.load(f)


    # -----------------------------
    # 제약조건 생성
    # -----------------------------
    with driver.session() as session:

        print("제약조건 생성 중...")
        session.execute_write(create_constraints)


    # -----------------------------
    # 그래프 생성
    # -----------------------------
    with driver.session() as session:

        print("그래프 생성 시작...")

        for idx, record in enumerate(json_data):

            try:

                session.execute_write(create_graph_nodes, record)

                if (idx + 1) % 10 == 0:
                    print(f"{idx+1}/{len(json_data)} 완료")

            except Exception as e:

                print(f"{record.get('institution')} 처리 중 오류:", e)


    print("그래프 생성 완료")


    # -----------------------------
    # 임베딩 생성
    # -----------------------------
    print("ViolationCase 임베딩 생성 시작...")
    build_violation_embeddings()


    print("Graph + Embedding 구축 완료 🚀")

    driver.close()


if __name__ == "__main__":
    build_graph()