"""Visualização didática da verificação da casca esférica.

Gera uma figura com quatro gráficos:
  (a) mapa de |B|/B0 com as linhas de campo desviadas pela casca;
  (b) perfil de |B|/B0 ao longo do plano equatorial;
  (c) fator de blindagem x permeabilidade (FEM e fórmula exata);
  (d) fator de blindagem x espessura (FEM e fórmula exata).

Uso:
    python modelos/verificacao/visualizar_casca_esferica.py
    python modelos/verificacao/visualizar_casca_esferica.py --sem-janela
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.patches import Circle
from matplotlib.tri import LinearTriInterpolator, Triangulation

from verificacao_casca_esferica import fator_blindagem, fator_exato, resolver

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "resultados" / "casca_esferica.png"

A, B, MU_R = 0.09, 0.10, 1000.0          # raios interno e externo (m)


def campo_no_plano(a, b, mu_r, L=0.2, N=150):
    """|B|/B0 e componentes no plano (x, z), espelhando a solução em rho."""
    basis, psi = resolver(a, b, mu_r, n=2)
    m = basis.mesh
    malha = Triangulation(m.p[0], m.p[1], m.t.T)
    interp = LinearTriInterpolator(malha, psi[basis.nodal_dofs[0]])
    h = L / N
    rho = (np.arange(N) + 0.5) * h                  # grade sem rho = 0
    z = np.linspace(-L, L, 2 * N + 1)
    RR, ZZ = np.meshgrid(rho, z)
    PSI = interp(RR, ZZ).filled(np.nan)              # psi nos pontos da grade
    dpsi_dz, dpsi_drho = np.gradient(PSI, z, rho)
    mu = np.where((np.hypot(RR, ZZ) > a) & (np.hypot(RR, ZZ) < b), mu_r, 1.0)
    Br, Bz = -mu * dpsi_drho, -mu * dpsi_dz          # B/B0, pois H0 = 1
    x = np.r_[-rho[::-1], rho]
    Bx = np.hstack([-Br[:, ::-1], Br])
    Bz = np.hstack([Bz[:, ::-1], Bz])
    return x, z, Bx, Bz


def grafico_mapa(ax, fig, x, z, Bx, Bz, sf):
    modulo = np.hypot(Bx, Bz)
    norma = LogNorm(vmin=1e-2, vmax=20)
    im = ax.pcolormesh(100 * x, 100 * z, modulo, norm=norma, cmap="magma",
                       shading="auto")
    largura = 0.3 + 1.2 * norma(np.clip(modulo, 1e-2, 20))
    ax.streamplot(100 * x, 100 * z, Bx, Bz, color="white", density=1.3,
                  linewidth=largura, arrowsize=0.7)
    for r in (A, B):
        ax.add_patch(Circle((0, 0), 100 * r, fill=False, color="cyan", lw=1))
    ax.text(0, 0, f"campo\n{sf:.0f}× menor", color="white", ha="center",
            va="center", fontsize=10, weight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="black", ec="none",
                      alpha=0.75))
    ax.set_aspect("equal")
    ax.set_xlabel("x (cm)")
    ax.set_ylabel("z (cm)")
    ax.set_title("(a) O metal desvia as linhas de campo")
    fig.colorbar(im, ax=ax, label="|B| / B₀ (escala logarítmica)")


def grafico_perfil(ax, x, z, Bx, Bz, sf):
    j = np.argmin(np.abs(z))                         # linha z = 0
    lado = x > 0
    modulo = np.hypot(Bx[j, lado], Bz[j, lado])
    ax.semilogy(100 * x[lado], modulo, color="tab:blue", lw=2)
    ax.axvspan(100 * A, 100 * B, color="gray", alpha=0.3,
               label="casca de metal")
    ax.axhline(1, ls="--", color="k", lw=1, label="campo aplicado B₀")
    ax.axhline(1 / sf, ls=":", color="tab:red", lw=1.5,
               label=f"campo interno = B₀/{sf:.0f}")
    ax.set_xlabel("distância ao centro, no equador (cm)")
    ax.set_ylabel("|B| / B₀")
    ax.set_title("(b) O fluxo se concentra no metal")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(True, which="both", alpha=0.3)


def grafico_permeabilidade(ax):
    mus = np.array([30, 100, 300, 1000, 3000, 10000])
    fem = [fator_blindagem(A, B, mu) for mu in mus]
    curva = np.logspace(1, 4.2, 200)
    ax.loglog(curva, fator_exato(A, B, curva), "k-", label="fórmula exata")
    ax.loglog(mus, fem, "o", color="tab:orange", ms=8,
              label="computador (FEM)")
    ax.set_xlabel("permeabilidade relativa µr")
    ax.set_ylabel("fator de blindagem")
    ax.set_title("(c) Mais permeabilidade, mais blindagem\n"
                 "(espessura de 1 cm)")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)


def grafico_espessura(ax):
    esp = np.array([0.25, 0.5, 1.0, 2.0, 3.0]) / 100          # m
    fem = [fator_blindagem(B - t, B, MU_R) for t in esp]
    curva = np.linspace(0.1, 3.2, 200) / 100
    ax.plot(100 * curva, fator_exato(B - curva, B, MU_R), "k-",
            label="fórmula exata")
    ax.plot(100 * esp, fem, "o", color="tab:orange", ms=8,
            label="computador (FEM)")
    ax.set_xlabel("espessura da casca (cm)")
    ax.set_ylabel("fator de blindagem")
    ax.set_title("(d) Mais espessura, mais blindagem\n(µr = 1000)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sem-janela", action="store_true",
                        help="só grava a figura, sem abrir a janela")
    args = parser.parse_args()

    print("Calculando o mapa de campo...")
    sf = fator_blindagem(A, B, MU_R, n=2)
    x, z, Bx, Bz = campo_no_plano(A, B, MU_R)
    print("Varrendo permeabilidade e espessura...")
    fig, eixos = plt.subplots(2, 2, figsize=(12, 10))
    grafico_mapa(eixos[0, 0], fig, x, z, Bx, Bz, sf)
    grafico_perfil(eixos[0, 1], x, z, Bx, Bz, sf)
    grafico_permeabilidade(eixos[1, 0])
    grafico_espessura(eixos[1, 1])
    fig.suptitle("Casca esférica de metal em campo magnético uniforme "
                 "(raios de 9 e 10 cm, µr = 1000)", fontsize=13)
    fig.tight_layout()
    SAIDA.parent.mkdir(exist_ok=True)
    fig.savefig(SAIDA, dpi=150)
    print(f"Figura gravada em {SAIDA}")
    if not args.sem_janela:
        plt.show()


if __name__ == "__main__":
    main()
