"""Simulador didático de blindagem magnética: casca esférica (Streamlit).

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

from capacete.requisitos import carregar  # noqa: E402
from verificacao_casca_esferica import fator_blindagem, fator_exato  # noqa: E402
from visualizar_casca_esferica import campo_meridional, grafico_mapa  # noqa: E402
from visualizar_casca_esferica_3d import CORTE, Campo, linhas_de_campo  # noqa: E402

N_GRADE = 300                      # pontos da grade de visualização por eixo
ESPESSURAS_MM = [0.1, 0.2, 0.5, 1, 2, 3, 5, 10, 20, 30]
PERMEABILIDADES = [1, 3, 10, 30, 100, 300, 1000, 1500, 3000, 10000, 30000,
                   64000, 100000]
EXEMPLOS = {
    "Exemplo do Passo 2 (µr = 1000, 1 cm)": dict(b=10.0, t=10, mu=1000),
    "Fita Fe nanocristalina: 10 lâminas de 20 µm": dict(b=10.0, t=0.2,
                                                         mu=64000),
    "Ferrita MnZn, placa de 3 mm": dict(b=10.0, t=3, mu=1500),
    "Ar (sem blindagem)": dict(b=10.0, t=10, mu=1),
}

st.set_page_config(page_title="Simulador de blindagem", layout="wide")


def br(x, casas=1, sinal=False):
    """Número no formato brasileiro: 1.234,5."""
    texto = f"{x:{'+' if sinal else ''},.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


# ------------------------------------------------------------------ cálculos
@st.cache_data(show_spinner=False)
def metas():
    reqs = carregar()
    return (reqs["campo_externo"].valor, reqs["campo_residual_passivo"].valor,
            reqs["campo_residual_final"].valor)


@st.cache_data(show_spinner=False)
def simular(b_cm, t_mm, mu_r, n):
    b = b_cm / 100
    return fator_blindagem(b - t_mm / 1000, b, mu_r, n=n, R=20 * b)


@st.cache_data(show_spinner=False)
def campo_visual(b_cm, t_mm, mu_r):
    """Campo para os gráficos.

    A grade de visualização não resolve cascas muito finas. Nesse caso, a
    casca é desenhada com a espessura mínima visível e permeabilidade
    equivalente (mesmo produto µr x espessura), o que preserva o campo
    dentro e fora dela.
    """
    b, t = b_cm / 100, t_mm / 1000
    L = 2 * b
    t_vis = max(t, 3 * L / N_GRADE)
    mu_vis = max(mu_r * t / t_vis, 1.0)
    rho, z, Br, Bz = campo_meridional(b - t_vis, b, mu_vis, L=L, N=N_GRADE,
                                      n=2, R=20 * b)
    return dict(rho=rho, z=z, Br=Br, Bz=Bz, a=b - t_vis, b=b,
                t_vis=t_vis, mu_vis=mu_vis, ajustado=t_vis > t)


@st.cache_data(show_spinner=False)
def linhas(b_cm, t_mm, mu_r):
    c = campo_visual(b_cm, t_mm, mu_r)
    campo = Campo(c["rho"], c["z"], c["Br"], c["Bz"])
    passo = min(5e-4, c["t_vis"] / 5)
    maximo = int(4 * campo.L / passo)
    n_ext = 14                                   # linhas de mesmo fluxo
    rho_ext = 0.85 * campo.L * np.sqrt((np.arange(n_ext) + 0.5) / n_ext)
    externas = linhas_de_campo(campo, rho_ext, z0=-0.975 * campo.L,
                               passo=passo, max_passos=maximo)
    internas = linhas_de_campo(campo, np.array([0.3, 0.6]) * c["a"], z0=0.0,
                               passo=passo, max_passos=maximo)
    return externas, internas


@st.cache_data(show_spinner=False)
def varrer_permeabilidade(b_cm, t_mm, n):
    mus = [mu for mu in PERMEABILIDADES if mu >= 10]
    return mus, [simular(b_cm, t_mm, mu, n) for mu in mus]


@st.cache_data(show_spinner=False)
def varrer_espessura(b_cm, mu_r, n):
    esp = [t for t in ESPESSURAS_MM if t < 0.6 * b_cm * 10]
    return esp, [simular(b_cm, t, mu_r, n) for t in esp]


# ------------------------------------------------------------------ gráficos
def limites_de_cor(c, sf):
    """Faixa de cores: do campo interno ao campo no metal (~1,5 b/t)."""
    return (min(1e-2, 0.3 / sf), max(20.0, 3 * c["b"] / c["t_vis"]))


def figura_mapa(c, sf, lim):
    rho, Br, Bz = c["rho"], c["Br"], c["Bz"]
    x = np.r_[-rho[::-1], rho]
    Bx = np.hstack([-Br[:, ::-1], Br])
    Bzz = np.hstack([Bz[:, ::-1], Bz])
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    grafico_mapa(ax, fig, x, c["z"], Bx, Bzz, sf, raios=(c["a"], c["b"]),
                 limites=lim, titulo="O metal desvia as linhas de campo")
    fig.tight_layout()
    return fig


def figura_perfil(c, sf, direcao):
    rho, z, Br, Bz = c["rho"], c["z"], c["Br"], c["Bz"]
    if direcao == "Equador (plano horizontal)":
        j = np.argmin(np.abs(z))
        pos, mod = rho, np.hypot(Br[j], Bz[j])
        rotulo = "distância ao centro, no equador (cm)"
    else:
        pos, mod = z, np.hypot(Br[:, 0], Bz[:, 0])
        rotulo = "posição no eixo vertical z (cm)"
    fig = go.Figure(go.Scatter(
        x=100 * pos, y=mod, mode="lines", line=dict(width=3),
        hovertemplate="posição %{x:.1f} cm<br>|B|/B₀ = %{y:.3g}<extra></extra>"))
    for lado in ((1, -1) if direcao != "Equador (plano horizontal)" else (1,)):
        fig.add_vrect(x0=lado * 100 * c["a"], x1=lado * 100 * c["b"],
                      fillcolor="gray", opacity=0.3, line_width=0)
    for valor, texto, estilo, cor_ in ((1, "campo aplicado B₀", "dash", "black"),
                                       (1 / sf, f"campo interno = B₀/{sf:.0f}",
                                        "dot", "crimson")):
        fig.add_hline(y=valor, line_dash=estilo, line_color=cor_)
        fig.add_annotation(x=1, xref="paper", xanchor="right",
                           y=np.log10(valor), yshift=10, showarrow=False,
                           text=texto, font=dict(color=cor_))
    fig.update_yaxes(type="log", dtick=1, title="|B| / B₀ (escala logarítmica)")
    fig.update_xaxes(title=rotulo)
    fig.update_layout(height=480, margin=dict(t=30))
    return fig


def figura_3d(c, sf, externas, internas, lim):
    campo = Campo(c["rho"], c["z"], c["Br"], c["Bz"])
    a, b = c["a"], c["b"]
    cmin, cmax = np.log10(lim)

    def cor(rho, z):
        br, bz = campo(rho, z)
        return np.log10(np.clip(np.hypot(br, bz), *lim))

    comum = dict(colorscale="Plasma", cmin=cmin, cmax=cmax, showscale=False,
                 hoverinfo="skip")
    fig = go.Figure()
    th = np.linspace(0, np.pi, 61)
    TH, PH = np.meshgrid(th, np.linspace(0, CORTE, 91))
    rm = 0.5 * (a + b)                          # cor = campo no meio do metal
    cor_casca = cor(rm * np.sin(TH).ravel(), rm * np.cos(TH).ravel())
    for r in (a, b):
        fig.add_trace(go.Surface(
            x=100 * r * np.sin(TH) * np.cos(PH),
            y=100 * r * np.sin(TH) * np.sin(PH), z=100 * r * np.cos(TH),
            surfacecolor=cor_casca.reshape(TH.shape), **comum))
    RR, TT = np.meshgrid(np.linspace(a, b, 5), th)
    cor_face = cor((RR * np.sin(TT)).ravel(), (RR * np.cos(TT)).ravel())
    for phi in (0.0, CORTE):                    # faces do corte
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
                    z=100 * z, mode="lines", showlegend=False,
                    hoverinfo="skip",
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
        scene=dict(aspectmode="data", xaxis_title="x (cm)",
                   yaxis_title="y (cm)", zaxis_title="z (cm)",
                   camera=dict(eye=dict(x=1.35, y=-1.35, z=0.75))))
    return fig


def figura_varredura(x, fem, exato_x, exato_y, atual, titulo_x, log_x):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=exato_x, y=exato_y, mode="lines",
                             name="fórmula exata", line=dict(color="black")))
    fig.add_trace(go.Scatter(x=x, y=fem, mode="markers", name="computador (FEM)",
                             marker=dict(size=10, color="darkorange")))
    fig.add_trace(go.Scatter(x=[atual[0]], y=[atual[1]], mode="markers",
                             name="sua simulação",
                             marker=dict(size=16, color="crimson",
                                         symbol="star")))
    eixo_log = dict(type="log", dtick=1) if log_x else dict(type="linear")
    fig.update_xaxes(title=titulo_x, **eixo_log)
    fig.update_yaxes(title="fator de blindagem", **eixo_log)
    fig.update_layout(height=470, margin=dict(t=30),
                      legend=dict(orientation="h", x=0, y=-0.25))
    return fig


# ------------------------------------------------------------------ barra lateral
def aplicar_exemplo():
    ex = EXEMPLOS.get(st.session_state.exemplo)
    if ex:
        st.session_state.b_cm = ex["b"]
        st.session_state.t_mm = ex["t"]
        st.session_state.mu_r = ex["mu"]


B0_PADRAO, META_PASSIVA, META_FINAL = metas()
for chave, valor in (("b_cm", 10.0), ("t_mm", 10), ("mu_r", 1000),
                     ("n", 2), ("B0", float(B0_PADRAO)), ("densidade", 7.3)):
    st.session_state.setdefault(chave, valor)

st.sidebar.header("Parâmetros")
st.sidebar.selectbox("Exemplos prontos", ["Personalizado"] + list(EXEMPLOS),
                     key="exemplo", on_change=aplicar_exemplo)
with st.sidebar.form("parametros"):
    b_cm = st.slider("Raio externo da esfera (cm)", 5.0, 20.0, step=0.5,
                     format="%.1f", key="b_cm",
                     help="Tamanho da casca de metal.")
    t_mm = st.select_slider("Espessura do metal (mm)", ESPESSURAS_MM,
                            key="t_mm",
                            help="Uma fita nanocristalina tem cerca de 0,02 mm; "
                                 "dez lâminas somam 0,2 mm.")
    mu_r = st.select_slider("Permeabilidade relativa µr", PERMEABILIDADES,
                            key="mu_r",
                            help="Quanto o material conduz o campo magnético. "
                                 "Ar = 1; ferrita MnZn ≈ 1.500; fitas "
                                 "nanocristalinas ≈ 64.000.")
    B0 = st.number_input("Campo externo B₀ (µT)", 1.0, 200.0, step=1.0,
                         key="B0", help="O projeto usa 90 µT como pior caso.")
    n = st.select_slider("Refino da malha", [1, 2, 4], key="n",
                         help="Multiplica o número de divisões da malha. Mais "
                              "refino = resultado mais preciso e mais lento.")
    densidade = st.number_input("Densidade do metal (g/cm³)", 1.0, 10.0,
                                step=0.1, key="densidade",
                                help="Fe nanocristalino ≈ 7,3; ferrita MnZn ≈ 4,9.")
    st.form_submit_button("Simular", type="primary", width="stretch")

# ------------------------------------------------------------------ página
st.title("Simulador de blindagem magnética: casca esférica")
st.caption("Passo 2 do guia do projeto. Escolha os parâmetros na barra lateral "
           "e clique em **Simular**. O computador resolve o campo pelo método "
           "dos elementos finitos e compara com a fórmula exata.")

if t_mm / 10 >= 0.6 * b_cm:
    st.error("A espessura precisa ser menor que 60% do raio externo.")
    st.stop()

with st.spinner("Calculando o campo..."):
    sf = simular(b_cm, t_mm, mu_r, n)
    exato = fator_exato(b_cm / 100 - t_mm / 1000, b_cm / 100, mu_r)
    c = campo_visual(b_cm, t_mm, mu_r)

erro = 100 * (sf / exato - 1)
b_int = 1000 * B0 / sf                                     # nT
a_cm = b_cm - t_mm / 10
massa = 4 / 3 * np.pi * (b_cm**3 - a_cm**3) * densidade / 1000   # kg

col = st.columns(6)
col[0].metric("Fator de blindagem", br(sf),
              help="Quantas vezes o campo diminui no centro.")
col[1].metric("Fórmula exata", br(exato))
col[2].metric("Erro do computador", f"{br(erro, 3, sinal=True)} %",
              help="Diferença entre o FEM e a fórmula. Abaixo de 1% é bom.")
col[3].metric("Atenuação", f"{br(20 * np.log10(sf))} dB")
col[4].metric("Campo no centro", f"{br(b_int, 0)} nT",
              help=f"B₀ = {B0:g} µT dividido pelo fator de blindagem.")
col[5].metric("Massa do metal", f"{br(massa, 2)} kg")

if abs(erro) > 1:
    st.warning(f"O erro está acima de 1%: aumente o **refino da malha**. "
               f"Cascas finas precisam de malha mais fina.")
if b_int <= META_FINAL:
    st.success(f"Campo no centro de {br(b_int, 0)} nT: abaixo da meta final de "
               f"{META_FINAL} nT só com a blindagem passiva.")
elif b_int <= META_PASSIVA:
    st.success(f"Campo no centro de {br(b_int, 0)} nT: atinge a meta passiva de "
               f"{META_PASSIVA} nT. As bobinas ainda precisariam reduzir "
               f"{br(b_int / META_FINAL)} vezes para chegar a {META_FINAL} nT.")
else:
    st.warning(f"Campo no centro de {br(b_int, 0)} nT: acima da meta passiva de {META_PASSIVA} nT. Para "
               f"{B0:g} µT, seria preciso um fator de blindagem de pelo menos "
               f"{1000 * B0 / META_PASSIVA:.0f}.")
st.info("Esta é uma **esfera fechada**, o caso ideal. No capacete, as aberturas "
        "para o rosto e o pescoço deixam o campo entrar e reduzem muito a "
        "blindagem; isso é estudado no Passo 5 do guia.")

lim = limites_de_cor(c, sf)
abas = st.tabs(["Mapa do campo", "Perfil do campo", "Visão 3D",
                "Efeito dos parâmetros", "Entenda e experimente"])

with abas[0]:
    esq, dir_ = st.columns([3, 2])
    fig = figura_mapa(c, sf, lim)
    esq.pyplot(fig)
    plt.close(fig)
    dir_.markdown(
        "**Como ler o mapa**\n\n"
        "- O corte mostra a esfera vista de lado; os círculos azuis são as "
        "faces interna e externa do metal.\n"
        "- As **cores** indicam a intensidade do campo em relação a B₀: claro "
        "é forte, escuro é fraco.\n"
        "- As **linhas brancas** mostram o caminho do campo. Elas são puxadas "
        "para dentro do metal e contornam a região central.\n"
        "- Logo fora do metal, no equador, também aparece uma região escura: "
        "uma \"sombra\", porque as linhas foram desviadas para dentro da "
        "casca.")
    if c["ajustado"]:
        dir_.caption(
            f"A casca de {t_mm:g} mm é fina demais para aparecer na grade do "
            f"desenho. Para os gráficos, ela foi representada com "
            f"{br(1000 * c['t_vis'])} mm e permeabilidade equivalente "
            f"({br(c['mu_vis'], 0)}), mantendo o mesmo produto µr × espessura. "
            f"O fator de blindagem acima é o do caso real.")

with abas[1]:
    direcao = st.radio("Direção do perfil",
                       ["Equador (plano horizontal)", "Eixo vertical z"],
                       horizontal=True)
    st.plotly_chart(figura_perfil(c, sf, direcao))
    st.markdown("A faixa cinza é o metal. Passe o mouse sobre a curva para ler "
                "os valores. Dentro da cavidade, o campo é uniforme e igual a "
                "B₀ dividido pelo fator de blindagem; no metal, o campo é "
                "maior que B₀, porque o fluxo se concentra ali.")

with abas[2]:
    with st.spinner("Traçando as linhas de campo em 3D..."):
        externas, internas = linhas(b_cm, t_mm, mu_r)
    st.plotly_chart(figura_3d(c, sf, externas, internas, lim))
    st.caption("Arraste para girar, use a roda do mouse para aproximar. A casca "
               "tem uma fatia removida para mostrar o interior. Cada linha "
               "externa transporta a mesma quantidade de fluxo: quase nenhuma "
               "atravessa a cavidade. As linhas escuras dentro dela mostram o "
               "campo interno, fraco e uniforme.")

with abas[3]:
    st.markdown("Calcula o fator de blindagem para vários valores, mantendo os "
                "demais parâmetros da barra lateral. Pode levar de 10 a 60 "
                "segundos, conforme o refino.")
    if st.button("Calcular as curvas", type="primary"):
        st.session_state.curvas = True
    if st.session_state.get("curvas"):
        e1, e2 = st.columns(2)
        with st.spinner("Variando a permeabilidade..."):
            mus, fem = varrer_permeabilidade(b_cm, t_mm, n)
        mx = np.logspace(1, 5, 200)
        a_m, b_m = b_cm / 100 - t_mm / 1000, b_cm / 100
        e1.plotly_chart(figura_varredura(
            mus, fem, mx, fator_exato(a_m, b_m, mx), (mu_r, sf),
            "permeabilidade relativa µr", log_x=True))
        with st.spinner("Variando a espessura..."):
            esp, fem_t = varrer_espessura(b_cm, mu_r, n)
        tx = np.linspace(min(esp), max(esp), 200)
        e2.plotly_chart(figura_varredura(
            esp, fem_t, tx, fator_exato(b_m - tx / 1000, b_m, mu_r),
            (t_mm, sf), "espessura do metal (mm)", log_x=False))

with abas[4]:
    st.markdown(f"""
