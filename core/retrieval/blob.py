"""Azure Blob Storage source for repository text ingestion."""

import os
from dataclasses import dataclass

from azure.storage.blob import BlobServiceClient

from core.retrieval.ingestion import RepositoryFile

_SUPPORTED_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".md", ".txt")


@dataclass(frozen=True)
class AzureBlobConfig:
    connection_string: str
    container: str = "repositories"

    @classmethod
    def from_environment(cls) -> "AzureBlobConfig":
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
        container = os.getenv("AZURE_STORAGE_CONTAINER", "repositories")
        if not connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING is required")
        return cls(connection_string, container)


class AzureBlobRepositorySource:
    """Read repository files stored as blobs under repository/ref prefixes."""

    def __init__(self, config: AzureBlobConfig) -> None:
        self.client = BlobServiceClient.from_connection_string(config.connection_string)
        self.container = config.container

    def list_files(self, repository: str, ref: str) -> list[RepositoryFile]:
        prefix = f"{repository}/{ref}/"
        container = self.client.get_container_client(self.container)
        files: list[RepositoryFile] = []
        for blob in container.list_blobs(name_starts_with=prefix):
            if not blob.name.endswith(_SUPPORTED_SUFFIXES):
                continue
            content = container.download_blob(blob.name).readall().decode("utf-8")
            path = blob.name.removeprefix(prefix)
            files.append(RepositoryFile(path, content, str(blob.etag or ""), repository, ref))
        return files
