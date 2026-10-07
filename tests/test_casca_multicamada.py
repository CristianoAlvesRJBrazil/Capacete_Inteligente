"""Verificação do modelo multicamada contra a solução exata (matrizes de
transferência) e contra a fórmula clássica de uma casca."""
import pytest

from casca_multicamada import (fator_blindagem_multicamada, fator_exato_multicamada,
                               inducao_exata_por_camada, simular_multicamada, validar)
from verificacao_casca_esferica import fator_exato

FE = 70000.0          # FINEMET FT-3M (1 kHz)
CO = 290000.0         # Metglas 2705M (DC, como fundido)
LAM_FE, LAM_CO = 18e-6, 22e-6


def test_exata_reduz_a_formula_classica():
    assert fator_exato_multicamada([(0.09, 0.10, 1000.0)]) == pytest.approx(
        fator_exato(0.09, 0.10, 1000.0), rel=1e-12)


def test_camadas_encostadas_do_mesmo_material_sao_uma_camada():
    duas = fator_exato_multicamada([(0.09, 0.095, 1000.0), (0.095, 0.10, 1000.0)])
    assert duas == pytest.approx(fator_exato(0.09, 0.10, 1000.0), rel=1e-9)


def test_espacamento_multiplica_os_fatores():
    a, t, g = 0.09, 10 * LAM_FE, 0.010
    encostadas = fator_exato_multicamada([(a, a + t, FE), (a + t, a + 2 * t, FE)])
    separadas = fator_exato_multicamada([(a, a + t, FE), (a + t + g, a + 2 * t + g, FE)])
    assert separadas > 10 * encostadas
    sf1 = fator_exato(a, a + t, FE)
    sf2 = fator_exato(a + t + g, a + 2 * t + g, FE)
    aproximado = sf1 * sf2 * (1 - ((a + t) / (a + t + g)) ** 3)
    assert separadas == pytest.approx(aproximado, rel=0.1)


@pytest.mark.parametrize("camadas", [
    [(0.09, 0.10, 1000.0)],
    [(0.09, 0.09 + 10 * LAM_FE, FE), (0.10, 0.10 + 10 * LAM_FE, FE)],
    [(0.09, 0.09 + 10 * LAM_CO, CO), (0.09 + 10 * LAM_CO, 0.09 + 10 * LAM_CO + 10 * LAM_FE, FE),
     (0.09 + 10 * LAM_CO + 10 * LAM_FE, 0.09 + 10 * LAM_CO + 20 * LAM_FE, FE)],
])
def test_fem_contra_solucao_exata(camadas):
    sf, bmax = simular_multicamada(camadas, n=1)
    assert sf == pytest.approx(fator_exato_multicamada(camadas), rel=0.01)
    for fem, exato in zip(bmax, inducao_exata_por_camada(camadas)):
        assert fem == pytest.approx(exato, rel=0.02)


def test_fator_blindagem_e_simular_coincidem():
    camadas = [(0.09, 0.0902, FE), (0.1, 0.1002, FE)]
    assert fator_blindagem_multicamada(camadas, n=1) == pytest.approx(
        simular_multicamada(camadas, n=1)[0])


@pytest.mark.parametrize("camadas", [
    [], [(0.0, 0.1, 1000.0)], [(0.09, 0.08, 1000.0)], [(0.09, 0.10, 0.5)],
    [(0.09, 0.10, 1000.0), (0.095, 0.11, 1000.0)],          # sobreposição
])
def test_validar_rejeita_configuracoes_invalidas(camadas):
    with pytest.raises(ValueError):
        validar(camadas)