### O que está sendo simulado
Uma esfera oca de metal é colocada num campo magnético uniforme. O computador
divide o espaço em milhares de pequenos triângulos (a **malha**) e calcula o
campo em cada um deles: é o **método dos elementos finitos (FEM)**. Como esse
caso também tem uma fórmula exata, dá para conferir se o programa acerta. Essa
conferência se chama **verificação**.

### Os parâmetros
- **Permeabilidade relativa (µr):** quanto o material conduz o campo. Quanto
  maior, mais o metal "puxa" as linhas de campo para si e menos campo sobra no
  centro.
- **Espessura:** mais metal oferece um caminho mais largo para o campo.
- **Raio:** esferas maiores blindam um pouco menos com a mesma espessura.
- **Refino da malha:** triângulos menores dão resultados mais precisos, mas o
  cálculo demora mais.
- **Campo externo B₀:** não muda o fator de blindagem, mas muda o campo que
  sobra no centro. O projeto usa {B0_PADRAO} µT como pior caso, com metas de
  {META_PASSIVA} nT depois da blindagem e {META_FINAL} nT depois das bobinas.
""")
    st.markdown("### Experimente")
    exercicios = [
        ("Escolha o *Exemplo do Passo 2* e dobre a espessura de 10 para 20 mm. "
         "O fator de blindagem também dobra?",
         "Não. Ele passa de 61 para 109: aumenta, mas menos que o dobro, "
         "porque a camada extra fica mais perto do centro."),
        ("Volte para 10 mm e aumente µr de 1.000 para 10.000. Quantas vezes o "
         "fator aumenta?",
         "Cerca de 10 vezes (de 61 para 603). Para cascas de alta "
         "permeabilidade, o fator é quase proporcional a µr."),
        ("Escolha *Fita Fe nanocristalina* e use refino 1. Qual é o erro? "
         "Depois use refino 2.",
         "Com refino 1 o erro é de cerca de −6%; com refino 2 cai para cerca "
         "de 0,01%. Cascas finas precisam de malha fina."),
        ("Escolha *Ar (sem blindagem)*. O que acontece com o campo?",
         "O fator de blindagem é 1: o campo não muda, porque o ar não desvia "
         "as linhas."),
        (f"Com B₀ = {B0_PADRAO} µT, encontre uma combinação de material e "
         f"espessura que leve o campo no centro abaixo de {META_PASSIVA} nT.",
         f"É preciso fator de pelo menos {1000 * B0_PADRAO / META_PASSIVA:.0f}. "
         f"Por exemplo, µr = 10.000 com 5 mm, ou a fita nanocristalina com "
         f"espessura de 1 mm. Lembre-se de que a esfera fechada é o caso "
         f"ideal."),
    ]
    for i, (pergunta, resposta) in enumerate(exercicios, 1):
        st.markdown(f"**{i}.** {pergunta}")
        with st.expander("Ver resposta"):
            st.markdown(resposta)
