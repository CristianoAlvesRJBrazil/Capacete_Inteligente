"""Simulador didático de blindagem magnética: casca esférica multicamada.

Executar a partir da raiz do repositório:
    streamlit run interface/app_casca_esferica.py
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "modelos" / "verificacao"))

from capacete.materiais import carregar as carregar_materiais  # noqa: E402
from capacete.materiais import formatar_valor  # noqa: E402
from capacete.requisitos import carregar  # noqa: E402
from casca_multicamada import (campo_meridional_multicamada,  # noqa: E402
                               fator_exato_multicamada, simular_multicamada)
from visualizar_casca_esferica import grafico_mapa  # noqa: E402
from visualizar_casca_esferica_3d import CORTE, Campo, linhas_de_campo  # noqa: E402

N_GRADE = 300                      # pontos da grade de visualização por eixo
MAX_CAMADAS = 4
ESPESSURAS_MM = [0.1, 0.2, 0.5, 1, 2, 3, 5, 10, 20, 30]
PERMEABILIDADES = [1, 3, 10, 30, 100, 300, 1000, 1500, 3000, 10000, 30000,
                   64000, 100000]
ESPACAMENTOS_MM = [0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
PERSONALIZADO = "personalizado"
ROTULO = {"fe_nanocristalino": "Fe", "co_amorfo": "Co", "fe_amorfo": "FeA",
          "permalloy": "NiFe", "ferrita_mnzn": "MnZn", "aco_silicio": "FeSi",
          None: "P"}
FE, CO = "finemet_ft3m", "metglas_2705m"
PRESETS = {
    "Exemplo do Passo 2: 1 camada, µr = 1000, 10 mm":
        dict(a_cm=9.0, camadas=[dict(mat=PERSONALIZADO, mu=1000, t=10, rho=7.3)]),
    "1 camada: 10 lâminas de FINEMET FT-3M":
        dict(a_cm=9.0, camadas=[dict(mat=FE, lam=10)]),
    "1 camada: ferrita MnZn N87, placa de 3 mm":
        dict(a_cm=9.0, camadas=[dict(mat="ferrita_n87_tdk", t=3)]),
    "Ar (sem blindagem)":
        dict(a_cm=9.0, camadas=[dict(mat=PERSONALIZADO, mu=1, t=10, rho=0.0)]),
    "Fe–Co: FT-3M + Metglas 2705M (10 lâminas cada), encostadas":
        dict(a_cm=9.0, camadas=[dict(mat=FE, lam=10, gap=0.0), dict(mat=CO, lam=10)]),
    "Fe–Fe: 2 × 10 lâminas de FT-3M, encostadas":
        dict(a_cm=9.0, camadas=[dict(mat=FE, lam=10, gap=0.0), dict(mat=FE, lam=10)]),
    "Fe–Fe: 2 × 10 lâminas de FT-3M, 10 mm de espaçamento":
        dict(a_cm=9.0, camadas=[dict(mat=FE, lam=10, gap=10.0), dict(mat=FE, lam=10)]),
    "Fe–Fe–Co: FT-3M, FT-3M, Metglas 2705M (10 lâminas cada)":
        dict(a_cm=9.0, camadas=[dict(mat=FE, lam=10, gap=0.0), dict(mat=FE, lam=10, gap=0.0),
                                dict(mat=CO, lam=10)]),
    "Fe–Fe–Co–Co (10 lâminas cada)":
        dict(a_cm=9.0, camadas=[dict(mat=FE, lam=10, gap=0.0), dict(mat=FE, lam=10, gap=0.0),
                                dict(mat=CO, lam=10, gap=0.0), dict(mat=CO, lam=10)]),
    "MUMETALL: 2 cascas de 1 mm com 10 mm de espaçamento":
        dict(a_cm=9.0, camadas=[dict(mat="mumetall", lam=5, gap=10.0), dict(mat="mumetall", lam=5)]),
}
SEQUENCIAS = {"Fe–Co": "FC", "Fe–Fe": "FF", "Fe–Fe–Co": "FFC",
              "Fe–Fe–Co–Co": "FFCC", "Co–Fe (ordem invertida)": "CF"}

st.set_page_config(page_title="Simulador de blindagem", layout="wide")


def br(x, casas=1, sinal=False):
    """Número no formato brasileiro: 1.234,5."""
    texto = f"{x:{'+' if sinal else ''},.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


# ------------------------------------------------------------------ dados
@st.cache_resource(show_spinner=False)
def base_materiais():
    return carregar_materiais()


@st.cache_data(show_spinner=False)
def metas():
    reqs = carregar()
    return (reqs["campo_externo"].valor, reqs["campo_residual_passivo"].valor,
            reqs["campo_residual_final"].valor)


BASE = base_materiais()
B0_PADRAO, META_PASSIVA, META_FINAL = metas()


def camada_de_material(mid, perm_tipo, laminas=None, t_mm=None, gap_mm=0.0):
    """Descrição de uma camada feita de um material da base."""
    p = BASE.parametros_simulacao(mid, perm_tipo)
    v = p["valores"]
    if v["espessura_fita"] and laminas is not None:
        t_mm = laminas * v["espessura_fita"] / 1000
    else:
        laminas = None
    m = BASE.materiais[mid]
    return dict(material=mid, nome=m.nome, classe=m.classe, mu_r=v["mu_r"],
                densidade=v["densidade"], B_s=v["B_s"], t_mm=float(t_mm),
                laminas=laminas, espessura_fita=v["espessura_fita"],
                avisos=p["avisos"], registros=p["registros"], gap_mm=float(gap_mm))


def camada_personalizada(mu_r, t_mm, densidade, B_s=None, gap_mm=0.0):
    return dict(material=PERSONALIZADO, nome="Personalizado", classe=None,
                mu_r=float(mu_r), densidade=float(densidade), B_s=B_s or None,
                t_mm=float(t_mm), laminas=None, espessura_fita=None, avisos=[],
                registros=None, gap_mm=float(gap_mm))


def geometria(camadas, a_cm, gaps_mm=None):
    """Camadas listadas de fora para dentro -> raios de cada uma (m) e a
    lista (r_in, r_out, mu) de dentro para fora, usada pelos modelos."""
    n = len(camadas)
    raios = [None] * n
    r = a_cm / 100
    for k in range(n - 1, -1, -1):                  # de dentro para fora
        c = camadas[k]
        r_in, r_out = r, r + c["t_mm"] / 1000
        raios[k] = (r_in, r_out)
        gap = (gaps_mm[k - 1] if gaps_mm is not None else camadas[k - 1]["gap_mm"]) if k > 0 else 0.0
        r = r_out + gap / 1000
    geom = tuple((raios[k][0], raios[k][1], camadas[k]["mu_r"]) for k in range(n - 1, -1, -1))
    return raios, geom


def sequencia(camadas):
    return "–".join(ROTULO.get(c["classe"], "P") for c in camadas)


def massa_camada(c, raios):
    if not c["densidade"]:
        return None
    r_in, r_out = raios
    return 4 / 3 * np.pi * (r_out**3 - r_in**3) * c["densidade"] * 1000   # kg


# ------------------------------------------------------------------ cálculos
@st.cache_data(show_spinner=False)
def simular(geom, n):
    """Fator de blindagem (FEM) e |B|max/B0 por camada, de fora para dentro."""
    sf, bmax = simular_multicamada(list(geom), n=n)
    return float(sf), [float(b) for b in bmax[::-1]]


@st.cache_data(show_spinner=False)
def campo_visual(geom):
    """Campo para os gráficos.

    A grade de visualização não resolve camadas muito finas. Cada camada fina
    é desenhada com a espessura mínima visível e permeabilidade equivalente
    (mesmo produto µr x espessura), o que preserva o campo fora dela. Os
    espaçamentos são mantidos.
    """
    L = 2 * geom[-1][1]
    t_min = 3 * L / N_GRADE
    vis, r, b_anterior, ajustado = [], geom[0][0], geom[0][0], False
    for a, b, mu in geom:
        r_in = r + (a - b_anterior)
        t = b - a
        t_vis = max(t, t_min)
        vis.append((r_in, r_in + t_vis, mu * t / t_vis))
        ajustado |= t_vis > t
        r, b_anterior = r_in + t_vis, b
    rho, z, Br, Bz = campo_meridional_multicamada(vis, L=L, N=N_GRADE, n=2)
    return dict(rho=rho, z=z, Br=Br, Bz=Bz, vis=tuple(vis), L=L, t_min=t_min,
                ajustado=ajustado)


@st.cache_data(show_spinner=False)
def linhas(geom):
    c = campo_visual(geom)
    campo = Campo(c["rho"], c["z"], c["Br"], c["Bz"])
    passo = min(5e-4, c["t_min"] / 5)
    maximo = int(4 * campo.L / passo)
    n_ext = 14                                   # linhas de mesmo fluxo
    rho_ext = 0.85 * campo.L * np.sqrt((np.arange(n_ext) + 0.5) / n_ext)
    externas = linhas_de_campo(campo, rho_ext, z0=-0.975 * campo.L,
                               passo=passo, max_passos=maximo)
    internas = linhas_de_campo(campo, np.array([0.3, 0.6]) * c["vis"][0][0],
                               z0=0.0, passo=passo, max_passos=maximo)
    return externas, internas


# ------------------------------------------------------------------ gráficos
def limites_de_cor(c, sf):
    modulo = np.hypot(c["Br"], c["Bz"])
    return (min(1e-2, 0.3 / sf), max(20.0, float(np.nanpercentile(modulo, 99.9))))


def figura_mapa(c, sf, lim):
    rho, Br, Bz = c["rho"], c["Br"], c["Bz"]
    x = np.r_[-rho[::-1], rho]
    Bx = np.hstack([-Br[:, ::-1], Br])
    Bzz = np.hstack([Bz[:, ::-1], Bz])
    raios = sorted({r for a, b, _ in c["vis"] for r in (a, b)})
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    grafico_mapa(ax, fig, x, c["z"], Bx, Bzz, sf, raios=raios, limites=lim,
                 titulo="O metal desvia as linhas de campo")
    fig.tight_layout()
    return fig


def figura_perfil(c, sf, direcao):
    rho, z, Br, Bz = c["rho"], c["z"], c["Br"], c["Bz"]
    if direcao == "Equador (plano horizontal)":
        j = np.argmin(np.abs(z))
        pos, mod = rho, np.hypot(Br[j], Bz[j])
        rotulo, lados = "distância ao centro, no equador (cm)", (1,)
    else:
        pos, mod = z, np.hypot(Br[:, 0], Bz[:, 0])
        rotulo, lados = "posição no eixo vertical z (cm)", (1, -1)
    fig = go.Figure(go.Scatter(
        x=100 * pos, y=mod, mode="lines", line=dict(width=3),
        hovertemplate="posição %{x:.1f} cm<br>|B|/B₀ = %{y:.3g}<extra></extra>"))
    for a, b, _ in c["vis"]:
        for lado in lados:
            fig.add_vrect(x0=lado * 100 * a, x1=lado * 100 * b, fillcolor="gray",
                          opacity=0.3, line_width=0)
    for valor, texto, estilo, cor_ in ((1, "campo aplicado B₀", "dash", "black"),
                                       (1 / sf, f"campo interno = B₀/{sf:.0f}",
                                        "dot", "crimson")):
        fig.add_hline(y=valor, line_dash=estilo, line_color=cor_)
        fig.add_annotation(x=1, xref="paper", xanchor="right", y=np.log10(valor),
                           yshift=10, showarrow=False, text=texto,
                           font=dict(color=cor_))
    fig.update_yaxes(type="log", dtick=1, title="|B| / B₀ (escala logarítmica)")
    fig.update_xaxes(title=rotulo)
    fig.update_layout(height=480, margin=dict(t=30))
    return fig


def figura_3d(c, sf, externas, internas, lim):
    campo = Campo(c["rho"], c["z"], c["Br"], c["Bz"])
    cmin, cmax = np.log10(lim)

    def cor(rho, z):
        br_, bz_ = campo(rho, z)
        return np.log10(np.clip(np.hypot(br_, bz_), *lim))

    comum = dict(colorscale="Plasma", cmin=cmin, cmax=cmax, showscale=False,
                 hoverinfo="skip")
    fig = go.Figure()
    th = np.linspace(0, np.pi, 61)
    TH, PH = np.meshgrid(th, np.linspace(0, CORTE, 91))
    for a, b, _ in c["vis"]:
        rm = 0.5 * (a + b)                       # cor = campo no meio do metal
        cor_casca = cor(rm * np.sin(TH).ravel(), rm * np.cos(TH).ravel())
        for r in (a, b):
            fig.add_trace(go.Surface(
                x=100 * r * np.sin(TH) * np.cos(PH),
                y=100 * r * np.sin(TH) * np.sin(PH), z=100 * r * np.cos(TH),
                surfacecolor=cor_casca.reshape(TH.shape), **comum))
        RR, TT = np.meshgrid(np.linspace(a, b, 5), th)
        cor_face = cor((RR * np.sin(TT)).ravel(), (RR * np.cos(TT)).ravel())
        for phi in (0.0, CORTE):                 # faces do corte
            fig.add_trace(go.Surface(
                x=100 * RR * np.sin(TT) * np.cos(phi),
                y=100 * RR * np.sin(TT) * np.sin(phi), z=100 * RR * np.cos(TT),
                surfacecolor=cor_face.reshape(RR.shape), **comum))
    for grupo, largura in ((externas, 4), (internas, 3)):
        for phi in np.linspace(0, CORTE, 7):
            for lin in grupo:
                rho, z = lin[::3, 0], lin[::3, 1]
                fig.add_trace(go.Scatter3d(
                    x=100 * rho * np.cos(phi), y=100 * rho * np.sin(phi),
                    z=100 * z, mode="lines", showlegend=False, hoverinfo="skip",
                    line=dict(color=cor(rho, z), colorscale="Plasma",
                              cmin=cmin, cmax=cmax, width=largura)))
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0], mode="markers+text", showlegend=False,
        marker=dict(size=9, color="limegreen"),
        text=[f"região protegida: campo {sf:.0f}× menor"],
        textposition="top center", hoverinfo="skip"))
    L = 100 * campo.L
    seta = (-0.8 * L, -0.8 * L)
    fig.add_trace(go.Scatter3d(
        x=[seta[0]] * 2, y=[seta[1]] * 2, z=[-0.7 * L, -0.25 * L],
        mode="lines+text", text=["", "B₀ (campo aplicado)"],
        textposition="top center", line=dict(color="royalblue", width=8),
        showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Cone(
        x=[seta[0]], y=[seta[1]], z=[-0.25 * L], u=[0], v=[0], w=[1],
        sizemode="absolute", sizeref=0.12 * L, anchor="tail",
        colorscale=[[0, "royalblue"], [1, "royalblue"]], showscale=False,
        hoverinfo="skip"))
    ticks = [v for v in (1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100, 1000)
             if lim[0] <= v <= lim[1]]
    fig.add_trace(go.Scatter3d(
        x=[None], y=[None], z=[None], mode="markers", showlegend=False,
        hoverinfo="skip",
        marker=dict(colorscale="Plasma", cmin=cmin, cmax=cmax, color=[cmin],
                    showscale=True,
                    colorbar=dict(title="|B|/B₀", tickvals=np.log10(ticks),
                                  ticktext=[f"{v:g}" for v in ticks]))))
    fig.update_layout(
        height=720, margin=dict(l=0, r=0, t=10, b=0),
        scene=dict(aspectmode="data", xaxis_title="x (cm)", yaxis_title="y (cm)",
                   zaxis_title="z (cm)",
                   camera=dict(eye=dict(x=1.35, y=-1.35, z=0.75))))
    return fig


def figura_varredura(x, fem, exato_x, exato_y, atual, titulo_x, log_x, log_y=None):
    log_y = log_x if log_y is None else log_y
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=exato_x, y=exato_y, mode="lines",
                             name="fórmula exata", line=dict(color="black")))
    fig.add_trace(go.Scatter(x=x, y=fem, mode="markers", name="computador (FEM)",
                             marker=dict(size=10, color="darkorange")))
    fig.add_trace(go.Scatter(x=[atual[0]], y=[atual[1]], mode="markers",
                             name="sua simulação",
                             marker=dict(size=16, color="crimson", symbol="star")))
    fig.update_xaxes(title=titulo_x, **(dict(type="log", dtick=1) if log_x else {}))
    fig.update_yaxes(title="fator de blindagem",
                     **(dict(type="log", dtick=1) if log_y else {}))
    fig.update_layout(height=470, margin=dict(t=30),
                      legend=dict(orientation="h", x=0, y=-0.25))
    return fig


# ------------------------------------------------------------------ barra lateral
def nome_material(mid):
    return "Personalizado (escolher µr)" if mid == PERSONALIZADO else BASE.materiais[mid].nome


def aplicar_preset():
    p = PRESETS.get(st.session_state.preset)
    if not p:
        return
    ss = st.session_state
    ss.a_cm, ss.n_camadas = p["a_cm"], len(p["camadas"])
    for k, c in enumerate(p["camadas"], 1):
        ss[f"cam{k}_mat"] = c.get("mat", PERSONALIZADO)
        for chave in ("lam", "t", "mu", "rho", "bs", "gap"):
            if chave in c:
                ss[f"cam{k}_{chave}"] = c[chave]
    ss.cfg = None                                   # simula com os novos valores


def camada_dos_widgets(k, ultima):
    ss = st.session_state
    gap = 0.0 if ultima else float(ss[f"cam{k}_gap"])
    mid = ss[f"cam{k}_mat"]
    if mid == PERSONALIZADO:
        return camada_personalizada(ss[f"cam{k}_mu"], ss[f"cam{k}_t"],
                                    ss[f"cam{k}_rho"], ss[f"cam{k}_bs"], gap)
    return camada_de_material(mid, ss.perm_tipo, laminas=int(ss[f"cam{k}_lam"]),
                              t_mm=ss[f"cam{k}_t"], gap_mm=gap)


def ler_config():
    ss = st.session_state
    n = int(ss.n_camadas)
    return dict(a_cm=float(ss.a_cm), B0=float(ss.B0), n=int(ss.n),
                perm_tipo=ss.perm_tipo,
                camadas=[camada_dos_widgets(k, k == n) for k in range(1, n + 1)])


padroes = {"a_cm": 9.0, "B0": float(B0_PADRAO), "n": 2, "perm_tipo": "inicial",
           "n_camadas": 1, "preset": "Personalizado"}
for k in range(1, MAX_CAMADAS + 1):
    padroes.update({f"cam{k}_mat": PERSONALIZADO, f"cam{k}_lam": 10, f"cam{k}_t": 10,
                    f"cam{k}_mu": 1000, f"cam{k}_rho": 7.3, f"cam{k}_bs": 0.0,
                    f"cam{k}_gap": 0.0})
for chave, valor in padroes.items():
    st.session_state.setdefault(chave, valor)

materiais_ordenados = sorted(BASE.simulaveis(), key=lambda m: (m.classe, m.nome))
opcoes_material = [PERSONALIZADO] + [m.material_id for m in materiais_ordenados]

st.sidebar.header("Parâmetros")
st.sidebar.selectbox("Exemplos prontos", ["Personalizado"] + list(PRESETS),
                     key="preset", on_change=aplicar_preset)
st.sidebar.slider("Raio da cavidade (cm)", 5.0, 20.0, step=0.5, format="%.1f",
                  key="a_cm", help="Raio interno da camada mais interna: onde "
                  "ficam a cabeça e os sensores. As camadas são montadas para fora.")
st.sidebar.number_input("Campo externo B₀ (µT)", 1.0, 200.0, step=1.0, key="B0",
                        help="O projeto usa 90 µT como pior caso.")
st.sidebar.select_slider("Refino da malha", [1, 2, 4], key="n",
                         help="Multiplica o número de divisões da malha. Mais "
                              "refino = resultado mais preciso e mais lento.")
st.sidebar.radio("Permeabilidade dos materiais da base", ["inicial", "maxima"],
                 key="perm_tipo", horizontal=True,
                 format_func=lambda t: "inicial (conservadora)" if t == "inicial"
                 else "máxima (otimista)",
                 help="A permeabilidade inicial vale para campos muito baixos; a "
                      "máxima é atingida em campos maiores.")
st.sidebar.number_input("Número de camadas", 1, MAX_CAMADAS, step=1, key="n_camadas",
                        help="Camadas de fora para dentro, cada uma com seu "
                             "material, sua espessura e o espaçamento até a próxima.")
n_cam = int(st.session_state.n_camadas)
for k in range(1, n_cam + 1):
    posicao = ("externa" if k == 1 else "interna, junto à cavidade" if k == n_cam
               else "intermediária")
    with st.sidebar.container(border=True):
        st.markdown(f"**Camada {k}** ({posicao})")
        st.selectbox("Material", opcoes_material, key=f"cam{k}_mat",
                     format_func=nome_material)
        mid = st.session_state[f"cam{k}_mat"]
        if mid == PERSONALIZADO:
            st.select_slider("Permeabilidade relativa µr", PERMEABILIDADES,
                             key=f"cam{k}_mu")
            st.select_slider("Espessura (mm)", ESPESSURAS_MM, key=f"cam{k}_t")
            st.number_input("Densidade (g/cm³)", 0.0, 10.0, step=0.1,
                            key=f"cam{k}_rho")
            st.number_input("Indução de saturação Bs (T); 0 = desconhecida",
                            0.0, 2.5, step=0.05, format="%.2f", key=f"cam{k}_bs")
        else:
            fita = BASE.parametros_simulacao(mid, st.session_state.perm_tipo)
            esp = fita["valores"]["espessura_fita"]
            if esp:
                st.number_input("Número de lâminas", 1, 2000, step=1, key=f"cam{k}_lam",
                                help=f"Cada fita tem {br(esp, 0)} µm.")
                st.caption(f"Espessura: {br(st.session_state[f'cam{k}_lam'] * esp / 1000, 3)} mm")
            else:
                st.select_slider("Espessura (mm)", ESPESSURAS_MM, key=f"cam{k}_t")
        if k < n_cam:
            st.select_slider("Espaçamento até a próxima camada (mm)", ESPACAMENTOS_MM,
                             key=f"cam{k}_gap", help="Ar entre esta camada e a "
                             "seguinte, mais interna.")
if st.sidebar.button("Simular", type="primary", width="stretch"):
    st.session_state.cfg = ler_config()
if st.session_state.get("cfg") is None:
    st.session_state.cfg = ler_config()
cfg = st.session_state.cfg

# ------------------------------------------------------------------ página
st.title("Simulador de blindagem magnética: casca esférica multicamada")
st.caption("Passos 2 e 6 do guia do projeto. Monte as camadas na barra lateral e "
           "clique em **Simular**. O computador resolve o campo pelo método dos "
           "elementos finitos e compara com a solução exata para cascas "
           "concêntricas.")

camadas, B0 = cfg["camadas"], cfg["B0"]
raios, geom = geometria(camadas, cfg["a_cm"])
with st.spinner("Calculando o campo..."):
    sf, bmax = simular(geom, cfg["n"])
    exato = fator_exato_multicamada(list(geom))
    c = campo_visual(geom)

erro = 100 * (sf / exato - 1)
b_int = 1000 * B0 / sf                                     # nT
massas = [massa_camada(cam, r) for cam, r in zip(camadas, raios)]
massa_total = sum(massas) if all(m is not None for m in massas) else None
fracoes = [(B0 * 1e-6 * b / cam["B_s"]) if cam["B_s"] else None
           for cam, b in zip(camadas, bmax)]
pior = max((f for f in fracoes if f is not None), default=None)

st.markdown(f"**Sequência (de fora para dentro): {sequencia(camadas)}** — "
            f"cavidade de {br(cfg['a_cm'])} cm, raio externo de "
            f"{br(100 * geom[-1][1], 2)} cm")

col = st.columns(4)
col[0].metric("Fator de blindagem", br(sf), help="Quantas vezes o campo diminui "
              "no centro.")
col[1].metric("Solução exata", br(exato), help="Cascas concêntricas: matrizes "
              "de transferência.")
col[2].metric("Erro do computador", f"{br(erro, 3, sinal=True)} %",
              help="Diferença entre o FEM e a solução exata. Abaixo de 1% é bom.")
col[3].metric("Atenuação", f"{br(20 * np.log10(sf))} dB")
col = st.columns(4)
col[0].metric("Campo no centro", f"{br(b_int, 0)} nT",
              help=f"B₀ = {B0:g} µT dividido pelo fator de blindagem.")
col[1].metric("Massa do metal", f"{br(massa_total, 2)} kg" if massa_total is not None
              else "incompleta", help="Soma das camadas: volume vezes densidade.")
col[2].metric("Pior saturação", f"{br(100 * pior, 0)} %" if pior is not None else "sem dado",
              help="Maior razão entre a indução no metal e a saturação Bs entre "
                   "as camadas.")
col[3].metric("Camadas", f"{len(camadas)}")

NAN = float("nan")
tabela = []
for k, (cam, r, m, b, f) in enumerate(zip(camadas, raios, massas, bmax, fracoes), 1):
    tabela.append({
        "Camada": f"{k} ({'externa' if k == 1 else 'interna' if k == len(camadas) else 'meio'})",
        "Material": cam["nome"],
        "R interno (cm)": round(100 * r[0], 3), "Espessura (mm)": round(cam["t_mm"], 3),
        "Lâminas": cam["laminas"] if cam["laminas"] else NAN,
        "Espaço p/ dentro (mm)": cam["gap_mm"] if k < len(camadas) else NAN,
        "µr": round(cam["mu_r"]), "B máx (mT)": round(1000 * B0 * 1e-6 * b, 1),
        "Bs (T)": cam["B_s"] if cam["B_s"] else NAN,
        "Saturação (%)": round(100 * f) if f is not None else NAN,
        "Massa (kg)": round(m, 3) if m is not None else NAN})
st.dataframe(tabela, hide_index=True)
st.caption("B máx: maior indução dentro da camada (o metal concentra o fluxo). "
           "Células vazias: dado ausente na base (Bs, densidade) ou não aplicável.")

if abs(erro) > 1:
    st.warning("O erro está acima de 1%: aumente o **refino da malha**.")
for k, (cam, f) in enumerate(zip(camadas, fracoes), 1):
    if f is None:
        continue
    if f >= 1:
        st.error(f"A camada {k} ({cam['nome']}) **satura**: a indução no metal supera "
                 f"Bs. A blindagem real seria muito pior que a calculada. Use mais "
                 f"lâminas ou mais espessura nessa camada.")
    elif f > 0.5:
        st.warning(f"A camada {k} ({cam['nome']}) opera a {br(100 * f, 0)}% da "
                   f"saturação. A permeabilidade cai antes de saturar, e este modelo "
                   f"linear superestima a blindagem.")
if b_int <= META_FINAL:
    st.success(f"Campo no centro de {br(b_int, 0)} nT: abaixo da meta final de "
               f"{META_FINAL} nT só com a blindagem passiva.")
elif b_int <= META_PASSIVA:
    st.success(f"Campo no centro de {br(b_int, 0)} nT: atinge a meta passiva de "
               f"{META_PASSIVA} nT. As bobinas ainda precisariam reduzir "
               f"{br(b_int / META_FINAL)} vezes para chegar a {META_FINAL} nT.")
else:
    st.warning(f"Campo no centro de {br(b_int, 0)} nT: acima da meta passiva de "
               f"{META_PASSIVA} nT. Para {B0:g} µT, seria preciso um fator de "
               f"blindagem de pelo menos {1000 * B0 / META_PASSIVA:.0f}.")
st.info("Esta é uma **esfera fechada**, o caso ideal. No capacete, as aberturas "
        "para o rosto e o pescoço deixam o campo entrar e reduzem muito a "
        "blindagem; isso é estudado no Passo 5 do guia.")

if any(cam["registros"] for cam in camadas):
    with st.expander("Origem dos dados dos materiais"):
        origem = []
        for k, cam in enumerate(camadas, 1):
            if not cam["registros"]:
                continue
            for prop, reg in cam["registros"].items():
                if reg is None:
                    origem.append({"Camada": k, "Material": cam["nome"],
                                   "Propriedade": prop, "Valor": "sem dado"})
                    continue
                fonte = " ".join(BASE.fontes[reg.fonte_id]["referencia"].split())
                origem.append({"Camada": k, "Material": cam["nome"], "Propriedade": prop,
                               "Valor": f"{formatar_valor(reg)} {reg.unidade}",
                               "Condição": reg.condicao(), "Tipo": reg.tipo_dado,
                               "Fonte": fonte, "Onde na fonte": reg.localizacao,
                               "Registro": reg.id_registro})
            for aviso in cam["avisos"]:
                st.caption(f"⚠ Camada {k}: {aviso}")
        st.dataframe(origem, hide_index=True)
        st.caption("Os valores de ficha técnica são medidos em núcleos toroidais, em "
                   "condições que podem diferir das da blindagem. Os registros ainda "
                   "aguardam conferência por uma segunda pessoa.")

lim = limites_de_cor(c, sf)
abas = st.tabs(["Mapa do campo", "Perfil do campo", "Visão 3D",
                "Efeito dos parâmetros", "Comparar sequências", "Base de materiais",
                "Entenda e experimente"])

with abas[0]:
    esq, dir_ = st.columns([3, 2])
    fig = figura_mapa(c, sf, lim)
    esq.pyplot(fig)
    plt.close(fig)
    dir_.markdown(
        "**Como ler o mapa**\n\n"
        "- O corte mostra a esfera vista de lado; os círculos azuis são as faces "
        "de cada camada de metal.\n"
        "- As **cores** indicam a intensidade do campo em relação a B₀: claro é "
        "forte, escuro é fraco.\n"
        "- As **linhas brancas** mostram o caminho do campo. Elas são puxadas para "
        "dentro do metal e contornam a região central.\n"
        "- Com várias camadas, a mais externa recebe o campo pleno e as internas "
        "recebem só o que sobrou; por isso a externa é a mais clara.")
    if c["ajustado"]:
        dir_.caption(
            f"Camadas mais finas que {br(1000 * c['t_min'])} mm não aparecem na grade "
            f"do desenho. Nos gráficos, elas foram engrossadas até esse valor, com "
            f"permeabilidade equivalente (mesmo produto µr × espessura). Os números "
            f"acima são os da geometria real.")

with abas[1]:
    direcao = st.radio("Direção do perfil",
                       ["Equador (plano horizontal)", "Eixo vertical z"], horizontal=True)
    st.plotly_chart(figura_perfil(c, sf, direcao))
    st.markdown("As faixas cinza são as camadas de metal. Passe o mouse sobre a curva "
                "para ler os valores. Dentro da cavidade, o campo é uniforme e igual a "
                "B₀ dividido pelo fator de blindagem; em cada camada, o campo é maior "
                "que fora dela, porque o fluxo se concentra no metal.")

with abas[2]:
    with st.spinner("Traçando as linhas de campo em 3D..."):
        externas, internas = linhas(geom)
    st.plotly_chart(figura_3d(c, sf, externas, internas, lim))
    st.caption("Arraste para girar, use a roda do mouse para aproximar. As cascas têm "
               "uma fatia removida para mostrar o interior. Cada linha externa "
               "transporta a mesma quantidade de fluxo: quase nenhuma atravessa a "
               "cavidade. As linhas escuras dentro dela mostram o campo interno, "
               "fraco e uniforme.")

with abas[3]:
    if len(camadas) == 1:
        st.markdown("Calcula o fator de blindagem para vários valores de permeabilidade "
                    "e de espessura da camada única, mantendo o restante. Pode levar "
                    "de 10 a 60 segundos, conforme o refino.")
    else:
        st.markdown("Calcula o fator de blindagem para vários **espaçamentos** entre as "
                    "camadas (todos iguais), mantendo materiais e espessuras. É o "
                    "efeito central do Passo 6: camadas separadas por ar blindam muito "
                    "mais que camadas encostadas.")
    if st.button("Calcular as curvas", type="primary"):
        st.session_state.curvas = True
    if st.session_state.get("curvas"):
        a_m, cam = cfg["a_cm"] / 100, camadas[0]
        if len(camadas) == 1:
            e1, e2 = st.columns(2)
            with st.spinner("Variando a permeabilidade..."):
                mus = [mu for mu in PERMEABILIDADES if mu >= 10]
                fem = [simular(geometria([dict(cam, mu_r=mu)], cfg["a_cm"])[1], cfg["n"])[0]
                       for mu in mus]
            mx = np.logspace(1, 5, 200)
            b_m = a_m + cam["t_mm"] / 1000
            e1.plotly_chart(figura_varredura(
                mus, fem, mx, [fator_exato_multicamada([(a_m, b_m, mu)]) for mu in mx],
                (cam["mu_r"], sf), "permeabilidade relativa µr", log_x=True))
            with st.spinner("Variando a espessura..."):
                esp = [t for t in ESPESSURAS_MM]
                fem_t = [simular(geometria([dict(cam, t_mm=t)], cfg["a_cm"])[1], cfg["n"])[0]
                         for t in esp]
            tx = np.linspace(min(esp), max(esp), 200)
            e2.plotly_chart(figura_varredura(
                esp, fem_t, tx, [fator_exato_multicamada([(a_m, a_m + t / 1000, cam["mu_r"])])
                                 for t in tx],
                (cam["t_mm"], sf), "espessura do metal (mm)", log_x=False))
        else:
            with st.spinner("Variando o espaçamento..."):
                gaps = [0, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30]
                fem_g = [simular(geometria(camadas, cfg["a_cm"], [g] * (len(camadas) - 1))[1],
                                 cfg["n"])[0] for g in gaps]
            gx = np.linspace(0, 30, 121)
            exato_g = [fator_exato_multicamada(
                list(geometria(camadas, cfg["a_cm"], [g] * (len(camadas) - 1))[1]))
                for g in gx]
            gap_atual = camadas[0]["gap_mm"]
            st.plotly_chart(figura_varredura(
                gaps, fem_g, gx, exato_g, (gap_atual, sf),
                "espaçamento entre as camadas (mm)", log_x=False, log_y=True))
            st.markdown("Para duas cascas, a aproximação clássica é "
                        "SF ≈ SF₁ · SF₂ · [1 − (R₂/R₁)³]: o termo entre colchetes é "
                        "quase zero quando as cascas se encostam e cresce com o "
                        "espaçamento.")

with abas[4]:
    st.markdown("Compara as sequências do projeto na **mesma cavidade**, com os mesmos "
                "materiais, o mesmo número de lâminas por camada e o mesmo espaçamento. "
                "As colunas de saturação mostram qual camada concentra mais fluxo.")
    fe_ids = [m.material_id for m in materiais_ordenados if m.classe == "fe_nanocristalino"
              and BASE.registros_de(m.material_id, "espessura_fita")]
    co_ids = [m.material_id for m in materiais_ordenados if m.classe == "co_amorfo"
              and BASE.registros_de(m.material_id, "espessura_fita")]
    c1, c2, c3, c4 = st.columns(4)
    fe_id = c1.selectbox("Fita Fe", fe_ids, index=fe_ids.index(FE) if FE in fe_ids else 0,
                         format_func=nome_material)
    co_id = c2.selectbox("Fita Co", co_ids, index=co_ids.index(CO) if CO in co_ids else 0,
                         format_func=nome_material)
    lam_seq = c3.number_input("Lâminas por camada", 1, 500, 10, step=1)
    gap_seq = c4.select_slider("Espaçamento (mm)", ESPACAMENTOS_MM, value=0.0)
    if st.button("Comparar", type="primary"):
        st.session_state.comparar = True
    if st.session_state.get("comparar"):
        linhas_seq, nomes, sfs = [], [], []
        with st.spinner("Simulando as sequências..."):
            for nome, codigo in SEQUENCIAS.items():
                cams = [camada_de_material(fe_id if ch == "F" else co_id, cfg["perm_tipo"],
                                           laminas=lam_seq, gap_mm=gap_seq)
                        for ch in codigo]
                cams[-1]["gap_mm"] = 0.0
                r_seq, g_seq = geometria(cams, cfg["a_cm"])
                sf_seq, b_seq = simular(g_seq, cfg["n"])
                ex_seq = fator_exato_multicamada(list(g_seq))
                m_seq = [massa_camada(cm, r) for cm, r in zip(cams, r_seq)]
                f_seq = [(B0 * 1e-6 * b / cm["B_s"]) if cm["B_s"] else None
                         for cm, b in zip(cams, b_seq)]
                validas = [f for f in f_seq if f is not None]
                pior_k = (f_seq.index(max(validas)) + 1) if validas else None
                linhas_seq.append({
                    "Sequência": nome, "Fator de blindagem (FEM)": round(sf_seq, 1),
                    "Solução exata": round(ex_seq, 1),
                    "Campo no centro (nT)": round(1000 * B0 / sf_seq),
                    "Massa (kg)": round(sum(m_seq), 3) if all(m is not None for m in m_seq) else NAN,
                    "Pior saturação (%)": round(100 * max(validas)) if validas else NAN,
                    "Camada que mais satura": pior_k if pior_k else NAN})
                nomes.append(nome)
                sfs.append(sf_seq)
        st.dataframe(linhas_seq, hide_index=True)
        fig = go.Figure(go.Bar(x=nomes, y=sfs, marker_color="darkorange",
                               text=[br(s) for s in sfs], textposition="outside"))
        fig.update_yaxes(title="fator de blindagem", type="log")
        fig.update_layout(height=400, margin=dict(t=30))
        st.plotly_chart(fig)
        st.caption("Modelo linear: a permeabilidade não cai com o campo, por isso "
                   "inverter a ordem das camadas quase não muda o fator. A vantagem "
                   "real de pôr o Fe (maior Bs) por fora aparece em campos fortes, "
                   "quando a permeabilidade cai antes de saturar; isso exige o modelo "
                   "não linear da Fase 3. Quando a saturação passa de 50%, o resultado "
                   "real é pior que o mostrado.")

with abas[5]:
    st.markdown(f"A base tem **{len(BASE.materiais)} materiais** e "
                f"**{len(BASE.registros)} registros**, cada um com fonte, condição de "
                "medição e localização na fonte. A tabela mostra o valor escolhido pelo "
                "simulador: menor frequência disponível e, no empate, o valor mais "
                "conservador.")
    tab_base = []
    for m in sorted(BASE.materiais.values(), key=lambda m: (m.classe, m.nome)):
        def valor(*props, _m=m):
            return formatar_valor(BASE.escolher(_m.material_id, props))
        tab_base.append({"Material": m.nome, "Classe": m.classe,
                         "µr inicial": valor("mu_r_inicial", "mu_r"),
                         "µr máxima": valor("mu_r_max"), "Bs (T)": valor("B_s"),
                         "Densidade (g/cm³)": valor("densidade"),
                         "Fita (µm)": valor("espessura_fita"), "Fonte": m.fonte_principal})
    st.dataframe(tab_base, hide_index=True, height=560)
    st.caption("— indica lacuna na base. Os arquivos ficam em `materiais/` e o relatório "
               "de cobertura em `docs/materiais_cobertura.md`.")

with abas[6]:
    st.markdown(f"""
