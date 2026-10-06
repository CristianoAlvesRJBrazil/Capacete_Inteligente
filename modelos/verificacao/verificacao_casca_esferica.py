"""Verificação: casca esférica de alta permeabilidade em campo uniforme.

FEM axissimétrico (rho, z) do potencial escalar magnético total psi,
com H = -grad(psi) e div(mu grad psi) = 0. O fator de blindagem no
centro é comparado com a solução exata.
"""
import numpy as np
from skfem import (MeshTri, Basis, ElementTriP2, BilinearForm, asm,
                   condense, solve)
from skfem.helpers import dot, grad


def malha_polar(s, nth):
    """Semidisco no plano (rho, z): anéis de raio s, nth divisões."""
    th = np.linspace(0.0, np.pi, nth + 1)
    S, T = np.meshgrid(s[1:], th, indexing="ij")
    p = np.vstack([np.r_[0.0, (S * np.sin(T)).ravel()],
                   np.r_[0.0, (S * np.cos(T)).ravel()]])
    k = lambda i, j: 1 + i * (nth + 1) + j
    j = np.arange(nth)
    leque = np.vstack([np.zeros(nth, int), k(0, j), k(0, j + 1)])
    i, j = np.meshgrid(np.arange(len(s) - 2), j, indexing="ij")
    i, j = i.ravel(), j.ravel()
    q = [k(i, j), k(i + 1, j), k(i + 1, j + 1), k(i, j + 1)]
    t = np.hstack([leque, np.vstack([q[0], q[1], q[2]]),
                   np.vstack([q[0], q[2], q[3]])])
    return MeshTri(p, t)


@BilinearForm
def rigidez(u, v, w):
    # peso rho da formulação axissimétrica
    return w["mu"] * dot(grad(u), grad(v)) * w.x[0]


def resolver(a, b, mu_r, n=1, H0=1.0, R=2.0):
    """Resolve o problema; retorna a base FEM e o potencial psi."""
    return resolver_camadas(a, [(b, mu_r)], n=n, H0=H0, R=R)


def validar_camadas(a, camadas):
    """Camadas contíguas: (raio externo em m, µr), do interior ao exterior."""
    if not np.isfinite(a) or a <= 0 or not camadas:
        raise ValueError("A cavidade deve ter raio positivo e ao menos uma camada.")
    anterior = a
    for raio, mu in camadas:
        if not np.isfinite(raio) or raio <= anterior:
            raise ValueError("Os raios das camadas devem ser finitos e crescentes.")
        if not np.isfinite(mu) or mu < 1:
            raise ValueError("A permeabilidade relativa deve ser finita e >= 1.")
        anterior = raio


def resolver_camadas(a, camadas, n=1, H0=1.0, R=2.0):
    """Resolve todas as interfaces de uma casca composta no mesmo sistema FEM."""
    validar_camadas(a, camadas)
    b = camadas[-1][0]
    if R <= b or n < 1 or int(n) != n:
        raise ValueError("R deve superar o raio externo e n deve ser inteiro positivo.")
    aneis = [np.linspace(0, a, 8 * n + 1)]
    anterior = a
    for raio, _ in camadas:
        aneis.append(np.linspace(anterior, raio, 8 * n + 1)[1:])
        anterior = raio
    aneis.append(np.geomspace(b, R, 24 * n + 1)[1:])
    s = np.concatenate(aneis)
    m = malha_polar(s, 90 * n)
    basis = Basis(m, ElementTriP2())
    rc = np.hypot(*m.p)[m.t].mean(axis=0)         # raio médio dos vértices
    mu = np.ones_like(rc)
    anterior = a
    for raio, permeabilidade in camadas:
        mu[(rc > anterior) & (rc < raio)] = permeabilidade
        anterior = raio
    mu_qp = mu[:, None] * np.ones_like(basis.X[0])[None, :]
    A = asm(rigidez, basis, mu=mu_qp)
    D = basis.get_dofs(lambda x: np.hypot(x[0], x[1]) > 0.999 * R)
    psi = basis.zeros()
    psi[D] = -H0 * basis.doflocs[1, D]            # campo uniforme ao longe
    psi = solve(*condense(A, np.zeros_like(psi), x=psi, D=D))
    return basis, psi


