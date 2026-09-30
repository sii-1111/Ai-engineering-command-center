from core.retrieval.embedding import GeminiEmbeddingProvider


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


def test_gemini_embedding_provider_maps_response():
    provider = GeminiEmbeddingProvider(FakeClient(), "gemini-embedding-001")
    assert provider.embed(["one", "two"]) == [[0.0, 1.0], [1.0, 2.0]]
    assert provider.embed([]) == []
