import io
import json
from types import SimpleNamespace

import httpx
from groq import BadRequestError, GroqError, RateLimitError
from PIL import Image, ImageDraw, ImageFont

from assistant import llm, stt, views
from assistant.tests.conftest import found


def fake_llm(monkeypatch, *answers):
    """Replaces the LLM call with fixed answers, one per chat turn."""
    replies = iter(answers)
    monkeypatch.setattr(views, "extract", lambda *args, **kwargs: next(replies))


def say(api, url, message, previous=None):
    previous = previous or {}
    return api.post(url, {"draft": previous.get("draft"), "message": message, "question": previous.get("question") or ""})


def test_assistant_needs_login(api, goa):
    assert api.post(f"{goa}/assistant", {"message": "hi"}).status_code == 401


def test_only_group_members_can_use_it(api, goa):
    token = api.post("/api/auth/signup", {"name": "Zoya", "password": "secret1"}).json()["token"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    assert api.post(f"{goa}/assistant", {"message": "hi"}).status_code == 400


def test_two_turns_then_save(api, mohit, monkeypatch):
    fake_llm(
        monkeypatch,
        found(description="Lunch", items=[{"name": "Pizza", "amount": "600"}, {"name": "Beer", "amount": "400"}],
              who_had_what=[{"item": "pizza", "people": ["Mohit", "Rahul"]}, {"item": "beer", "people": ["Ankit"]}]),
        found(payers=[{"person": "Rahul", "amount": None}]),
    )
    first = say(api, mohit, "lunch: pizza 600 me and rahul, beer 400 ankit").json()
    assert first["question"] == "Who paid?"

    second = say(api, mohit, "rahul paid", first).json()
    assert second["question"] is None
    assert [(s["name"], s["amount"]) for s in second["shares"]] == [("Mohit", "300.00"), ("Rahul", "300.00"), ("Ankit", "400.00")]

    saved = api.post("/api/groups/1/expenses", second["draft"])  # Confirm & add
    assert saved.status_code == 201


def test_problems_are_reported_not_saved(api, mohit, monkeypatch):
    fake_llm(monkeypatch, found(description="Odd bill", total="100", items=[{"name": "Tea", "amount": "300"}],
                                who_had_what=[{"item": "tea", "people": ["everyone"]}], payers=[{"person": "Mohit", "amount": None}]))
    reply = say(api, mohit, "tea 300, total 100, I paid").json()
    assert reply["errors"] == {"items": ["Item amounts must add up to the expense amount."]}


def test_scanned_receipts_never_fill_in_people(api, mohit, monkeypatch):
    fake_llm(monkeypatch, found(items=[{"name": "Tea", "amount": "50"}], total="50",
                                who_had_what=[{"item": "tea", "people": ["Mohit"]}], payers=[{"person": "Mohit", "amount": None}]))
    reply = say(api, mohit, "Scanned receipt of a bill our group shared:\nTEA 50.00\nTOTAL 50.00").json()
    assert reply["question"].startswith("Who had what? (Tea)")
    assert reply["draft"]["payers"] == []


def test_receipt_that_misses_its_subtotal_gets_one_second_look(api, mohit, monkeypatch):
    receipt = {"total": "694.00", "subtotal": "694.00"}
    fake_llm(
        monkeypatch,
        found(**receipt, items=[{"name": "Room", "amount": "189.00"}, {"name": "Bar", "amount": "127.00"}]),  # unit price
        found(**receipt, items=[{"name": "Room", "amount": "567.00"}, {"name": "Bar", "amount": "127.00"}]),  # corrected
    )
    receipt_text = "Scanned receipt of a bill our group shared:\n3 x ROOM @ 567.00\n189.00\nBAR 127.00\nSUBTOTAL 694.00"
    reply = say(api, mohit, receipt_text).json()
    assert [item["amount"] for item in reply["draft"]["items"]] == ["567.00", "127.00"]
    assert reply["question"].startswith("Who had what?")


def test_llm_down_gives_a_friendly_503(api, mohit, monkeypatch):
    def broken(*args, **kwargs):
        raise GroqError("rate limited")

    monkeypatch.setattr(views, "extract", broken)
    assert say(api, mohit, "dinner 900").status_code == 503


def test_an_answer_that_breaks_the_schema_asks_to_rephrase(api, mohit, monkeypatch):
    def misunderstood(*args, **kwargs):
        raise groq_error(BadRequestError, 400)

    monkeypatch.setattr(views, "extract", misunderstood)
    response = say(api, mohit, "Unket paid")
    assert response.status_code == 400
    assert response.json()["detail"].startswith("Sorry, I couldn't understand that.")


def test_llm_call_uses_a_strict_schema_with_member_names(monkeypatch):
    sent = {}

    class FakeGroq:
        def __init__(self, **options):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **request):
            sent.update(request)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(found(total="900"))))])

    monkeypatch.setattr(llm, "Groq", FakeGroq)
    assert llm.extract("dinner 900", ["Mohit", "Rahul"], "Mohit", "", [])["total"] == "900"
    schema = sent["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"]["properties"]["payers"]["items"]["properties"]["person"]["enum"] == ["Mohit", "Rahul", "everyone"]


