from types import SimpleNamespace

from core.mcp_client import _extract_tool_result


def test_extracts_text_content() -> None:
    result = SimpleNamespace(content=[SimpleNamespace(text='{"path":"README.md"}')])
    assert _extract_tool_result(result) == '{"path":"README.md"}'


def test_extracts_structured_content_when_text_is_missing() -> None:
    result = SimpleNamespace(
        content=[],
        structuredContent={"path": "README.md", "content": "hello"},
    )
    assert _extract_tool_result(result) == '{"path": "README.md", "content": "hello"}'


def test_extracts_model_dump_as_last_resort() -> None:
    class Result:
        content = []

        def model_dump(self):
            return {"content": [{"type": "text", "text": "repository evidence"}]}

    assert "repository evidence" in _extract_tool_result(Result())
