from __future__ import annotations

from pathlib import Path

import pytest

from helio.conversation.store import ConversationStore
from helio.schemas.conversation import ConversationRequest, ConversationResponse


@pytest.fixture
def store(tmp_path: Path) -> ConversationStore:
    return ConversationStore(tmp_path / "conversation.sqlite3")


def test_self_test_round_trips(store: ConversationStore):
    assert store.self_test() is True


def test_create_and_get_by_id(store: ConversationStore):
    request = ConversationRequest(message="get into btc", intent="GET_INTO_BTC", risk_profile="balanced")
    store.create(request)
    fetched = store.get_by_id(request.request_id)
    assert fetched is not None
    assert fetched.status == "PENDING"
    assert fetched.response is None


def test_get_pending_excludes_answered(store: ConversationStore):
    pending_req = ConversationRequest(message="a", intent="UNKNOWN", risk_profile="balanced")
    answered_req = ConversationRequest(message="b", intent="UNKNOWN", risk_profile="balanced")
    store.create(pending_req)
    store.create(answered_req)
    store.respond(answered_req.request_id, ConversationResponse(kind="unavailable", message="n/a"))

    pending = store.get_pending()
    assert [r.request_id for r in pending] == [pending_req.request_id]


def test_respond_unknown_request_raises_key_error(store: ConversationStore):
    with pytest.raises(KeyError):
        store.respond("nope", ConversationResponse(kind="unavailable", message="n/a"))


def test_respond_twice_raises_value_error(store: ConversationStore):
    request = ConversationRequest(message="a", intent="UNKNOWN", risk_profile="balanced")
    store.create(request)
    store.respond(request.request_id, ConversationResponse(kind="unavailable", message="n/a"))
    with pytest.raises(ValueError):
        store.respond(request.request_id, ConversationResponse(kind="unavailable", message="n/a"))


def test_error_kind_sets_failed_status(store: ConversationStore):
    request = ConversationRequest(message="a", intent="GET_INTO_BTC", risk_profile="balanced")
    store.create(request)
    updated = store.respond(request.request_id, ConversationResponse(kind="error", message="boom"))
    assert updated.status == "FAILED"
