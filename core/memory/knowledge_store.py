"""PostgreSQL adapter for durable engineering knowledge."""

import json
from typing import Any

from core.memory.knowledge import EngineeringKnowledge, KnowledgeStore

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS engineering_knowledge (
    knowledge_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    repository TEXT NOT NULL,
    ref TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    fix TEXT NOT NULL,
    files JSONB NOT NULL,
    verification TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    pull_request TEXT NOT NULL,
    tags JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
)
"""


class PostgresKnowledgeStore(KnowledgeStore):
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        import psycopg

        return psycopg.connect(self.database_url)

    def setup(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(CREATE_TABLE)

    def save(self, knowledge: EngineeringKnowledge) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO engineering_knowledge
                (knowledge_id, task_id, repository, ref, root_cause, fix, files,
                 verification, confidence, pull_request, tags, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (knowledge_id) DO NOTHING""",
                (
                    knowledge.knowledge_id,
                    knowledge.task_id,
                    knowledge.repository,
                    knowledge.ref,
                    knowledge.root_cause,
                    knowledge.fix,
                    json.dumps(list(knowledge.files)),
                    knowledge.verification,
                    knowledge.confidence,
                    knowledge.pull_request,
                    json.dumps(list(knowledge.tags)),
                    knowledge.created_at,
                ),
            )

    def search(
        self, query: str, repository: str | None = None, top_k: int = 5
    ) -> list[EngineeringKnowledge]:
        clauses = [
            (
                "to_tsvector('simple', root_cause || ' ' || fix || ' ' || "
                "coalesce(array_to_string(ARRAY(SELECT jsonb_array_elements_text(tags)), ' '), '')) "
                "@@ plainto_tsquery('simple', %s)"
            )
        ]
        params: list[Any] = [query]
        if repository:
            clauses.append("repository = %s")
            params.append(repository)
        params.append(top_k)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""SELECT knowledge_id, task_id, repository, ref, root_cause, fix,
                    files, verification, confidence, pull_request, tags, created_at
                    FROM engineering_knowledge WHERE {' AND '.join(clauses)}
                    ORDER BY confidence DESC, created_at DESC LIMIT %s""",
                params,
            )
            return [_row_to_knowledge(row) for row in cur.fetchall()]


def _row_to_knowledge(row: tuple[Any, ...]) -> EngineeringKnowledge:
    return EngineeringKnowledge(
        knowledge_id=row[0],
        task_id=row[1],
        repository=row[2],
        ref=row[3],
        root_cause=row[4],
        fix=row[5],
        files=tuple(row[6] or []),
        verification=row[7],
        confidence=float(row[8]),
        pull_request=row[9],
        tags=tuple(row[10] or []),
        created_at=row[11].isoformat(),
    )
