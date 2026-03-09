from neo4j import GraphDatabase, basic_auth
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def get_driver():

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    return driver