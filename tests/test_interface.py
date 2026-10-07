"""Testes de fumaça da interface gráfica: o app roda sem exceções e reproduz
valores conhecidos."""
from pathlib import Path

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
APP = Path(__file__).resolve().parents[1] / "interface" / "app_casca_esferica.py"


def metricas(at):
    return {m.label: m.value for m in at.metric}


def test_app_roda_e_reproduz_o_exemplo_do_passo_2():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    assert not at.exception
    m = metricas(at)
    assert m["Fator de blindagem"] == "61,1"        # cavidade 9 cm + 10 mm, µr 1000
    assert m["Solução exata"] == "61,1"
    assert m["Camadas"] == "1"


def test_preset_de_uma_camada_da_base():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    at.sidebar.selectbox(key="preset").set_value(
        "1 camada: 10 lâminas de FINEMET FT-3M").run()
    assert not at.exception
    m = metricas(at)
    assert m["Solução exata"] == "94,0"             # a = 9 cm, t = 0,18 mm, µr 70.000
    assert m["Pior saturação"] == "5 %"               # 67,5 mT em Bs = 1,23 T


def test_preset_fe_fe_com_espacamento():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    at.sidebar.selectbox(key="preset").set_value(
        "Fe–Fe: 2 × 10 lâminas de FT-3M, 10 mm de espaçamento").run()
    assert not at.exception
    m = metricas(at)
    assert m["Camadas"] == "2"
    assert m["Solução exata"] == "2.278,4"
    assert abs(float(m["Erro do computador"].split()[0].replace(",", "."))) < 0.1


def test_montagem_manual_de_duas_camadas():
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    at.sidebar.number_input(key="n_camadas").set_value(2).run()
    at.sidebar.selectbox(key="cam1_mat").set_value("finemet_ft3m").run()
    at.sidebar.selectbox(key="cam2_mat").set_value("metglas_2705m").run()
    at.sidebar.number_input(key="cam1_lam").set_value(10)
    at.sidebar.number_input(key="cam2_lam").set_value(10)
    at.sidebar.select_slider(key="cam1_gap").set_value(10.0)
    at.sidebar.button[0].click().run()
    assert not at.exception
    m = metricas(at)
    assert m["Camadas"] == "2"
    assert m["Massa do metal"] != "incompleta"
    assert float(m["Solução exata"].replace(".", "").replace(",", ".")) > 2000   # espaçamento aplicado
