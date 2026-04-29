from neo4j import GraphDatabase


# -----------------------------
# DB 초기화
# -----------------------------
def clear_database(tx):
    """데이터베이스의 모든 노드와 관계 삭제"""
    tx.run("MATCH (n) DETACH DELETE n")


# -----------------------------
# 제약조건 생성
# -----------------------------
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


# -----------------------------
# 그래프 생성
# -----------------------------
def create_graph_nodes(tx, record):

    institution = record.get("institution", "Unknown")
    date = record.get("date", "")

    case_id = f"{institution}_{date}"

    # -----------------------------
    # Institution + Case
    # -----------------------------
    tx.run("""
        MERGE (i:Institution {name: $institution})
        MERGE (c:Case {case_id: $case_id})
        SET c.action_date = $date
        MERGE (i)-[:INVOLVED_IN]->(c)
    """,
    institution=institution,
    case_id=case_id,
    date=date
    )


    # -----------------------------
    # Violation 처리
    # -----------------------------
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


        # -----------------------------
        # Law 연결
        # -----------------------------
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


    # -----------------------------
    # Sanction 처리
    # -----------------------------
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