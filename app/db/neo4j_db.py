from neo4j import GraphDatabase
import json
import re
from pathlib import Path
from app.db.neo4j_driver import get_driver

# 그래프 DB 초기화
def clear_database(tx):
    """데이터베이스의 모든 노드와 관계를 삭제합니다"""
    tx.run("MATCH (n) DETACH DELETE n")

driver = get_driver()
with driver.session() as session:
    session.execute_write(clear_database)

# =========================
#  제약 조건 생성
# =========================

def create_constraints(tx):
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Institution) REQUIRE i.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case) REQUIRE c.case_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (v:ViolationCase) REQUIRE v.violation_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (l:Law) REQUIRE l.legal_basis IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Sanction) REQUIRE s.sanction_id IS UNIQUE"
    ]
    for c in constraints:
        tx.run(c)


# =========================
# 그래프 생성 로직
# =========================

def create_graph_nodes(tx, record):

    institution = record.get("institution", "Unknown")
    date = record.get("date", "")
    case_id = f"{institution}_{date}"

    # (A) Institution + Case
    tx.run("""
        MERGE (i:Institution {name: $institution})
        MERGE (c:Case {case_id: $case_id})
        SET c.action_date = $date
        MERGE (i)-[:INVOLVED_IN]->(c)
    """, institution=institution, case_id=case_id, date=date)


    # (B) Violation 처리
    for idx, violation in enumerate(record.get("violations", [])):
        violation_id = f"{case_id}_v_{idx}"

        tx.run("""
            MERGE (v:ViolationCase {violation_id: $v_id})
            SET v.violation_name = $v_name,
                v.content = $content,
                v.parent_title = $parent_title,
                v.sub_title = $sub_title,
                v.detail_idx = $detail_idx,
                v.date = $date
            WITH v
            MATCH (c:Case {case_id: $case_id})
            MERGE (c)-[:HAS_VIOLATION]->(v)
        """,
        v_id=violation_id,
        v_name=violation.get("violation_name", ""),
        content=violation.get("content", ""),
        parent_title=violation.get("parent_title", ""),
        sub_title=violation.get("sub_title", ""),
        detail_idx=violation.get("detail_idx", ""),
        date=date,
        case_id=case_id
        )

        # Law 연결
        legal_basis = violation.get("legal_basis", "")
        if legal_basis:
            tx.run("""
                MERGE (l:Law {legal_basis: $legal_basis})
                WITH l
                MATCH (v:ViolationCase {violation_id: $v_id})
                MERGE (v)-[:BASED_ON]->(l)
            """,
            legal_basis=legal_basis,
            v_id=violation_id
            )


    # (C) Sanction 처리
    for s_idx, sanction in enumerate(record.get("sanctions", [])):
        sanction_id = f"{case_id}_s_{s_idx}"

        tx.run("""
            MERGE (s:Sanction {sanction_id: $s_id})
            SET s.target = $target,
                s.content = $content
            WITH s
            MATCH (c:Case {case_id: $case_id})
            MERGE (c)-[:RESULTED_IN]->(s)
            WITH s
            MATCH (i:Institution {name: $institution})
            MERGE (i)-[:RECEIVED]->(s)
        """,
        s_id=sanction_id,
        target=sanction.get("target", ""),
        content=sanction.get("content", ""),
        case_id=case_id,
        institution=institution
        )


# =========================
#  JSON 로딩 후 실행
# =========================

JSON_PATH = "refined_fss_sanctions_data.json"   # 네가 저장한 파일

with open(JSON_PATH, "r", encoding="utf-8") as f:
    json_data = json.load(f)

with driver.session() as session:
    print("제약조건 설정 중...")
    session.execute_write(create_constraints)

    print("데이터 적재 시작...")
    for idx, record in enumerate(json_data):
        try:
            session.execute_write(create_graph_nodes, record)
            if (idx + 1) % 5 == 0:
                print(f"{idx+1}/{len(json_data)} 완료")
        except Exception as e:
            print(f"{record.get('institution')} 처리 중 오류:", e)

driver.close()
print("Graph 구축 완료 🚀")