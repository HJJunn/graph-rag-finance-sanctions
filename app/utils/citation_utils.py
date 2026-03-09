from typing import List
import re


def extract_refs(answer: str) -> List[int]:
    """
    답변에서 [[ref1]], [[ref2]] 형태의 citation 번호 추출
    """

    pattern = r"\[\[ref(\d+)\]\]"
    refs = re.findall(pattern, answer)

    return sorted(set(int(r) for r in refs))


def build_search_results(items: list, top_k: int = 5) -> str:
    """
    파인튜닝 모델이 학습한 RAG 형식으로 검색 결과를 문서 형태로 구성
    """

    docs = []

    for idx, item in enumerate(items[:top_k], start=1):

        meta = item.metadata if item.metadata else {}

        institution = meta.get("institution", "")
        action_date = meta.get("action_date", "")
        violation_name = meta.get("violation_name", "")
        legal_bases = meta.get("legal_bases", [])
        sanctions = meta.get("sanctions", [])

        if legal_bases is None:
            legal_bases = []

        if sanctions is None:
            sanctions = []

        sanctions_text = "; ".join(
            f"{s.get('target','')}: {s.get('content','')}"
            for s in sanctions if isinstance(s, dict)
        )

        doc = f"""
[{idx}]
기관명: {institution}
조치일: {action_date}
위반내용: {violation_name}
법규: {", ".join(legal_bases)}
제재: {sanctions_text}

본문:
{str(item.content)}
""".strip()

        docs.append(doc)

    return "\n\n".join(docs)


def map_refs_to_nodes(items: list, refs: List[int]) -> List[str]:
    """
    [[ref1]], [[ref2]] → retriever item → Neo4j node id 매핑
    """

    used_nodes = []

    for ref_num in refs:

        idx = ref_num - 1

        if 0 <= idx < len(items):

            meta = items[idx].metadata if items[idx].metadata else {}

            node_id = meta.get("id") or meta.get("violation_id")

            if node_id:
                used_nodes.append(node_id)

    return sorted(set(used_nodes))