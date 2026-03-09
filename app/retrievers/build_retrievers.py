from neo4j_graphrag.retrievers import (
    VectorRetriever,
    VectorCypherRetriever,
    Text2CypherRetriever,
    ToolsRetriever
)

from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j_graphrag.indexes import create_vector_index


INDEX_NAME = "violation_vector_index"


def build_retrievers(driver, llm):

    embedder = OpenAIEmbeddings(model="text-embedding-3-small")

    # =========================
    # 1️⃣ Vector Index 생성 (한번만)
    # =========================

    try:
        create_vector_index(
            driver,
            INDEX_NAME,
            label="ViolationCase",
            embedding_property="embedding",
            dimensions=1536,
            similarity_fn="cosine"
        )
    except:
        pass

    # =========================
    # 2️⃣ Vector Retriever
    # =========================

    vector_retriever = VectorRetriever(
        driver=driver,
        index_name=INDEX_NAME,
        embedder=embedder
    )

    # =========================
    # 3️⃣ VectorCypher Retriever
    # =========================

    retrieval_query = """
    WITH node AS v, score

    OPTIONAL MATCH (c:Case)-[:HAS_VIOLATION]->(v)
    OPTIONAL MATCH (i:Institution)-[:INVOLVED_IN]->(c)
    OPTIONAL MATCH (v)-[:BASED_ON]->(l:Law)
    OPTIONAL MATCH (c)-[:RESULTED_IN]->(s:Sanction)

    RETURN
        v.violation_id AS violation_id,
        v.violation_name AS violation_name,
        v.parent_title AS parent_title,
        v.sub_title AS sub_title,
        v.detail_idx AS detail_idx,
        v.content AS content,
        score,

        i.name AS institution,
        c.action_date AS action_date,

        collect(DISTINCT l.legal_basis) AS legal_basis,
        collect(DISTINCT {
            sanction_id: s.sanction_id,
            target: s.target,
            content: s.content
        }) AS sanctions

    ORDER BY score DESC
    LIMIT $top_k
    """

    vector_cypher_retriever = VectorCypherRetriever(
        driver=driver,
        index_name=INDEX_NAME,
        retrieval_query=retrieval_query,
        embedder=embedder
    )

    # =========================
    # 4️⃣ Neo4j Schema 생성
    # =========================

    with driver.session() as session:

        node_info = session.run("""
        CALL db.schema.nodeTypeProperties()
        YIELD nodeType, propertyName
        RETURN nodeType, collect(propertyName) as properties
        """).data()

        patterns = session.run("""
        MATCH (n)-[r]->(m)
        RETURN DISTINCT labels(n)[0] as source, type(r) as relationship, labels(m)[0] as target
        LIMIT 30
        """).data()

    schema_text = "=== Neo4j Schema ===\n\n노드 타입:\n"

    for node in node_info:
        schema_text += f"- {node['nodeType']}: {node['properties']}\n"

    schema_text += "\n관계 패턴:\n"

    for p in patterns:
        schema_text += f"- ({p['source']})-[:{p['relationship']}]->({p['target']})\n"

    # =========================
    # 5️⃣ Text2Cypher 예시
    # =========================

    examples = [
        """
        USER INPUT: 기관별 위반 건수를 알려줘
        CYPHER QUERY:
        MATCH (i:Institution)-[:INVOLVED_IN]->(c:Case)-[:HAS_VIOLATION]->(v:ViolationCase)
        RETURN i.name AS institution, count(v) AS violation_count
        ORDER BY violation_count DESC
        LIMIT 10
        """,

        """
        USER INPUT: 특정 기관 (한국투자증권)의 제재 내역을 보여줘
        CYPHER QUERY:
        MATCH (i:Institution {name:"한국투자증권㈜"})-[:INVOLVED_IN]->(c:Case)
        OPTIONAL MATCH (c)-[:RESULTED_IN]->(s:Sanction)
        RETURN c.case_id, c.action_date,
        collect(DISTINCT {target:s.target, content:s.content}) AS sanctions
        ORDER BY c.action_date DESC
        LIMIT 10
        """,

        """
        USER INPUT: 녹취의무 위반 사례만 찾아줘
        CYPHER QUERY:
        MATCH (v:ViolationCase)
        WHERE v.violation_name CONTAINS "녹취"
        RETURN v.violation_id, v.violation_name, v.parent_title, v.sub_title
        LIMIT 10
        """,

        """
        USER INPUT: 가장 많이 등장하는 법규 TOP 10 알려줘
        CYPHER QUERY:
        MATCH (v:ViolationCase)-[:BASED_ON]->(l:Law)
        RETURN l.legal_basis AS legal_basis, count(v) AS cnt
        ORDER BY cnt DESC
        LIMIT 10
        """
    ]

    # =========================
    # 6️⃣ Text2Cypher Retriever
    # =========================

    text2cypher_retriever = Text2CypherRetriever(
        driver=driver,
        llm=llm,
        neo4j_schema=schema_text,
        examples=examples
    )

    # =========================
    # 7️⃣ Tools
    # =========================

    vector_tool = vector_retriever.convert_to_tool(
    name = "vector_retriever",
    description= "위반사건(ViolationCase) 본문/제목 기반으로 의미 검색할 때 사용합니다."
)

    vector_cypher_tool = vector_cypher_retriever.convert_to_tool(
        name="vectorcypher_retriever",
        description="벡터 검색으로 찾은 위반사건과 연결된 기관/조치일/법규/제재까지 함께 조회할 때 사용합니다."
    )

    text2cypher_tool = text2cypher_retriever.convert_to_tool(
        name="text2cypher_retriever",
        description="기관별 통계, 법규별 빈도, 특정 조건 필터링 등 구조적 질의를 할 때 사용합니다."
    )

    tools_retriever = ToolsRetriever(
        driver=driver,
        llm=llm,
        tools=[
            vector_tool,
            vector_cypher_tool,
            text2cypher_tool
        ]
    )

    return tools_retriever

