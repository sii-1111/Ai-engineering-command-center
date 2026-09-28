from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from core.retrieval.blob import AzureBlobConfig, AzureBlobRepositorySource


def test_blob_config_requires_connection_string(monkeypatch):
    monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)
    with pytest.raises(ValueError, match="AZURE_STORAGE_CONNECTION_STRING"):
        AzureBlobConfig.from_environment()


@patch("core.retrieval.blob.BlobServiceClient")
def test_blob_source_lists_supported_text_files(blob_client):
    container = Mock()
    blob_client.from_connection_string.return_value.get_container_client.return_value = container
    container.list_blobs.return_value = [
        SimpleNamespace(name="owner/repo/main/app.py", etag="etag1"),
        SimpleNamespace(name="owner/repo/main/logo.png", etag="etag2"),
    ]
    download = Mock()
    download.readall.return_value = b"print('ok')"
    container.download_blob.return_value = download

    source = AzureBlobRepositorySource(AzureBlobConfig("connection", "repositories"))
    files = source.list_files("owner/repo", "main")

    assert len(files) == 1
    assert files[0].path == "app.py"
    assert files[0].content == "print('ok')"
    assert files[0].commit_sha == "etag1"