def fator_blindagem(a, b, mu_r, n=1, H0=1.0, R=2.0):
    return fator_blindagem_camadas(a, [(b, mu_r)], n=n, H0=H0, R=R)


def fator_blindagem_camadas(a, camadas, n=1, H0=1.0, R=2.0):
    basis, psi = resolver_camadas(a, camadas, n=n, H0=H0, R=R)
    dz = 0.5 * a                                  # campo interno uniforme
    v = basis.probes(np.array([[1e-6, 1e-6], [dz, -dz]])) @ psi
    H_in = (v[1] - v[0]) / (2 * dz)               # H_z = -d(psi)/dz
    return H0 / H_in


def fator_exato(a, b, mu_r):
    return 1 + 2 / 9 * (mu_r - 1) ** 2 / mu_r * (1 - (a / b) ** 3)


def coeficientes_camadas(a, camadas):
    """Solução exata: psi=(A*r + B/r²)cos(theta), com r normalizado por b.

    Em cada interface, conserva psi e mu*dpsi/dr. A cavidade começa com
    A=1, B=0; o A exterior resultante é o fator de blindagem. Os coeficientes
    retornados são normalizados para campo aplicado unitário.
    """
    validar_camadas(a, camadas)
    b = camadas[-1][0]
    raios = np.array([a] + [r for r, _ in camadas]) / b
    mus = [1.0] + [mu for _, mu in camadas] + [1.0]
    coeficientes = [np.array([1.0, 0.0])]
    for i, raio in enumerate(raios):
        q = mus[i] / mus[i + 1]
        transferencia = np.array([
            [(2 + q) / 3, 2 * (1 - q) / (3 * raio**3)],
            [raio**3 * (1 - q) / 3, (1 + 2 * q) / 3],
        ])
        coeficientes.append(transferencia @ coeficientes[-1])
    fator = coeficientes[-1][0]
    return fator, np.array(coeficientes) / fator


def fator_exato_camadas(a, camadas):
    return coeficientes_camadas(a, camadas)[0]


def campo_exato_camadas(a, camadas, rho, z):
    """B_rho/B0 e B_z/B0 da casca composta, para campo aplicado em +z.

    Coordenadas em metros, com broadcasting NumPy. Em uma interface,
    retorna o limite pelo material exterior; no centro usa o limite regular.
    """
    _, coeficientes = coeficientes_camadas(a, camadas)
    rho, z = np.broadcast_arrays(np.asarray(rho, dtype=float),
                                 np.asarray(z, dtype=float))
    raio = np.hypot(rho, z)
    limites = [a] + [r for r, _ in camadas]
    regiao = np.searchsorted(limites, raio, side="right")
    mu = np.array([1.] + [mu for _, mu in camadas] + [1.])[regiao]
    A, C = coeficientes[regiao, 0], coeficientes[regiao, 1]
    termo = np.divide(C, (raio / limites[-1])**3,
                      out=np.zeros_like(raio), where=raio > 0)
    cos = np.divide(z, raio, out=np.zeros_like(raio), where=raio > 0)
    sen = np.divide(rho, raio, out=np.zeros_like(raio), where=raio > 0)
    return -3 * mu * termo * sen * cos, mu * (A + termo * (1 - 3 * cos**2))


if __name__ == "__main__":
    a, b, mu_r = 0.09, 0.10, 1000.0               # raios em metros
    ref = fator_exato(a, b, mu_r)
    print(f"SF exato = {ref:.3f}")
    for n in (1, 2, 4):
        sf = fator_blindagem(a, b, mu_r, n=n)
        erro = 100 * (sf / ref - 1)
        print(f"refino {n}: SF FEM = {sf:.3f}  erro = {erro:+.3f} %")
