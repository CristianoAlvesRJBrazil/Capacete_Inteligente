"""Visualização 3D interativa da verificação da casca esférica (PyVista).

Mostra:
  - a casca de metal com um corte, colorida pela intensidade |B|/B0;
  - as linhas de campo em 3D, desviadas pela casca;
  - a região protegida no centro, onde ficariam os sensores.

Na janela: girar = arrastar com o botão esquerdo; zoom = roda do mouse;
mover = Shift + botão esquerdo; fechar = tecla q.

Uso:
    python modelos/verificacao/visualizar_casca_esferica_3d.py
    python modelos/verificacao/visualizar_casca_esferica_3d.py --sem-janela
"""
import argparse
from pathlib import Path

import numpy as np
import pyvista as pv
from scipy.interpolate import RegularGridInterpolator

from verificacao_casca_esferica import fator_blindagem
from visualizar_casca_esferica import A, B, MU_R, campo_meridional

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "resultados" / "casca_esferica_3d.png"
L = 0.2                     # meia-largura da região visualizada (m)
CORTE = 1.5 * np.pi         # a casca cobre phi de 0 a 270 graus
ESCALA = dict(cmap="plasma", log_scale=True, clim=[1e-2, 20])


class Campo:
    """B/B0 em qualquer ponto (rho, z), a partir da solução axissimétrica."""

    def __init__(self, rho, z, Br, Bz):
        self.L = z[-1]                            # meia-largura da grade
        self.rho_lim = (rho[0], rho[-1])
        self.fr = RegularGridInterpolator((z, rho), Br)
        self.fz = RegularGridInterpolator((z, rho), Bz)

    @classmethod
    def calcular(cls, a, b, mu_r, L=L, N=300):
        return cls(*campo_meridional(a, b, mu_r, L=L, N=N))

    def __call__(self, rho, z):
        pts = np.column_stack([np.clip(z, -self.L, self.L),
                               np.clip(np.abs(rho), *self.rho_lim)])
        return self.fr(pts), self.fz(pts)


def linhas_de_campo(campo, rho0, z0, passo=5e-4, max_passos=4000):
    """Linhas de B no semiplano meridional, integradas por Runge-Kutta 4.

    Cada linha é integrada nos dois sentidos a partir de (rho0, z0) até
    sair da região visualizada.
    """
    def direcao(q, sentido):
        br, bz = campo(q[:, 0], q[:, 1])
        norma = np.hypot(br, bz) + 1e-30
        return sentido * np.column_stack([br / norma, bz / norma])

    metades = []
    for sentido in (1.0, -1.0):
        p = np.column_stack([rho0, np.full(len(rho0), z0)]).astype(float)
        caminhos = [[q.copy()] for q in p]
        ativo = np.ones(len(p), bool)
        for _ in range(max_passos):
            if not ativo.any():
                break
            q = p[ativo]
            k1 = direcao(q, sentido)
            k2 = direcao(q + 0.5 * passo * k1, sentido)
            k3 = direcao(q + 0.5 * passo * k2, sentido)
            k4 = direcao(q + passo * k3, sentido)
            p[ativo] = q + passo / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            for i in np.flatnonzero(ativo):
                caminhos[i].append(p[i].copy())
            fora = ((np.abs(p[:, 1]) > 0.98 * campo.L)
                    | (p[:, 0] > 0.98 * campo.L))
            ativo &= ~fora
        metades.append(caminhos)
    return [np.vstack([np.array(tras)[::-1], np.array(frente)[1:]])
            for frente, tras in zip(*metades)]


def linhas_3d(campo, linhas, angulos):
    """Gira as linhas meridionais em torno do eixo z e monta os tubos."""
    blocos = []
    for phi in angulos:
        for lin in linhas:
            rho, z = lin[:, 0], lin[:, 1]
            pts = np.column_stack([rho * np.cos(phi), rho * np.sin(phi), z])
            poli = pv.lines_from_points(pts)
            br, bz = campo(rho, z)
            poli["|B| / B0"] = np.hypot(br, bz)
            blocos.append(poli)
    return pv.merge(blocos).tube(radius=0.0012, n_sides=10)


