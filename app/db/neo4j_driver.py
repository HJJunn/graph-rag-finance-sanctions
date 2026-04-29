import logging
import time
from neo4j import GraphDatabase, basic_auth
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

def get_driver():
    """
    neo4j-graphrag Retriever들이 요구하는 공식 Neo4j Driver 객체 반환
    """
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )


def execute_read(cypher: str, params: dict = None):
    """
    디버깅용 직접 Cypher 실행 함수.
    Retriever에 넘기는 driver와는 별도로 사용.
    """
    params = params or {}

    logger.debug("Executing Cypher:\n%s\nparams=%s", cypher, params)

    start = time.time()

    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run(cypher, **params)
            records = [record.data() for record in result]
    finally:
        driver.close()

    elapsed = time.time() - start
    logger.debug("Cypher finished in %.3fs | rows=%d", elapsed, len(records))

    return records