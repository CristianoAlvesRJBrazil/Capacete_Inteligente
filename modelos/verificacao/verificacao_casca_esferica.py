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


def fator_blindagem(a, b, mu_r, n=1, H0=1.0, R=2.0):
    s = np.r_[np.linspace(0, a, 8 * n + 1),
              np.linspace(a, b, 8 * n + 1)[1:],
              np.geomspace(b, R, 24 * n + 1)[1:]]
    m = malha_polar(s, 90 * n)
    basis = Basis(m, ElementTriP2())
    rc = np.hypot(*m.p[:, m.t].mean(axis=1))      # raio do centroide
    mu = np.where((rc > a) & (rc < b), mu_r, 1.0)
    mu_qp = mu[:, None] * np.ones_like(basis.X[0])[None, :]
    A = asm(rigidez, basis, mu=mu_qp)
    D = basis.get_dofs(lambda x: np.hypot(x[0], x[1]) > 0.999 * R)
    psi = basis.zeros()
    psi[D] = -H0 * basis.doflocs[1, D]            # campo uniforme ao longe
    psi = solve(*condense(A, np.zeros_like(psi), x=psi, D=D))
    dz = 0.5 * a                                  # campo interno uniforme
    v = basis.probes(np.array([[1e-6, 1e-6], [dz, -dz]])) @ psi
    H_in = (v[1] - v[0]) / (2 * dz)               # H_z = -d(psi)/dz
    return H0 / H_in


def fator_exato(a, b, mu_r):
    return 1 + 2 / 9 * (mu_r - 1) ** 2 / mu_r * (1 - (a / b) ** 3)


if __name__ == "__main__":
    a, b, mu_r = 0.09, 0.10, 1000.0               # raios em metros
    ref = fator_exato(a, b, mu_r)
    print(f"SF exato = {ref:.3f}")
    for n in (1, 2, 4):
        sf = fator_blindagem(a, b, mu_r, n=n)
        erro = 100 * (sf / ref - 1)
        print(f"refino {n}: SF FEM = {sf:.3f}  erro = {erro:+.3f} %")
