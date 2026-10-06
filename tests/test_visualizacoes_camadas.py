import numpy as np
import pytest

from interface.visualizacoes_camadas import linhas_fluxo, varrer, fator_das_entradas
from verificacao_casca_esferica import coeficientes_camadas


def test_linhas_amostram_interfaces_de_fitas_finas():
    a, b = 0.09998, 0.1
    camadas = [(0.09999, 70000), (b, 2200)]
    sf, coefs = coeficientes_camadas(a, camadas)
    resultado = dict(a=a, b=b, coeficientes=coefs,
                     tabela=[{"Raio externo (cm)": r * 100, "µr": mu} for r, mu in camadas])
    linhas = linhas_fluxo(resultado)
    for linha in linhas:
        assert np.isfinite(linha).all()
    # A linha que cruza a cavidade percorre todas as faces, mesmo a 10 µm.
    raios = np.hypot(*linhas[0].T)
    for interface in [a, camadas[0][0], b]:
        assert np.min(np.abs(raios - interface)) < 1e-12
    regioes = np.searchsorted([a, camadas[0][0], b], raios, side="right")
    mus = np.array([1, 70000, 2200, 1])[regioes]
    A, C = coefs[regioes, 0], coefs[regioes, 1]
    fluxo = mus * (A - 2 * C * (b / raios)**3) * linhas[0][:, 0]**2
    np.testing.assert_allclose(fluxo, fluxo[0], rtol=1e-8)


@pytest.mark.parametrize("parametro", ["Espessura (mm)", "Permeabilidade µr"])
def test_varredura_preserva_o_caso_atual_e_as_outras_camadas(parametro):
    entradas = [("A", 0.18, 70000, 7.3, 1.23), ("B", 3., 2200, 4.9, 0.49)]
    anterior = list(entradas)
    xs, ys = varrer(10, entradas, 0, parametro)
    atual = entradas[0][1 if parametro == "Espessura (mm)" else 2]
    indice = np.flatnonzero(xs == atual)[0]
    assert ys[indice] == pytest.approx(fator_das_entradas(10, entradas))
    assert entradas == anterior
    assert np.isfinite(ys).all()
