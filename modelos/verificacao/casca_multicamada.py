"""Casca esférica multicamada em campo uniforme.

Uma configuração é uma lista de camadas (r_in, r_out, mu_r), em metros, de
dentro para fora, sem sobreposição; o espaço entre camadas é ar. Camadas
encostadas têm r_out de uma igual ao r_in da seguinte.

O módulo resolve o problema por FEM axissimétrico (mesma formulação de
verificacao_casca_esferica.py) e pela solução exata por matrizes de
transferência, usada como referência de verificação.
"""
import numpy as np
from matplotlib.tri import LinearTriInterpolator, Triangulation
from skfem import Basis, ElementTriP2, asm, condense, solve

from verificacao_casca_esferica import malha_polar, rigidez


def validar(camadas):
    """Normaliza a lista de camadas e confere ordem e sobreposição."""
    cam = [(float(a), float(b), float(mu)) for a, b, mu in camadas]
    if not cam:
        raise ValueError("é preciso pelo menos uma camada")
    r = 0.0
    for a, b, mu in cam:
        if a <= 0 or a < r or b <= a or mu < 1:
            raise ValueError(f"camada inválida ou sobreposta: {(a, b, mu)}")
        r = b
    return cam


# ----------------------------------------------------------------- solução exata
def solucao_exata(camadas, H0=1.0):
    """Potencial psi = (A r + B / r^2) cos(theta) em cada região.

    Em cada interface de raio R, psi e mu dpsi/dr são contínuos, o que dá a
    matriz de transferência de dentro para fora. Retorna o fator de blindagem
    e a lista de regiões (r_in, r_out, mu, A, B), já escaladas para o campo
    aplicado H0.
    """
    cam = validar(camadas)
    interfaces = []
    for a, b, mu in cam:
        interfaces += [(a, 1.0, mu), (b, mu, 1.0)]
    A, B = 1.0, 0.0                                  # região interna, A_in = 1
    regioes = [[0.0, cam[0][0], 1.0, A, B]]
    for k, (R, mi, mj) in enumerate(interfaces):
        m = mi / mj
        A, B = (((2 + m) * A + 2 * (1 - m) * B / R**3) / 3,
                ((1 - m) * R**3 * A + (1 + 2 * m) * B) / 3)
        r_out = interfaces[k + 1][0] if k + 1 < len(interfaces) else np.inf
        regioes.append([R, r_out, mj, A, B])
    sf = A                                            # A_out com A_in = 1
    escala = -H0 / A                                  # impõe A_out = -H0
    regioes = [(ri, ro, mu, a * escala, b * escala) for ri, ro, mu, a, b in regioes]
    return sf, regioes


def fator_exato_multicamada(camadas):
    return solucao_exata(camadas)[0]


def inducao_exata_por_camada(camadas, H0=1.0):
    """Máximo de |B|/(mu0 H0) em cada camada, pela solução exata.

    |H| máximo em theta é max(|A - 2B/r^3|, |A + B/r^3|), monótono em r.
    """
    _, regioes = solucao_exata(camadas, H0)
    maximos = []
    for ri, ro, mu, A, B in regioes[1::2]:            # regiões ímpares = camadas
        cand = [abs(A - 2 * B / r**3) for r in (ri, ro)]
        cand += [abs(A + B / r**3) for r in (ri, ro)]
        maximos.append(mu * max(cand) / H0)
    return maximos


# ----------------------------------------------------------------- FEM
def _raios(cam, n, R):
    a0 = cam[0][0]
    partes = [np.linspace(0.0, a0, 8 * n + 1)]
    r = a0
    for a, b, _ in cam:
        if a > r:                                     # espaçamento (ar)
            partes.append(np.linspace(r, a, 4 * n + 1)[1:])
        partes.append(np.linspace(a, b, 8 * n + 1)[1:])
        r = b
    partes.append(np.geomspace(r, R, 24 * n + 1)[1:])
    return np.concatenate(partes)


def permeabilidade_por_raio(r, cam):
    """mu_r em cada raio r, segundo a lista de camadas."""
    mu = np.ones_like(np.asarray(r, dtype=float))
    for a, b, mu_k in cam:
        mu[(r > a) & (r < b)] = mu_k
    return mu


