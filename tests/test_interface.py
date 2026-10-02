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
    at.sidebar.selectbox[0].set_value(
        "Fita Fe nanocristalina: 10 lâminas de 20 µm").run()
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["Fórmula exata"] == "86,2"
