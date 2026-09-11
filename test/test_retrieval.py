from dataclasses import replace

import pytest
import main


@pytest.mark.parametrize(
    ("retriever", "expected"),
    [
        ("bm25", "bm25"),
        ("vector", "vector"),
        ("hybrid", "hybrid"),
    ],
)
def test_retrieve_selects_configured_method(monkeypatch,retriever,expected,):
    
    test_settings = replace(
        main.settings,
        retriever=retriever,
    )

    monkeypatch.setattr(
        main,
        "settings",
        test_settings,
    )

    monkeypatch.setattr(
        main,
        "query_bm25",
        lambda question, n_results: ["bm25"],
    )

    monkeypatch.setattr(
        main,
        "query_documents",
        lambda question, n_results: ["vector"],
    )

    monkeypatch.setattr(
        main,
        "query_hybrid",
        lambda question, n_results, **kwargs: ["hybrid"],
    )

    result = main.retrieve(
        question="test question",
        n_results=3,
    )

    assert result == [expected]