def resolver_multicamada(camadas, n=1, H0=1.0, R=None):
    """Resolve o problema; retorna (base FEM, psi, mu por elemento)."""
    cam = validar(camadas)
    R = R or 20 * cam[-1][1]
    m = malha_polar(_raios(cam, n, R), 90 * n)
    basis = Basis(m, ElementTriP2())
    rc = np.hypot(*m.p)[m.t].mean(axis=0)             # raio médio dos vértices
    mu = permeabilidade_por_raio(rc, cam)
    mu_qp = mu[:, None] * np.ones_like(basis.X[0])[None, :]
    A = asm(rigidez, basis, mu=mu_qp)
    D = basis.get_dofs(lambda x: np.hypot(x[0], x[1]) > 0.999 * R)
    psi = basis.zeros()
    psi[D] = -H0 * basis.doflocs[1, D]                # campo uniforme ao longe
    psi = solve(*condense(A, np.zeros_like(psi), x=psi, D=D))
    return basis, psi, mu


def campo_no_centro(basis, psi, a0):
    """H_z no centro da cavidade (campo interno uniforme)."""
    dz = 0.5 * a0
    v = basis.probes(np.array([[1e-6, 1e-6], [dz, -dz]])) @ psi
    return (v[1] - v[0]) / (2 * dz)                   # H_z = -d(psi)/dz


def inducao_por_camada(basis, psi, mu_elem, camadas):
    """Máximo de |B|/(mu0 H0) em cada camada, avaliado nos pontos de
    quadratura dos elementos (H0 = 1)."""
    cam = validar(camadas)
    g = np.asarray(basis.interpolate(psi).grad)       # (2, elementos, pontos)
    modulo = np.hypot(g[0], g[1]) * mu_elem[:, None]
    rc = np.hypot(*basis.mesh.p)[basis.mesh.t].mean(axis=0)
    return [float(modulo[(rc > a) & (rc < b)].max()) for a, b, _ in cam]


def fator_blindagem_multicamada(camadas, n=1, H0=1.0, R=None):
    cam = validar(camadas)
    basis, psi, _ = resolver_multicamada(cam, n, H0, R)
    return H0 / campo_no_centro(basis, psi, cam[0][0])


def simular_multicamada(camadas, n=1, H0=1.0, R=None):
    """Fator de blindagem (FEM) e indução máxima por camada, em um só solve."""
    cam = validar(camadas)
    basis, psi, mu = resolver_multicamada(cam, n, H0, R)
    sf = H0 / campo_no_centro(basis, psi, cam[0][0])
    return sf, inducao_por_camada(basis, psi, mu, cam)


def campo_meridional_multicamada(camadas, L=None, N=150, n=2, R=None):
    """Componentes Br e Bz (em unidades de B0) no semiplano rho >= 0."""
    cam = validar(camadas)
    L = L or 2 * cam[-1][1]
    basis, psi, _ = resolver_multicamada(cam, n, R=R)
    m = basis.mesh
    interp = LinearTriInterpolator(Triangulation(m.p[0], m.p[1], m.t.T),
                                   psi[basis.nodal_dofs[0]])
    h = L / N
    rho = (np.arange(N) + 0.5) * h                    # grade sem rho = 0
    z = np.linspace(-L, L, 2 * N + 1)
    RR, ZZ = np.meshgrid(rho, z)
    PSI = interp(RR, ZZ).filled(np.nan)
    dpsi_dz, dpsi_drho = np.gradient(PSI, z, rho)
    mu = permeabilidade_por_raio(np.hypot(RR, ZZ), cam)
    return rho, z, -mu * dpsi_drho, -mu * dpsi_dz


if __name__ == "__main__":
    fe = (18e-6, 70000.0)                             # FINEMET FT-3M, 1 lâmina
    co = (22e-6, 290000.0)                            # Metglas 2705M, 1 lâmina
    casos = {
        "1 casca (Passo 2)": [(0.09, 0.10, 1000.0)],
        "2 x 10 lâminas Fe encostadas": [(0.09, 0.09018, fe[1]), (0.09018, 0.09036, fe[1])],
        "2 x 10 lâminas Fe, 10 mm de espaço": [(0.09, 0.09018, fe[1]), (0.10018, 0.10036, fe[1])],
        "Fe-Fe-Co (10 lâminas cada)": [(0.09, 0.09022, co[1]), (0.09022, 0.0904, fe[1]),
                                       (0.0904, 0.09058, fe[1])],
    }
    for nome, cam in casos.items():
        exato = fator_exato_multicamada(cam)
        print(f"{nome}: SF exato = {exato:.3f}")
        for n in (1, 2):
            sf, bmax = simular_multicamada(cam, n=n)
            erro = 100 * (sf / exato - 1)
            print(f"   refino {n}: SF FEM = {sf:.3f}  erro = {erro:+.3f} %  "
                  f"|B|max/B0 por camada = {[round(b, 1) for b in bmax]}")
        print(f"   |B|max/B0 exato = {[round(b, 1) for b in inducao_exata_por_camada(cam)]}")
