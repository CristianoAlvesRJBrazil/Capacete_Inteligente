"""Teste de fumaça da interface gráfica: o app roda sem exceções."""
from pathlib import Path

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
APP = Path(__file__).resolve().parents[1] / "interface" / "app_casca_esferica.py"


def test_app_roda_e_reproduz_o_exemplo():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    assert not at.exception
    metricas = {m.label: m.value for m in at.metric}
    assert metricas["Fator de blindagem"] == "61,1"
    assert metricas["Fórmula exata"] == "61,1"


def test_exemplo_de_casca_fina():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    at.sidebar.selectbox(key="exemplo").set_value(
        "Fita Fe nanocristalina: 10 lâminas de 20 µm").run()
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["Fórmula exata"] == "86,2"


def test_material_da_base():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    at.sidebar.selectbox(key="material").set_value("finemet_ft3m").run()
    at.sidebar.number_input(key="n_laminas").set_value(10)
    at.sidebar.button[0].click().run()
    assert not at.exception
    metricas = {m.label: m.value for m in at.metric}
    assert metricas["Fórmula exata"] == "84,8"           # µr 70.000, 0,18 mm
    assert metricas["Fração da saturação"] == "6 %"


def test_tres_camadas_sobrepostas():
    from verificacao_casca_esferica import fator_exato_camadas

    at = AppTest.from_file(str(APP), default_timeout=300).run()
    at.number_input(key="numero_camadas").set_value(3).run()
    at.selectbox(key="material_camada_2").set_value("mumetall").run()
    at.number_input(key="t_camada_0").set_value(0.18)
    at.number_input(key="t_camada_1").set_value(3.0)
    at.button(key="simular_camadas").click().run()
    assert not at.exception
    resultado = at.session_state["resultado_camadas"][1]
    tabela = resultado["tabela"]
    assert len(tabela) == 3
    assert tabela[0]["Espessura (mm)"] == 0.18
    assert tabela[1]["Raio interno (cm)"] == pytest.approx(tabela[0]["Raio externo (cm)"])
    assert tabela[-1]["Raio externo (cm)"] == pytest.approx(10)
    camadas = [(r["Raio externo (cm)"] / 100, r["µr"]) for r in tabela]
    assert resultado["exato"] == pytest.approx(
        fator_exato_camadas(resultado["a"], camadas))
    assert resultado["campo"] == pytest.approx(90000 / resultado["fator"])
    for nome in ["Mapa do campo", "Perfil do campo", "Visão 3D",
                 "Efeito dos parâmetros", "Base de materiais", "Entenda e experimente"]:
        assert sum(aba.label == nome for aba in at.tabs) == 2
    at.radio(key="perfil_camadas").set_value("Eixo vertical z").run()
    at.selectbox(key="camada_varredura").set_value(2).run()
    assert not at.exception
    at.number_input(key="t_camada_0").set_value(60.0).run()
    at.button(key="simular_camadas").click().run()
    assert not at.exception
    assert any("espessura total" in e.value for e in at.error)
