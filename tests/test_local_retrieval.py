from pathlib import Path

from core.retrieval.local_search import LocalRepositoryRetriever, LocalSearchConfig
from core.retrieval.local_source import LocalRepositorySource, LocalRepositorySourceConfig


def test_local_search_filters_repository_and_ref(tmp_path: Path) -> None:
    index = tmp_path / "index.jsonl"
    index.write_text(
        '{"source":"a.py","content":"search latency optimization","repository":"owner/repo","ref":"main"}
'
        '{"source":"b.py","content":"search latency","repository":"other/repo","ref":"main"}
',
        encoding="utf-8",
    )
    results = LocalRepositoryRetriever(LocalSearchConfig(str(index))).search(
        "search latency", repository="owner/repo", ref="main"
    )
    assert [item.source for item in results] == ["a.py"]


def test_local_source_reads_supported_files(tmp_path: Path) -> None:
    root = tmp_path / "repos" / "owner" / "repo" / "main"
    root.mkdir(parents=True)
    (root / "app.py").write_text("print('hello')", encoding="utf-8")
    (root / "notes.bin").write_bytes(b"ignored")

    files = LocalRepositorySource(LocalRepositorySourceConfig(str(tmp_path / "repos"))).list_files(
        "owner/repo", "main"
    )
    assert [item.path for item in files] == ["app.py"]