### O que está sendo simulado
Uma ou mais cascas esféricas de metal, concêntricas, são colocadas num campo
magnético uniforme. O computador divide o espaço em milhares de pequenos
triângulos (a **malha**) e calcula o campo em cada um deles: é o **método dos
elementos finitos (FEM)**. Para cascas concêntricas existe uma solução exata, e o
simulador compara os dois resultados em toda simulação. Essa conferência se chama
**verificação**.

### Os parâmetros
- **Permeabilidade relativa (µr):** quanto o material conduz o campo. Quanto maior,
  mais o metal "puxa" as linhas de campo para si e menos campo sobra no centro.
- **Espessura ou número de lâminas:** mais metal oferece um caminho mais largo
  para o campo, e também reduz a indução dentro dele (menos risco de saturação).
- **Espaçamento:** camadas encostadas somam espessura; camadas separadas por ar
  multiplicam seus fatores. Para duas cascas, SF ≈ SF₁ · SF₂ · [1 − (R₂/R₁)³].
- **Ordem das camadas:** a externa recebe o campo pleno; por isso o material de
  maior saturação (Fe) fica fora, e o de maior permeabilidade (Co), dentro.
- **Refino da malha:** triângulos menores dão resultados mais precisos, mas o
  cálculo demora mais.
- **Campo externo B₀:** não muda o fator de blindagem, mas muda o campo que sobra no
  centro e a indução no metal. O projeto usa {B0_PADRAO} µT como pior caso, com
  metas de {META_PASSIVA} nT depois da blindagem e {META_FINAL} nT depois das
  bobinas.
