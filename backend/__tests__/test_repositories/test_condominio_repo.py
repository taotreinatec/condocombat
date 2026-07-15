"""Unit tests for CondominioRepository — mocked AsyncSession."""

import pytest
from sqlalchemy.sql.selectable import Select

from app.models.condominio import Condominio
from app.repositories.condominio import CondominioRepository
from app.schemas.condominio import CondominioCreate, CondominioUpdate


@pytest.fixture
def repo(mock_session):
    return CondominioRepository(session=mock_session)


class TestCreate:
    async def test_creates_condominio(self, repo, mock_session):
        data = CondominioCreate(
            nome="Condomínio das Flores", endereco="Rua das Flores, 123"
        )
        result = await repo.create(data)
        assert result.nome == "Condomínio das Flores"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()

    async def test_creates_com_cnpj(self, repo, mock_session):
        data = CondominioCreate(
            nome="Edifício Central",
            endereco="Av. Central, 456",
            cnpj="12.345.678/0001-90",
        )
        result = await repo.create(data)
        assert result.cnpj == "12.345.678/0001-90"


class TestGetById:
    async def test_returns_condominio_when_found(self, repo, mock_session):
        cond = Condominio(id=1, nome="Teste", endereco="Rua X")
        mock_session.execute.return_value.scalar_one_or_none.return_value = cond
        result = await repo.get_by_id(1)
        assert result is not None
        assert result.id == 1
        assert result.nome == "Teste"

    async def test_returns_none_when_not_found(self, repo, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await repo.get_by_id(999)
        assert result is None

    async def test_executes_select_query(self, repo, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        await repo.get_by_id(5)
        call_args = mock_session.execute.call_args[0][0]
        assert isinstance(call_args, Select)


class TestGetAll:
    async def test_returns_all_condominios(self, repo, mock_session):
        conds = [
            Condominio(id=1, nome="A", endereco="Rua A"),
            Condominio(id=2, nome="B", endereco="Rua B"),
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = (
            conds
        )
        result = await repo.get_all()
        assert len(result) == 2
        mock_session.execute.assert_awaited_once()

    async def test_returns_empty_list(self, repo, mock_session):
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        result = await repo.get_all()
        assert result == []


class TestGetByCnpj:
    async def test_finds_by_cnpj(self, repo, mock_session):
        cond = Condominio(
            id=1,
            nome="Teste",
            endereco="Rua X",
            cnpj="12.345.678/0001-90",
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = cond
        result = await repo.get_by_cnpj("12.345.678/0001-90")
        assert result is not None
        assert result.cnpj == "12.345.678/0001-90"

    async def test_returns_none_when_not_found(self, repo, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await repo.get_by_cnpj("00.000/0000-00")
        assert result is None


class TestUpdate:
    async def test_updates_existing_condominio(self, repo, mock_session):
        cond = Condominio(id=1, nome="Antigo", endereco="Rua X")
        mock_session.execute.return_value.scalar_one_or_none.return_value = cond
        data = CondominioUpdate(nome="Novo Nome")
        result = await repo.update(1, data)
        assert result is not None
        assert result.nome == "Novo Nome"
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()

    async def test_returns_none_when_not_found(self, repo, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        data = CondominioUpdate(nome="Qualquer")
        result = await repo.update(999, data)
        assert result is None


class TestDelete:
    async def test_deletes_existing_condominio(self, repo, mock_session):
        cond = Condominio(id=1, nome="Teste", endereco="Rua X")
        mock_session.execute.return_value.scalar_one_or_none.return_value = cond
        result = await repo.delete(1)
        assert result is True
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_awaited_once()

    async def test_returns_false_when_not_found(self, repo, mock_session):
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        result = await repo.delete(999)
        assert result is False
        mock_session.delete.assert_not_called()
