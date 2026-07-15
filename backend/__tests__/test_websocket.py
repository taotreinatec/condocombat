"""Tests for WebSocket /ws/ocorrencias feed."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings
from app.main import app
from app.schemas.ws_message import EventType, WSMessage
from app.services.ws_manager import manager


@pytest.fixture
def client():
    return TestClient(app)


# ── Connection ────────────────────────────────────────────────────────


def test_connect_disconnect(client: TestClient):
    """Deve aceitar conexão e desconectar sem erros."""
    with client.websocket_connect("/ws/ocorrencias") as ws:
        assert ws is not None


def test_multiple_connections(client: TestClient):
    """Deve aceitar múltiplas conexões simultâneas."""
    with client.websocket_connect("/ws/ocorrencias") as ws1:
        with client.websocket_connect("/ws/ocorrencias") as ws2:
            assert ws1 is not None
            assert ws2 is not None


def test_send_and_receive_pong(client: TestClient):
    """Enviar mensagem deve responder com pong."""
    with client.websocket_connect("/ws/ocorrencias") as ws:
        ws.send_text(json.dumps({"type": "ping"}))
        data = ws.receive_json()
        assert data["type"] == EventType.PONG.value


def test_send_invalid_json(client: TestClient):
    """JSON inválido deve responder com pong."""
    with client.websocket_connect("/ws/ocorrencias") as ws:
        ws.send_text("not-json")
        data = ws.receive_json()
        assert data["type"] == EventType.PONG.value


def test_send_pong_message(client: TestClient):
    """Enviar pong deve ser aceito silenciosamente (sem resposta)."""
    with client.websocket_connect("/ws/ocorrencias") as ws:
        ws.send_text(json.dumps({"type": "pong"}))
        # No immediate response expected — test passes if no exception


# ── Authentication ────────────────────────────────────────────────────


def test_connect_with_invalid_token(client: TestClient):
    """Token JWT inválido na query string deve aceitar anônimo."""
    with client.websocket_connect("/ws/ocorrencias?token=invalid") as ws:
        assert ws is not None


def test_connect_with_valid_token(client: TestClient):
    """Token JWT válido deve ser aceito."""
    token = jwt.encode(
        {
            "sub": "admin@condocombat.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with client.websocket_connect(f"/ws/ocorrencias?token={token}") as ws:
        assert ws is not None


# ── Connection Manager ────────────────────────────────────────────────


async def test_manager_tracks_connections(client: TestClient):
    """Manager deve rastrear número de conexões ativas."""
    assert manager.active_connections == 0

    with client.websocket_connect("/ws/ocorrencias") as _ws:
        assert manager.active_connections == 1

    assert manager.active_connections == 0


async def test_manager_tracks_multiple_connections(client: TestClient):
    """Manager deve rastrear múltiplas conexões."""
    with client.websocket_connect("/ws/ocorrencias") as _ws1:
        with client.websocket_connect("/ws/ocorrencias") as _ws2:
            assert manager.active_connections == 2

    assert manager.active_connections == 0


# ── Broadcast ─────────────────────────────────────────────────────────


async def test_broadcast_reaches_all_connected(client: TestClient):
    """Broadcast deve alcançar todos conectados."""
    with client.websocket_connect("/ws/ocorrencias") as ws1:
        with client.websocket_connect("/ws/ocorrencias") as ws2:
            msg = WSMessage(
                type=EventType.OCORRENCIA_CRIADA,
                data={"ocorrencia_id": 1, "titulo": "Teste"},
            )

            await manager.broadcast(msg)

            received1 = ws1.receive_json()
            received2 = ws2.receive_json()

            assert received1["type"] == EventType.OCORRENCIA_CRIADA.value
            assert received2["type"] == EventType.OCORRENCIA_CRIADA.value
            assert received1["data"]["ocorrencia_id"] == 1
            assert received2["data"]["ocorrencia_id"] == 1


async def test_broadcast_after_disconnect(client: TestClient):
    """Broadcast não deve falhar quando cliente desconecta."""
    with client.websocket_connect("/ws/ocorrencias") as _ws1:
        pass  # ws1 closes here

    with client.websocket_connect("/ws/ocorrencias") as ws2:
        msg = WSMessage(
            type=EventType.OCORRENCIA_CRIADA,
            data={"ocorrencia_id": 2},
        )

        await manager.broadcast(msg)

        received = ws2.receive_json()
        assert received["type"] == EventType.OCORRENCIA_CRIADA.value