def casca_cortada(campo, a, b):
    """Casca sólida sem a fatia de 270 a 360 graus, colorida pelo campo
    no interior do metal."""
    r = np.linspace(a, b, 6)
    th = np.linspace(0, np.pi, 121)
    ph = np.linspace(0, CORTE, 181)
    R, TH, PH = np.meshgrid(r, th, ph, indexing="ij")
    grade = pv.StructuredGrid(R * np.sin(TH) * np.cos(PH),
                              R * np.sin(TH) * np.sin(PH), R * np.cos(TH))
    sup = grade.extract_surface(algorithm="dataset_surface")
    x, y, z = sup.points.T
    # cor = campo no meio da espessura do metal, na mesma direção do ponto
    escala = 0.5 * (a + b) / np.sqrt(x**2 + y**2 + z**2)
    br, bz = campo(np.hypot(x, y) * escala, z * escala)
    sup["|B| / B0"] = np.hypot(br, bz)
    return sup


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sem-janela", action="store_true",
                        help="só grava a imagem, sem abrir a janela")
    args = parser.parse_args()

    print("Calculando o campo...")
    sf = fator_blindagem(A, B, MU_R, n=2)
    campo = Campo.calcular(A, B, MU_R)

    print("Traçando as linhas de campo...")
    n_ext = 14                                   # linhas de mesmo fluxo
    rho_ext = 0.17 * np.sqrt((np.arange(n_ext) + 0.5) / n_ext)
    externas = linhas_de_campo(campo, rho_ext, z0=-0.195)
    internas = linhas_de_campo(campo, np.array([0.03, 0.06]), z0=0.0)
    angulos = np.linspace(0, CORTE, 7)

    print("Montando a cena 3D...")
    p = pv.Plotter(off_screen=args.sem_janela, window_size=(1300, 1000))
    p.set_background("white", top="lightsteelblue")
    p.add_mesh(casca_cortada(campo, A, B), scalars="|B| / B0",
               smooth_shading=True, show_scalar_bar=False, **ESCALA)
    p.add_mesh(linhas_3d(campo, externas, angulos), scalars="|B| / B0",
               show_scalar_bar=False, **ESCALA)
    p.add_mesh(linhas_3d(campo, internas, angulos), scalars="|B| / B0",
               scalar_bar_args=dict(title="intensidade B/B0", vertical=True,
                                    position_x=0.88, position_y=0.25,
                                    height=0.5, color="black"), **ESCALA)
    p.add_mesh(pv.Sphere(radius=0.015, center=(0, 0, 0)), color="limegreen")
    p.add_point_labels([[0, 0, 0.02]], [f"região protegida: campo {sf:.0f}x menor"],
                       font_size=16, text_color="black", shape_color="white",
                       shape_opacity=0.8, always_visible=True)
    p.add_mesh(pv.Arrow(start=(-0.21, -0.21, -0.13), direction=(0, 0, 1),
                        scale=0.12), color="royalblue")
    p.add_point_labels([[-0.21, -0.21, 0.01]], ["B0 (campo aplicado)"],
                       font_size=14, text_color="royalblue",
                       shape_opacity=0.0, always_visible=True)
    p.add_text("Casca esférica de metal em campo uniforme\n"
               "raios de 9 e 10 cm, permeabilidade relativa 1000",
               position="upper_left", font_size=12, color="black")
    p.add_text("Girar: botão esquerdo   Zoom: roda do mouse   "
               "Mover: Shift + botão esquerdo   Sair: q",
               position="lower_left", font_size=9, color="dimgray")
    p.add_axes(color="black")
    p.camera_position = [(0.62, -0.62, 0.38), (0, 0, 0), (0, 0, 1)]

    SAIDA.parent.mkdir(exist_ok=True)
    if args.sem_janela:
        p.screenshot(SAIDA)
    else:
        p.show(screenshot=SAIDA)
    print(f"Imagem gravada em {SAIDA}")


if __name__ == "__main__":
    main()
