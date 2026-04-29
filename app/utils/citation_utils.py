import re


def extract_refs(answer: str) -> list[int]:
    pattern = r"\[\[ref(\d+)\]\]"
    refs = re.findall(pattern, answer or "")
    return sorted(set(int(x) for x in refs))


def _record_to_dict(value):
    try:
        if hasattr(value, "data"):
            return value.data()
    except Exception:
        pass
    return None


def _get_item_metadata(item):

    # tuple 대응
    if isinstance(item, tuple):
        item = item[0]

    # dict 대응
    if isinstance(item, dict):
        return item.get("metadata", {}) or item

    # 일반 object
    metadata = getattr(item, "metadata", None)
    content = getattr(item, "content", None)

    if isinstance(metadata, dict) and metadata:
        return metadata

    # Neo4j Record 대응
    record_dict = _record_to_dict(content)
    if record_dict:
        return record_dict

    return {}


def _get_item_content(item):

    if isinstance(item, tuple):
        item = item[0]

    if isinstance(item, dict):
        return item.get("content", "")

    content = getattr(item, "content", "")

    record_dict = _record_to_dict(content)
    if record_dict:
        return record_dict.get("content") or str(record_dict)

    return str(content or "")

def normalize_items(result):
    """
    RetrieverResult, list, tuple 등 다양한 결과를 items 리스트로 통일.
    """
    if result is None:
        return []

    if hasattr(result, "items"):
        return result.items or []

    if hasattr(result, "records"):
        return result.records or []

    if isinstance(result, list):
        return result

    if isinstance(result, tuple):
        return list(result)

    return []


def extract_graph_ids(result_or_items):
    """
    검색 결과에서 그래프 하이라이트용 node id, edge id 추출.
    """
    items = normalize_items(result_or_items)

    node_ids = []
    edge_ids = []

    for item in items:
        metadata = _get_item_metadata(item)

        if not isinstance(metadata, dict):
            continue

        node_id = (
            metadata.get("id")
            or metadata.get("node_id")
            or metadata.get("element_id")
            or metadata.get("violation_node_id")
            or metadata.get("case_node_id")
            or metadata.get("institution_node_id")
            or metadata.get("law_node_id")
            or metadata.get("sanction_node_id")
        )

        if node_id:
            node_ids.append(str(node_id))

        edge_id = (
            metadata.get("edge_id")
            or metadata.get("relationship_id")
            or metadata.get("relationship")
        )

        if edge_id:
            edge_ids.append(str(edge_id))

    return sorted(set(node_ids)), sorted(set(edge_ids))


def build_search_results(items: list, top_k: int = 5) -> str:
    docs = []

    for idx, item in enumerate(items[:top_k], start=1):
        meta = _get_item_metadata(item)
        content = _get_item_content(item)

        institution = meta.get("institution", "")
        action_date = meta.get("action_date", "")
        violation_name = meta.get("violation_name", "")

        legal_bases = (
            meta.get("legal_bases")
            or meta.get("legal_basis")
            or []
        )

        sanctions = meta.get("sanctions", [])

        if legal_bases is None:
            legal_bases = []

        if isinstance(legal_bases, str):
            legal_bases_text = legal_bases
        elif isinstance(legal_bases, list):
            legal_bases_text = ", ".join(str(x) for x in legal_bases if x)
        else:
            legal_bases_text = str(legal_bases)

        if sanctions is None:
            sanctions = []

        sanctions_text = ""

        if isinstance(sanctions, list):
            sanctions_text = "; ".join(
                f"{s.get('target', '')}: {s.get('content', '')}"
                for s in sanctions
                if isinstance(s, dict)
            )
        else:
            sanctions_text = str(sanctions)

        doc = f"""
[{idx}]
기관명: {institution}
조치일: {action_date}
위반내용: {violation_name}
법규: {legal_bases_text}
제재: {sanctions_text}

본문:
{content}
""".strip()

        docs.append(doc)

    return "\n\n".join(docs)


def map_refs_to_nodes(items, refs):

    used_nodes = []

    for ref in refs:
        idx = ref - 1

        if 0 <= idx < len(items):

            meta = _get_item_metadata(items[idx])

            node_id = (
                meta.get("id")  # ⭐ 핵심
                or meta.get("node_id")
                or meta.get("element_id")
                or meta.get("violation_id")
            )

            if node_id:
                used_nodes.append(node_id)

    return list(set(used_nodes))