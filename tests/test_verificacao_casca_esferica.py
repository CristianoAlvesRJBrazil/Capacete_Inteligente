"""Verificação do FEM axissimétrico contra a solução exata (Fase 2, Tab. 3)."""
import pytest

from verificacao_casca_esferica import fator_blindagem, fator_exato


@pytest.mark.parametrize("a, b, mu_r", [
    (0.09, 0.10, 1000.0),        # casca espessa
    (0.0998, 0.10, 64000.0),     # 10 lâminas de 20 um de fita Fe
])
def test_erro_abaixo_de_1_por_cento(a, b, mu_r):
    sf = fator_blindagem(a, b, mu_r, n=2)
    assert sf == pytest.approx(fator_exato(a, b, mu_r), rel=0.01)


def test_lamina_unica_de_fita():
    """Uma única fita de 18 µm: a malha precisa reconhecer a casca fina."""
    a, b, mu_r = 0.10 - 18e-6, 0.10, 70000.0
    sf = fator_blindagem(a, b, mu_r, n=1)
    assert sf == pytest.approx(fator_exato(a, b, mu_r), rel=0.01)
