"""Unit tests for RivalidadeRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rivalidade import Rivalidade
from app.repositories.rivalidade import RivalidadeRepository


@pytest.fixture
def session() -> MagicMock:
    mock = AsyncMock(spec=AsyncSession)
    mock.add = MagicMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    mock.delete = AsyncMock()
    mock.execute = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock()
    result_mock.scalars = MagicMock()
    result_mock.scalars.return_value.all = MagicMock()
    mock.execute.return_value = result_mock
    return mock


@pytest.fixture
def repo(session: MagicMock) -> RivalidadeRepository:
    return RivalidadeRepository(session)


def _make(**kw: dict) -> MagicMock:
    from datetime import datetime, timezone

    vals: dict = {
        "id": 1,
        "apartamento_a_id": 101,
        "apartamento_b_id": 102,
        "motivo": "Barulho",
        "nivel": "moderado",
        "status": "ativa",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    vals.update(kw)
    m = MagicMock(spec=Rivalidade)
    for k, v in vals.items():
        setattr(m, k, v)
    return m


class TestCreate:
    async def test_creates(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        r = _make()
        result = await repo.create(r)
        session.add.assert_called_once_with(r)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once_with(r)
        assert result == r


class TestGetById:
    async def test_returns_when_found(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        session.execute.return_value.scalar_one_or_none.return_value = _make()
        result = await repo.get_by_id(1)
        assert result is not None
        assert result.id == 1

    async def test_returns_none_when_not_found(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        session.execute.return_value.scalar_one_or_none.return_value = None
        assert await repo.get_by_id(999) is None


class TestGetAll:
    async def test_returns_list(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        a, b = _make(id=1), _make(id=2, apartamento_a_id=201)
        session.execute.return_value.scalars.return_value.all.return_value = [a, b]
        result = await repo.get_all()
        assert len(result) == 2


class TestGetByApartamento:
    async def test_returns_rivalidades_do_apartamento(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        a = _make(apartamento_a_id=101, apartamento_b_id=102)
        b = _make(apartamento_a_id=103, apartamento_b_id=101)
        session.execute.return_value.scalars.return_value.all.return_value = [a, b]
        result = await repo.get_by_apartamento(101)
        assert len(result) == 2

    async def test_returns_empty_when_nenhuma(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        session.execute.return_value.scalars.return_value.all.return_value = []
        assert await repo.get_by_apartamento(999) == []


class TestGetBetween:
    async def test_returns_when_found(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        r = _make(apartamento_a_id=101, apartamento_b_id=102)
        session.execute.return_value.scalar_one_or_none.return_value = r
        result = await repo.get_between(101, 102)
        assert result is not None
        assert result.apartamento_a_id == 101

    async def test_returns_none_when_not_found(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        session.execute.return_value.scalar_one_or_none.return_value = None
        assert await repo.get_between(1, 2) is None


class TestTopRivalidades:
    async def test_returns_sorted_by_nivel(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        r1 = _make(id=1, nivel="leve")
        r2 = _make(id=2, nivel="moderado")
        r3 = _make(id=3, nivel="belico")
        r4 = _make(id=4, nivel="intenso")
        session.execute.return_value.scalars.return_value.all.return_value = [r1, r2, r3, r4]
        result = await repo.top_rivalidades(limite=10)
        # ordem: belico(0), intenso(1), moderado(2), leve(3)
        assert [r.id for r in result] == [3, 4, 2, 1]

    async def test_limita_quantidade(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        session.execute.return_value.scalars.return_value.all.return_value = [_make(id=i) for i in range(5)]
        result = await repo.top_rivalidades(limite=3)
        assert len(result) == 3


class TestUpdate:
    async def test_updates(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        r = _make()
        repo.get_by_id = AsyncMock(return_value=r)
        result = await repo.update(1, {"nivel": "serio"})
        assert r.nivel == "serio"
        session.commit.assert_awaited_once()
        assert result == r

    async def test_returns_none_when_not_found(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        repo.get_by_id = AsyncMock(return_value=None)
        assert await repo.update(999, {}) is None
        session.commit.assert_not_called()


class TestDelete:
    async def test_deletes(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        repo.get_by_id = AsyncMock(return_value=_make())
        assert await repo.delete(1) is True
        session.delete.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_returns_false_when_not_found(self, repo: RivalidadeRepository, session: MagicMock) -> None:
        repo.get_by_id = AsyncMock(return_value=None)
        assert await repo.delete(999) is False
        session.delete.assert_not_called()