""")
    st.markdown("### Experimente")
    exercicios = [
        ("Escolha o *Exemplo do Passo 2* e dobre a espessura de 10 para 20 mm. O fator "
         "de blindagem também dobra?",
         "Não. Ele passa de 61 para 101: aumenta, mas menos que o dobro, porque a "
         "camada extra fica mais longe do centro."),
        ("Volte para 10 mm e aumente µr de 1.000 para 10.000. Quantas vezes o fator "
         "aumenta?",
         "Cerca de 10 vezes (de 61 para 603). Para cascas de alta permeabilidade, o "
         "fator é quase proporcional a µr."),
        ("Escolha *1 camada: 10 lâminas de FINEMET FT-3M* e depois mude para 1 lâmina. "
         "Observe a coluna de saturação.",
         "Com 1 lâmina de 18 µm, a indução no metal chega a cerca de 55% da "
         "saturação: o modelo linear deixa de valer. Com 10 lâminas, cai para "
         "cerca de 5%."),
        ("Monte *Fe–Fe: 2 × 10 lâminas, encostadas* e compare com 1 camada de 20 "
         "lâminas.",
         "O resultado é o mesmo (fator 186): camadas encostadas do mesmo material "
         "são uma camada mais grossa."),
        ("Agora escolha *Fe–Fe com 10 mm de espaçamento*. O que acontece?",
         "O fator salta de 186 para cerca de 2.280, mais de dez vezes. Cada camada "
         "blinda o campo que a outra deixou passar; o espaçamento é a variável mais "
         "poderosa deste simulador."),
        ("Na aba *Comparar sequências*, compare Fe–Co com Co–Fe. O fator muda? Qual "
         "camada concentra mais fluxo em cada caso?",
         "No modelo linear o fator é o mesmo (562): só os raios mudam, e muito pouco. "
         "Nos dois casos quem mais satura é a camada de Co, por dentro ou por fora, "
         "porque seu produto µr × espessura é quase cinco vezes o da fita de Fe e "
         "ela puxa o fluxo para si. A razão para pôr o Fe por fora, no projeto, é "
         "outra: em campos fortes a permeabilidade cai antes de saturar, e o Fe, "
         "com Bs maior, aguenta mais. Esse efeito só aparece no modelo não linear "
         "da Fase 3."),
        (f"Com B₀ = {B0_PADRAO} µT, encontre uma montagem que leve o campo no centro "
         f"abaixo de {META_PASSIVA} nT sem nenhuma camada acima de 50% da saturação.",
         f"É preciso fator de pelo menos {1000 * B0_PADRAO / META_PASSIVA:.0f}. Duas "
         f"camadas de 10 lâminas com 10 mm de espaçamento já passam de 2.000, com "
         f"saturação baixa. Lembre-se de que a esfera fechada é o caso ideal."),
    ]
    for i, (pergunta, resposta) in enumerate(exercicios, 1):
        st.markdown(f"**{i}.** {pergunta}")
        with st.expander("Ver resposta"):
            st.markdown(resposta)
