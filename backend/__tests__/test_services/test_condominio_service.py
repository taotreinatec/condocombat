"""Unit tests for CondominioService — mocked repository."""

from unittest.mock import MagicMock

import pytest

from app.models.condominio import Condominio
from app.repositories.condominio import CondominioRepository
from app.schemas.condominio import CondominioCreate, CondominioUpdate
from app.services.condominio import (
    CondominioJaExiste,
    CondominioNaoEncontrado,
    CondominioService,
)


@pytest.fixture
def repo_mock():
    return MagicMock(spec=CondominioRepository)


@pytest.fixture
def service(repo_mock):
    return CondominioService(repository=repo_mock)


class TestCriar:
    async def test_cria_condominio_sem_cnpj(self, service, repo_mock):
        data = CondominioCreate(
            nome="Condomínio Teste", endereco="Rua Teste, 100"
        )
        repo_mock.create.return_value = Condominio(
            id=1, nome="Condomínio Teste", endereco="Rua Teste, 100"
        )
        result = await service.criar(data)
        assert result.id == 1
        assert result.nome == "Condomínio Teste"
        repo_mock.get_by_cnpj.assert_not_called()
        repo_mock.create.assert_called_once_with(data)

    async def test_cria_com_cnpj_valido(self, service, repo_mock):
        data = CondominioCreate(
            nome="Edifício Central",
            endereco="Av. Principal, 500",
            cnpj="12.345.678/0001-90",
        )
        repo_mock.get_by_cnpj.return_value = None
        repo_mock.create.return_value = Condominio(
            id=2,
            nome="Edifício Central",
            endereco="Av. Principal, 500",
            cnpj="12.345.678/0001-90",
        )
        result = await service.criar(data)
        assert result.id == 2
        repo_mock.get_by_cnpj.assert_called_once_with("12.345.678/0001-90")

    async def test_rejeita_cnpj_duplicado(self, service, repo_mock):
        data = CondominioCreate(
            nome="Outro Condomínio",
            endereco="Rua Outra, 50",
            cnpj="12.345.678/0001-90",
        )
        repo_mock.get_by_cnpj.return_value = Condominio(
            id=1, nome="Existente", endereco="Rua X, 10"
        )
        with pytest.raises(CondominioJaExiste) as exc:
            await service.criar(data)
        assert "12.345.678/0001-90" in str(exc.value)
        repo_mock.create.assert_not_called()


class TestListar:
    async def test_lista_todos(self, service, repo_mock):
        repo_mock.get_all.return_value = [
            Condominio(id=1, nome="A", endereco="Rua A"),
        ]
        result = await service.listar()
        assert len(result) == 1
        repo_mock.get_all.assert_called_once()

    async def test_lista_vazio(self, service, repo_mock):
        repo_mock.get_all.return_value = []
        result = await service.listar()
        assert result == []


class TestBuscar:
    async def test_retorna_condominio(self, service, repo_mock):
        repo_mock.get_by_id.return_value = Condominio(
            id=1, nome="Teste", endereco="Rua T"
        )
        result = await service.buscar(1)
        assert result.id == 1
        assert result.nome == "Teste"

    async def test_lanca_erro_nao_encontrado(self, service, repo_mock):
        repo_mock.get_by_id.return_value = None
        with pytest.raises(CondominioNaoEncontrado):
            await service.buscar(999)


class TestAtualizar:
    async def test_atualiza_sem_cnpj(self, service, repo_mock):
        repo_mock.update.return_value = Condominio(
            id=1, nome="Novo", endereco="Rua X"
        )
        data = CondominioUpdate(nome="Novo")
        result = await service.atualizar(1, data)
        assert result.nome == "Novo"
        repo_mock.get_by_cnpj.assert_not_called()

    async def test_atualiza_com_cnpj_novo(self, service, repo_mock):
        repo_mock.get_by_cnpj.return_value = None
        repo_mock.update.return_value = Condominio(
            id=1, nome="Cond", endereco="Rua X", cnpj="99.999.999/0001-99"
        )
        data = CondominioUpdate(cnpj="99.999.999/0001-99")
        result = await service.atualizar(1, data)
        assert result.cnpj == "99.999.999/0001-99"

    async def test_rejeita_cnpj_duplicado_em_update(self, service, repo_mock):
        repo_mock.get_by_cnpj.return_value = Condominio(
            id=2, nome="Outro Cond", endereco="Rua O", cnpj="11.111.111/0001-11"
        )
        data = CondominioUpdate(cnpj="11.111.111/0001-11")
        with pytest.raises(CondominioJaExiste):
            await service.atualizar(1, data)
        repo_mock.update.assert_not_called()

    async def test_lanca_erro_se_nao_encontrado(self, service, repo_mock):
        repo_mock.update.return_value = None
        data = CondominioUpdate(nome="Novo")
        with pytest.raises(CondominioNaoEncontrado):
            await service.atualizar(999, data)


class TestRemover:
    async def test_remove_com_sucesso(self, service, repo_mock):
        repo_mock.delete.return_value = True
        await service.remover(1)
        repo_mock.delete.assert_called_once_with(1)

    async def test_lanca_erro_nao_encontrado(self, service, repo_mock):
        repo_mock.delete.return_value = False
        with pytest.raises(CondominioNaoEncontrado):
            await service.remover(999)
