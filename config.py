from typing import Literal
class Settings:
    retriever : Literal["bm25", "vector", "hybrid"] = "bm25"
    generator: Literal["typhoon", "openai"] = "typhoon"

    n_results: int = 10
    rrf_k: int = 10
    bm25_weight: float = 3.0

    embedding_model: str = "text-embedding-3-small"

settings = Settings()