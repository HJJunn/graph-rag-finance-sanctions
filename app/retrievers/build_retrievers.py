from neo4j_graphrag.retrievers import (
    VectorRetriever,
    VectorCypherRetriever,
    Text2CypherRetriever,
    ToolsRetriever
)

from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j_graphrag.indexes import create_vector_index
import logging
import json
import ast
logger = logging.getLogger(__name__)


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
        elementId(v) AS id,
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
        USER INPUT: 한국투자증권㈜의 제재 내역을 알려줘
        CYPHER QUERY:
        MATCH (i:Institution)
        WHERE i.name CONTAINS "한국투자증권"
        MATCH (i)-[:INVOLVED_IN]->(c:Case)
        OPTIONAL MATCH (c)-[:HAS_VIOLATION]->(v:ViolationCase)
        OPTIONAL MATCH (v)-[:BASED_ON]->(l:Law)
        OPTIONAL MATCH (c)-[:RESULTED_IN]->(s:Sanction)
        RETURN i.name AS institution,
            c.case_id AS case_id,
            c.action_date AS action_date,
            collect(DISTINCT v.violation_name) AS violations,
            collect(DISTINCT l.legal_basis) AS legal_bases,
            collect(DISTINCT {target:s.target, content:s.content}) AS sanctions
        ORDER BY c.action_date DESC
        LIMIT 10
        """,

        """
        USER INPUT: 한국투자증권㈜과 연결된 노드를 보여줘
        CYPHER QUERY:
        MATCH (i:Institution)
        WHERE i.name CONTAINS "한국투자증권"
        OPTIONAL MATCH (i)-[:INVOLVED_IN]->(c:Case)
        OPTIONAL MATCH (c)-[:HAS_VIOLATION]->(v:ViolationCase)
        OPTIONAL MATCH (v)-[:BASED_ON]->(l:Law)
        OPTIONAL MATCH (c)-[:RESULTED_IN]->(s:Sanction)
        RETURN i.name AS institution,
            c.case_id AS case_id,
            c.action_date AS action_date,
            v.violation_id AS violation_id,
            v.violation_name AS violation_name,
            l.legal_basis AS legal_basis,
            s.sanction_id AS sanction_id,
            s.target AS sanction_target,
            s.content AS sanction_content
        LIMIT 30
        """,

        """
        USER INPUT: 녹취의무 위반 사례만 찾아줘
        CYPHER QUERY:
        MATCH (v:ViolationCase)
        WHERE v.violation_name CONTAINS "녹취"
        OR v.content CONTAINS "녹취"
        OPTIONAL MATCH (c:Case)-[:HAS_VIOLATION]->(v)
        OPTIONAL MATCH (i:Institution)-[:INVOLVED_IN]->(c)
        OPTIONAL MATCH (v)-[:BASED_ON]->(l:Law)
        OPTIONAL MATCH (c)-[:RESULTED_IN]->(s:Sanction)
        RETURN i.name AS institution,
            c.action_date AS action_date,
            v.violation_name AS violation_name,
            v.content AS content,
            collect(DISTINCT l.legal_basis) AS legal_bases,
            collect(DISTINCT {target:s.target, content:s.content}) AS sanctions
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
        description="그래프 구조 기반 질문, 관계 조회, 통계, 집계, 특정 기관의 연결 노드 조회에 사용합니다."
    )

    tools_retriever = ToolsRetriever(
        neo4j_driver=driver,
        top_k=10,  # 필요하면 10 대신 원하는 값으로 변경
        tools=[
            vector_tool,
            vector_cypher_tool,
            text2cypher_tool
        ]
    )

    # 빠른 개선: 의미/컨텍스트 기반 검색을 위해 vector_cypher_retriever를 기본 retriever로 반환
    return vector_cypher_retriever


logger = logging.getLogger(__name__)

class ToolsRetriever:
    def __init__(self, neo4j_driver, top_k: int = 10, llm=None, tools=None, **kwargs):
        self.driver = neo4j_driver
        self.top_k = top_k
        self.llm = llm
        self.tools = tools or []
        self._extra = kwargs

    def retrieve(self, query: str):
        logger.info("Retriever called, query=%s", query)
        cypher = """
        MATCH (n)
        WHERE toLower(coalesce(n.content, n.name, '')) CONTAINS toLower($q)
        RETURN elementId(n) AS eid, labels(n) AS labels, properties(n) AS props
        LIMIT $limit
        """
        params = {"q": query, "limit": self.top_k}
        # 호환성: 드라이버 구현에 따라 execute_read 또는 execute_query 사용
        if hasattr(self.driver, "execute_read") and callable(self.driver.execute_read):
            rows = self.driver.execute_read(cypher, params)
        elif hasattr(self.driver, "execute_query") and callable(self.driver.execute_query):
            rows = self.driver.execute_query(cypher, params)
        else:
            raise AttributeError("Driver has no execute_read or execute_query method")
        docs = []
        for r in rows:
            # normalize row into dict-like (eid, labels, props)
            if isinstance(r, dict):
                eid = r.get("eid") or r.get("nid")
                labels = r.get("labels") or []
                props = r.get("props") or {}
            elif isinstance(r, (list, tuple)):
                eid = r[0] if len(r) > 0 else None
                labels = r[1] if len(r) > 1 else []
                props = r[2] if len(r) > 2 and r[2] is not None else {}
            else:
                # fallback: try attribute access or convert to dict if possible
                try:
                    eid = getattr(r, "eid", None) or getattr(r, "nid", None) or getattr(r, "id", None)
                    labels = getattr(r, "labels", None) or []
                    props = getattr(r, "props", None) or {}
                except Exception:
                    eid, labels, props = None, [], {}

            # props가 문자열로 올 수 있으므로 JSON / Python literal로 파싱 시도
            if isinstance(props, str):
                parsed = None
                try:
                    parsed = json.loads(props)
                except Exception:
                    try:
                        parsed = ast.literal_eval(props)
                    except Exception:
                        parsed = None
                props = parsed if isinstance(parsed, dict) else {}

            # labels가 문자열로 올 경우 간단 정리
            if isinstance(labels, str):
                try:
                    labels_parsed = json.loads(labels)
                    labels = labels_parsed if isinstance(labels_parsed, (list, tuple)) else [labels]
                except Exception:
                    # 쉼표 구분 등 간단 분리 시도
                    if "," in labels:
                        labels = [s.strip() for s in labels.split(",") if s.strip()]
                    else:
                        labels = [labels]

            props = props or {}
            uid = props.get("violation_id") or props.get("sanction_id") or props.get("case_id") or props.get("name") or eid
            text = (props.get("content") or props.get("sub_title") or props.get("violation_name") or props.get("name") or "").strip()
            if text:
                safe_props = {k: v for k, v in props.items() if k != "embedding"}
                docs.append({"id": uid, "text": text, "labels": labels, "props": safe_props})
        return docs

    # 호환성용 wrapper: 기존 코드에서 .search(...) 호출을 사용하므로 동일 동작을 제공
    def search(self, query_text: str = None, top_k: int = None, **kwargs):
        q = query_text if query_text is not None else kwargs.get("query")
        if top_k is not None:
            old_top = self.top_k
            try:
                self.top_k = int(top_k)
                return self.retrieve(q)
            finally:
                self.top_k = old_top
        return self.retrieve(q)

