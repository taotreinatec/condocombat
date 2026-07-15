"""Integration tests for Condominio REST endpoints."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from httpx import ASGITransport

from app.main import app
from app.models.condominio import Condominio
from app.routers.condominio import _get_service
from app.services.condominio import CondominioJaExiste, CondominioNaoEncontrado


@pytest.fixture
def mock_service() -> MagicMock:
    """Retorna um mock do CondominioService."""
    service = MagicMock()
    service.criar = AsyncMock()
    service.listar = AsyncMock()
    service.buscar = AsyncMock()
    service.atualizar = AsyncMock()
    service.remover = AsyncMock()
    return service


@pytest.fixture
def override_deps(mock_service: MagicMock) -> AsyncGenerator[None]:
    """Substitui _get_service no app para usar o mock."""

    async def _override() -> MagicMock:
        return mock_service

    app.dependency_overrides[_get_service] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient]:
    """Cliente HTTP assíncrono para testes."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _make_condominio(
    condominio_id: int = 1,
    nome: str = "Condomínio Teste",
    cnpj: str = "11.222.333/0001-44",
) -> Condominio:
    """Cria um objeto Condominio simulado."""
    from datetime import datetime, timezone

    obj = MagicMock(spec=Condominio)
    obj.id = condominio_id
    obj.nome = nome
    obj.endereco = "Rua Teste, 123"
    obj.cnpj = cnpj
    obj.telefone = "(11) 99999-0000"
    obj.email = "teste@condominio.com"
    obj.created_at = datetime.now(timezone.utc)
    obj.updated_at = datetime.now(timezone.utc)
    return obj


# ── GET /condominios ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_listar_retorna_lista(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    cond_a = _make_condominio(1, "Cond A")
    cond_b = _make_condominio(2, "Cond B")
    mock_service.listar.return_value = [cond_a, cond_b]

    response = await client.get("/condominios/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["nome"] == "Cond A"
    assert data[1]["nome"] == "Cond B"


@pytest.mark.asyncio
async def test_listar_retorna_vazia(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    mock_service.listar.return_value = []

    response = await client.get("/condominios/")

    assert response.status_code == 200
    assert response.json() == []


# ── GET /condominios/{id} ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_obter_retorna_condominio(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    cond = _make_condominio(1)
    mock_service.buscar.return_value = cond

    response = await client.get("/condominios/1")

    assert response.status_code == 200
    assert response.json()["nome"] == "Condomínio Teste"


@pytest.mark.asyncio
async def test_obter_404_quando_nao_encontrado(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    mock_service.buscar.side_effect = CondominioNaoEncontrado("não encontrado")

    response = await client.get("/condominios/999")

    assert response.status_code == 404
    assert "não encontrado" in response.json()["detail"]


# ── POST /condominios ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_criar_retorna_201(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    cond = _make_condominio(1)
    mock_service.criar.return_value = cond

    response = await client.post(
        "/condominios/",
        json={"nome": "Condomínio Teste", "endereco": "Rua Teste, 123"},
    )

    assert response.status_code == 201
    assert response.json()["nome"] == "Condomínio Teste"


@pytest.mark.asyncio
async def test_criar_422_quando_dados_invalidos(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    response = await client.post("/condominios/", json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_criar_409_quando_cnpj_duplicado(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    mock_service.criar.side_effect = CondominioJaExiste("CNPJ já cadastrado")

    response = await client.post(
        "/condominios/",
        json={
            "nome": "Outro Cond",
            "endereco": "Rua X",
            "cnpj": "11.222.333/0001-44",
        },
    )

    assert response.status_code == 409
    assert "CNPJ" in response.json()["detail"]


# ── PUT /condominios/{id} ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_atualizar_retorna_200(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    cond = _make_condominio(1, nome="Nome Atualizado")
    mock_service.atualizar.return_value = cond

    response = await client.put(
        "/condominios/1",
        json={"nome": "Nome Atualizado"},
    )

    assert response.status_code == 200
    assert response.json()["nome"] == "Nome Atualizado"


@pytest.mark.asyncio
async def test_atualizar_404_quando_nao_encontrado(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    mock_service.atualizar.side_effect = CondominioNaoEncontrado("não encontrado")

    response = await client.put(
        "/condominios/999",
        json={"nome": "Qualquer"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_atualizar_409_quando_cnpj_duplicado(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    mock_service.atualizar.side_effect = CondominioJaExiste("CNPJ já pertence a outro condomínio")

    response = await client.put(
        "/condominios/1",
        json={"cnpj": "11.222.333/0001-44"},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_atualizar_422_quando_cnpj_invalido(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    response = await client.put(
        "/condominios/1",
        json={"cnpj": "123"},
    )

    assert response.status_code == 422


# ── DELETE /condominios/{id} ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_remover_retorna_204(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    mock_service.remover = AsyncMock()

    response = await client.delete("/condominios/1")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_remover_404_quando_nao_encontrado(client: httpx.AsyncClient, override_deps: None, mock_service: MagicMock):
    mock_service.remover.side_effect = CondominioNaoEncontrado("não encontrado")

    response = await client.delete("/condominios/999")

    assert response.status_code == 404
