import math

import pytest

from capacete.requisitos import (RequisitoInvalido, carregar,
                                 fatores_blindagem, pendencias)


@pytest.fixture(scope="module")
def reqs():
    return carregar()


def test_arquivo_valido(reqs):
    assert len(reqs) >= 16


def test_fatores_de_blindagem(reqs):
    f = fatores_blindagem(reqs)
    assert f["total"] == pytest.approx(3000)
    assert f["total_dB"] == pytest.approx(69.54, abs=0.01)
    assert f["passivo"] == pytest.approx(225)
    assert f["ativo"] == pytest.approx(400 / 30)
    assert f["passivo"] * f["ativo"] == pytest.approx(f["total"])


def test_meta_final_abaixo_da_operacao_do_opm(reqs):
    assert (reqs["campo_residual_final"].em_si()
            < reqs["campo_operacao_opm"].em_si())


def test_pendencias_tem_fase(reqs):
    abertas = pendencias(reqs)
    assert abertas
    assert all(r.situacao != "definido" for r in abertas)


def test_rejeita_valor_em_requisito_a_definir(tmp_path):
    arq = tmp_path / "r.yaml"
    arq.write_text(
        "requisitos:\n"
        "  - {id: R01, chave: x, parametro: X, valor: 1, unidade: nT,\n"
        "     situacao: a_definir, justificativa: j, origem: o,\n"
        "     fase_responsavel: F0, objetivos: [O1]}\n", encoding="utf-8")
    with pytest.raises(RequisitoInvalido):
        carregar(arq)


def test_rejeita_unidade_desconhecida(tmp_path):
    arq = tmp_path / "r.yaml"
    arq.write_text(
        "requisitos:\n"
        "  - {id: R01, chave: x, parametro: X, valor: 1, unidade: gauss,\n"
        "     situacao: definido, justificativa: j, origem: o,\n"
        "     fase_responsavel: F0, objetivos: [O1]}\n", encoding="utf-8")
    with pytest.raises(RequisitoInvalido):
        carregar(arq)
