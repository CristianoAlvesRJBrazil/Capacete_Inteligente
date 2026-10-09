import csv
import shutil

import pytest

from capacete.materiais import PASTA_PADRAO, BaseInvalida, carregar


@pytest.fixture(scope="module")
def base():
    return carregar()


def test_base_valida(base):
    assert len(base.materiais) >= 20
    assert len(base.registros) >= 140
    assert all(r.localizacao and r.fonte_id for r in base.registros)


def test_materiais_simulaveis_tem_permeabilidade(base):
    for m in base.simulaveis():
        assert base.parametros_simulacao(m.material_id)["valores"]["mu_r"] > 1


def test_escolha_conservadora_na_menor_frequencia(base):
    p = base.parametros_simulacao("finemet_ft3m")
    assert p["valores"]["mu_r"] == 70000            # 1 kHz, não 100 kHz
    assert p["registros"]["mu_r"].frequencia_Hz == 1000
    assert p["valores"]["B_s"] == pytest.approx(1.23)


def test_permeabilidade_maxima_e_faixa(base):
    assert base.parametros_simulacao("mumetall", "maxima")["valores"]["mu_r"] == 150000
    p = base.parametros_simulacao("vitroperm_500f")
    assert p["valores"]["mu_r"] == 15000            # limite inferior da faixa
    assert any("faixa" in aviso for aviso in p["avisos"])


def test_saturacao_na_temperatura_ambiente(base):
    assert base.parametros_simulacao("ferrita_n87_tdk")["valores"]["B_s"] == 0.49


def _copia_com_alteracao(tmp_path, alterar):
    destino = tmp_path / "materiais"
    shutil.copytree(PASTA_PADRAO, destino)
    caminho = destino / "registros.csv"
    with open(caminho, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    alterar(linhas[0])
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)
    return destino


@pytest.mark.parametrize("alterar", [
    lambda r: r.update(unidade="mm"),               # unidade errada
    lambda r: r.update(localizacao=""),             # sem localização na fonte
    lambda r: r.update(valor="1e9"),                # fora da faixa plausível
    lambda r: r.update(fonte_id="inexistente"),     # fonte desconhecida
])
def test_validador_rejeita_registro_invalido(tmp_path, alterar):
    with pytest.raises(BaseInvalida):
        carregar(_copia_com_alteracao(tmp_path, alterar))


def test_limite_superior_nao_e_valor_conservador(base):
    """'≤ 600.000' (VITROPERM 800 R) é teto, não valor: o simulador avisa que é otimista."""
    p = base.parametros_simulacao("vitroperm_800r")
    assert p["registros"]["mu_r"].so_limite_superior
    assert any("limite superior" in a for a in p["avisos"])
    # na norma, o mínimo garantido entra como piso conservador
    assert base.parametros_simulacao("permalloy_mil_n_14411_comp1")["valores"]["mu_r"] == 40000
