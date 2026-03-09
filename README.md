# GraphRAG 기반 금융 제재 분석 AI 시스템

## 프로젝트 소개

본 프로젝트는 **금융기관 제재 데이터를 기반으로 질문에 답변하는 GraphRAG 시스템**입니다.
Neo4j 그래프 데이터베이스를 활용하여 금융 제재 정보를 구조화하고, 다양한 Retriever를 결합한 **Agentic Retrieval 구조**를 통해 사용자 질문에 맞는 검색 방식을 자동으로 선택합니다.

검색된 결과는 **파인튜닝된 한국어 LLM을 통해 최종 답변을 생성**하며, 답변에는 근거 문서에 대한 **citation(`[[ref]]`)**이 포함됩니다.

또한, 검색에 사용된 노드들을 **그래프 시각화 형태로 확인할 수 있는 인터페이스**를 제공합니다.

---

# 주요 기능

### 1. Graph 기반 RAG 검색

Neo4j 그래프 데이터베이스를 기반으로 금융 제재 데이터를 구조화합니다.

그래프 구조 예시

```
Institution
   │
   └── INVOLVED_IN
           │
           Case
           │
           └── HAS_VIOLATION
                   │
                   ViolationCase
                   │
                   └── BASED_ON
                           │
                           Law
```

이를 통해 다음과 같은 질문을 처리할 수 있습니다.

* 특정 기관의 제재 내역
* 특정 법규 위반 사례
* 기관별 위반 통계
* 법규별 위반 빈도

---

### 2. Agentic Retrieval (Tool 기반 검색)

사용자의 질문에 따라 LLM이 자동으로 검색 전략을 선택합니다.

사용되는 Retriever

| Retriever             | 역할                |
| --------------------- | ----------------- |
| VectorRetriever       | 위반 내용 기반 의미 검색    |
| VectorCypherRetriever | 의미 검색 + 그래프 관계 조회 |
| Text2CypherRetriever  | 통계 및 구조적 질의       |

예시

```
질문: 녹취 의무 위반 사례 알려줘

→ VectorCypherRetriever 선택
```

```
질문: 기관별 위반 건수 알려줘

→ Text2CypherRetriever 선택
```

---

### 3. Query Rewrite

대화형 질문을 **독립적인 질문으로 재작성**합니다.

예시

```
사용자: 한국투자증권 제재 알려줘
사용자: 가장 최근 건은?

Rewrite →

한국투자증권의 가장 최근 제재 사례는 무엇인가?
```

---

### 4. Finetuned LLM 답변 생성

검색된 결과는 **파인튜닝된 한국어 LLM**을 통해 답변을 생성합니다.

모델

```
HJUNN/qwen2-7b-rag-ko-checkpoint-813
```

답변 예시

```
한국투자증권㈜은 2022년 3월 21일 녹취의무 위반으로 제재를 받았습니다. [[ref1]]

해당 위반은 투자자 보호 규정 위반에 해당하며 관련 법규는 금융투자업 규정 제4-20조입니다. [[ref2]]
```

---

### 5. Citation 기반 답변

모든 답변에는 근거 문서가 표시됩니다.

```
[[ref1]]
[[ref2]]
```

이를 통해 **Hallucination을 최소화**합니다.

---

### 6. Graph 시각화

검색 결과에 사용된 노드를 그래프 형태로 확인할 수 있습니다.

시각화 정보

* Institution
* Case
* ViolationCase
* Law
* Sanction

프론트엔드는 **vis-network 기반 그래프 인터페이스**로 구현되어 있습니다.

---

# 시스템 아키텍처

```
User
 ↓
FastAPI API
 ↓
Query Rewrite
 ↓
ToolsRetriever
 ├ Vector Retriever
 ├ VectorCypher Retriever
 └ Text2Cypher Retriever
 ↓
Neo4j Graph Database
 ↓
Context Construction
 ↓
Finetuned LLM (vLLM)
 ↓
Citation Parsing
 ↓
Graph Visualization
```

---

# 프로젝트 구조

```
app
 ├ config.py

 ├ db
 │   ├ neo4j_driver.py
 │   ├ neo4j_db.py
 │   └ build_graph.py

 ├ llm
 │   └ openai_llm.py

 ├ retrievers
 │   └ build_retrievers.py

 ├ services
 │   └ rag_pipeline.py

 ├ utils
 │   └ citation_utils.py

 ├ memory
 │   └ conversation_memory.py

 ├ query
 │   └ query_rewriter.py

 └ server.py

frontend
 └ index.html
```

---

# 설치 방법

## 1. 저장소 클론

```
git clone <repo_url>
cd project
```

---

## 2. Python 환경 생성

```
python -m venv .venv
```

Mac / Linux

```
source .venv/bin/activate
```

Windows

```
.venv\Scripts\activate
```

---

## 3. 패키지 설치

```
pip install -r requirements.txt
```

---

# 환경 설정

프로젝트 루트에 `.env` 파일 생성

```
OPENAI_API_KEY=your_openai_key

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

VLLM_BASE_URL=http://localhost:8001/v1
```

---

# Neo4j 실행

Docker 사용 권장

```
docker run \
-p7474:7474 -p7687:7687 \
-e NEO4J_AUTH=neo4j/password \
neo4j
```

접속

```
http://localhost:7474
```

---

# 그래프 데이터 구축

JSON 데이터를 Neo4j 그래프로 변환합니다.

```
python -m app.db.build_graph
```

실행 과정

```
DB 초기화
Constraint 생성
Graph 생성
Embedding 생성
```

---

# vLLM 서버 실행

파인튜닝 모델 서빙

```
python -m vllm.entrypoints.openai.api_server \
--model HJUNN/qwen2-7b-rag-ko-checkpoint-813 \
--port 8001
```

---

# 서버 실행

```
uvicorn app.server:app --reload
```

서버 접속

```
http://localhost:8000
```

---

# 사용 예시

질문 예시

```
제재를 가장 많이 받은 기관은 어디인가?
```

```
녹취 의무 위반 사례 알려줘
```

```
한국투자증권 제재 내역 알려줘
```

---

# 디버그 로그

Retriever 동작 확인

```
========== RETRIEVAL DEBUG ==========
Query: 한국투자증권 제재 내역
Retriever: ToolResult
Docs: 5
=====================================
```

---

# 기술 스택

### Backend

* Python
* FastAPI
* Neo4j
* Neo4j GraphRAG

### AI / LLM

* Qwen2 7B Finetuned
* Transformers
* vLLM

### Retrieval

* Vector Search
* Graph Search
* Cypher Query

### Frontend

* HTML
* vis-network

---

# 향후 개선 계획

* Tool Router 모델 파인튜닝
* Multi-hop Graph Reasoning
* Retrieval reranking
* Graph path explanation
* Streaming LLM 응답

---

# 라이선스

MIT License

---

# 참고

본 프로젝트는 다음 기술들을 기반으로 합니다.

* GraphRAG
* Neo4j
* Retrieval-Augmented Generation
* Agentic Retrieval