def groq_error(error_class, status):
    return error_class("error", response=httpx.Response(status, request=httpx.Request("POST", "http://x")), body=None)


def test_rate_limited_model_falls_back_to_the_other_one(monkeypatch):
    used = []

    class FakeGroq:
        def __init__(self, **options):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, model, **request):
            used.append(model)
            if model == llm.MODEL:
                raise groq_error(RateLimitError, 429)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(found(total="50"))))])

    monkeypatch.setattr(llm, "Groq", FakeGroq)
    assert llm.extract("tea 50", ["Mohit"], "Mohit", "", [])["total"] == "50"
    assert used == ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]


def test_quota_used_up_message(api, mohit, monkeypatch):
    def limited(*args, **kwargs):
        raise groq_error(RateLimitError, 429)

    monkeypatch.setattr(views, "extract", limited)
    response = say(api, mohit, "dinner 900")
    assert response.status_code == 503
    assert response.json()["detail"].startswith("The free AI quota is used up")


def test_scan_reads_a_receipt_image(api, mohit):
    image = Image.new("RGB", (500, 160), "white")
    ImageDraw.Draw(image).text((20, 50), "TOTAL 100.00", fill="black", font=ImageFont.load_default(size=48))
    file = io.BytesIO()
    image.save(file, "PNG")
    file.name = "receipt.png"
    file.seek(0)
    response = api.post("/api/assistant/scan", {"image": file}, format="multipart")
    assert response.status_code == 200
    assert response.json()["text"].startswith("Scanned receipt of a bill our group shared:")
    assert "100.00" in response.json()["text"]


def test_scan_rejects_non_images(api, mohit):
    file = io.BytesIO(b"not an image")
    file.name = "notes.txt"
    assert api.post("/api/assistant/scan", {"image": file}, format="multipart").status_code == 400


def test_transcribe(api, mohit, monkeypatch):
    sent = {}

    def create(**request):
        sent.update(request)
        return SimpleNamespace(text=" Rahul paid ")

    class FakeGroq:
        audio = SimpleNamespace(transcriptions=SimpleNamespace(create=create))

    monkeypatch.setattr(stt, "Groq", FakeGroq)
    file = io.BytesIO(b"fake audio")
    file.name = "voice.webm"
    assert api.post("/api/groups/1/assistant/transcribe", {"audio": file}, format="multipart").json() == {"text": "Rahul paid"}
    assert sent["prompt"] == "Names: Mohit, Rahul, Ankit."  # spelling hint for Whisper


def test_transcribe_when_groq_is_down(api, mohit, monkeypatch):
    def broken(audio, names):
        raise GroqError("no key")

    monkeypatch.setattr(views, "transcribe", broken)
    file = io.BytesIO(b"fake audio")
    file.name = "voice.webm"
    assert api.post("/api/groups/1/assistant/transcribe", {"audio": file}, format="multipart").status_code == 503
