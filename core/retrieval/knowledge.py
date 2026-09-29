"""Read-only retrieval of previously verified engineering knowledge."""

from core.memory.knowledge import get_knowledge_store


def search_engineering_knowledge(
    query: str, repository: str | None = None, top_k: int = 5
) -> list[dict]:
    return [
        item.as_dict()
        for item in get_knowledge_store().search(query, repository=repository, top_k=top_k)
    ]
