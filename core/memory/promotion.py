"""Promote only verified and reviewer-approved engineering outcomes."""

from core.memory.knowledge import get_knowledge_store, knowledge_from_state


def promote_knowledge(state: dict) -> dict:
    knowledge = knowledge_from_state(state)
    if knowledge is None:
        return {**state, "knowledge_promoted": False}

    get_knowledge_store().save(knowledge)
    return {**state, "knowledge_promoted": True, "knowledge_id": knowledge.knowledge_id}
