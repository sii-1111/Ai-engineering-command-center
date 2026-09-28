from core.retrieval.azure_index import AzureSearchIndexer
from core.retrieval.embedding import AzureOpenAIEmbeddingProvider


class FakeEmbeddings:
    def create(self, *, model, input):
        class Item:
            def __init__(self, embedding):
                self.embedding = embedding

        class Response:
            def __init__(self, data):
                self.data = data

        data = [Item([float(i), float(i + 1)]) for i, _ in enumerate(input)]
        return Response(data)


class FakeClient:
    embeddings = FakeEmbeddings()


def test_azure_openai_embedding_provider_maps_response():
    provider = AzureOpenAIEmbeddingProvider(FakeClient(), "embeddings")
    assert provider.embed(["one", "two"]) == [[0.0, 1.0], [1.0, 2.0]]
    assert provider.embed([]) == []


def test_azure_search_indexer_uploads_documents():
    class Search:
        def merge_or_upload_documents(self, *, documents):
            return [{"key": item["id"], "succeeded": True} for item in documents]

    indexer = AzureSearchIndexer(Search())
    assert indexer.upsert([{"id": "1"}, {"id": "2"}]) == 2
    assert indexer.upsert([]) == 0
