import numpy as np
import pytest

from verificacao_casca_esferica import (
    campo_exato_camadas, coeficientes_camadas, fator_blindagem_camadas, fator_exato,
    fator_exato_camadas,
)


def test_uma_camada_reproduz_formula_existente():
    for mu in [1, 1500, 70000]:
        assert fator_exato_camadas(0.09, [(0.10, mu)]) == pytest.approx(
            fator_exato(0.09, 0.10, mu), rel=1e-10)


def test_camadas_iguais_equivalem_a_uma_casca():
    assert fator_exato_camadas(0.08, [(0.09, 1500), (0.10, 1500)]) == pytest.approx(
        fator_exato(0.08, 0.10, 1500), rel=1e-10)
    assert fator_exato_camadas(0.08, [(0.09, 1), (0.10, 1)]) == pytest.approx(1)


@pytest.mark.parametrize("camadas", [
    [(0.095, 70000), (0.10, 1500)],
    [(0.092, 1500), (0.096, 70000), (0.10, 10000)],
])
def test_fem_multicamadas_confere_com_solucao_exata(camadas):
    exato = fator_exato_camadas(0.09, camadas)
    fem = fator_blindagem_camadas(0.09, camadas, n=2)
    assert fem == pytest.approx(exato, rel=0.01)


def test_condicoes_em_todas_as_interfaces():
    camadas = [(0.095, 70000), (0.10, 1500)]
    fator, coeficientes = coeficientes_camadas(0.09, camadas)
    mus = [1, 70000, 1500, 1]
    for i, raio in enumerate([0.9, 0.95, 1.0]):
        A, B = coeficientes[i]
        C, D = coeficientes[i + 1]
        assert A * raio + B / raio**2 == pytest.approx(C * raio + D / raio**2)
        assert mus[i] * (A - 2 * B / raio**3) == pytest.approx(
            mus[i + 1] * (C - 2 * D / raio**3), rel=1e-8, abs=1e-10)
    assert coeficientes[-1, 0] == pytest.approx(1)
    assert coeficientes[0, 0] == pytest.approx(1 / fator)


@pytest.mark.parametrize("a, camadas", [
    (0, [(0.1, 1000)]), (0.09, []),
    (0.09, [(0.08, 1000)]), (0.09, [(0.1, float('nan'))]),
])
def test_geometria_invalida(a, camadas):
    with pytest.raises(ValueError):
        fator_exato_camadas(a, camadas)


def test_campo_vazio_uniforme_inclusive_no_centro():
    x, z = np.meshgrid(np.linspace(-0.2, 0.2, 21), np.linspace(-0.2, 0.2, 21))
    br, bz = campo_exato_camadas(0.09, [(0.095, 1), (0.10, 1)], x, z)
    np.testing.assert_allclose(br, 0, atol=1e-12)
    np.testing.assert_allclose(bz, 1, atol=1e-12)


def test_campo_na_cavidade_corresponde_a_blindagem_conjunta():
    camadas = [(0.095, 70000), (0.10, 2200)]
    br, bz = campo_exato_camadas(0.09, camadas, [0, 0.03, -0.02], [0, 0.03, -0.04])
    np.testing.assert_allclose(br, 0, atol=1e-12)
    np.testing.assert_allclose(bz, 1 / fator_exato_camadas(0.09, camadas))


def test_componentes_do_campo_nas_interfaces():
    camadas = [(0.095, 70000), (0.10, 2200)]
    mus = [1, 70000, 2200, 1]
    th = np.pi / 3
    for i, r in enumerate([0.09, 0.095, 0.10]):
        # Muito próximo das faces: o gradiente radial é amplificado por µr.
        faces = r * np.array([1 - 1e-12, 1 + 1e-12])
        br, bz = campo_exato_camadas(0.09, camadas, faces * np.sin(th), faces * np.cos(th))
        normal = br * np.sin(th) + bz * np.cos(th)
        tangencial_h = (br * np.cos(th) - bz * np.sin(th)) / mus[i:i + 2]
        assert normal[0] == pytest.approx(normal[1], rel=1e-5)
        assert tangencial_h[0] == pytest.approx(tangencial_h[1], rel=1e-5)
