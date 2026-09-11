from fastapi.testclient import TestClient
import app
from app import Q
client = TestClient(app.app)


def test_valid_question(monkeypatch):
    monkeypatch.setattr(
        app,
        "answer_question",
        lambda question: "คำตอบทดสอบ",
    )

    response = client.post(
        "/ask",
        json={"question": "สยามประกาศสงครามเมื่อใด"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "คำตอบทดสอบ"
    }


def test_empty_question_is_rejected():
    response = client.post(
        "/ask",
        json={"question": ""},
    )

    assert response.status_code == 422


def test_whitespace_question_is_rejected():
    response = client.post(
        "/ask",
        json={"question": "     "},
    )

    assert response.status_code == 422


def test_long_question_is_rejected():
    response = client.post(
        "/ask",
        json={"question": "ก" * 501},
    )

    assert response.status_code == 422

def test_question_is_trimmed():
    request = Q(
        question="   สยามประกาศสงครามเมื่อใด   "
    )

    assert request.question == "สยามประกาศสงครามเมื่อใด"