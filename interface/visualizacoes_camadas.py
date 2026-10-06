"""Visualizações do campo exato de todas as camadas da esfera composta."""
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Circle
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from capacete.materiais import formatar_valor
from verificacao_casca_esferica import campo_exato_camadas, fator_exato_camadas

ABAS = ["Mapa do campo", "Perfil do campo", "Visão 3D",
        "Efeito dos parâmetros", "Base de materiais", "Entenda e experimente"]
CORES = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"]


def geometria(resultado):
    return [(r["Raio externo (cm)"] / 100, r["µr"]) for r in resultado["tabela"]]


def campo(resultado, rho, z):
    return campo_exato_camadas(resultado["a"], geometria(resultado), rho, z)


def figura_mapa(resultado):
    b = resultado["b"]
    eixo = np.linspace(-1.5 * b, 1.5 * b, 401)
    X, Z = np.meshgrid(eixo, eixo)
    Bx, Bz = campo(resultado, X, Z)
    modulo = np.hypot(Bx, Bz)
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.pcolormesh(eixo * 100, eixo * 100, modulo, shading="auto",
                       cmap="magma", norm=LogNorm(vmin=modulo.min(),
                                                 vmax=max(modulo.max(), 1)))
    ax.streamplot(eixo * 100, eixo * 100, Bx, Bz, color="white",
                  density=1.4, linewidth=0.55, arrowsize=0.7)
    ax.add_patch(Circle((0, 0), resultado["a"] * 100, fill=False,
                        color="cyan", linewidth=1))
    for i, linha in enumerate(resultado["tabela"]):
        ax.add_patch(Circle((0, 0), linha["Raio externo (cm)"], fill=False,
                            color=CORES[i % len(CORES)], linewidth=1.5,
                            label=f"{i + 1}: {linha['Material']}"))
    ax.set(aspect="equal", xlabel="x (cm)", ylabel="z (cm)",
           title="Campo conjunto das camadas — solução exata")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=8)
    fig.colorbar(im, ax=ax, label="|B| / B₀")
    return fig


def figura_perfil(resultado, B0, direcao, meta_passiva, meta_final):
    fig = go.Figure()
    tabela = resultado["tabela"]
    limites = [0, resultado["a"]] + [r for r, _ in geometria(resultado)]
    limites.append(1.5 * resultado["b"])
    mus = [1] + [r["µr"] for r in tabela] + [1]
    nomes = ["Cavidade"] + [f"Camada {r['Camada']}: {r['Material']}" for r in tabela] + ["Exterior"]
    # Amostra cada região separadamente para preservar ambas as faces de
    # camadas finas e as descontinuidades tangenciais nos seus limites.
    for i, (A, C) in enumerate(resultado["coeficientes"]):
        raios = np.linspace(limites[i], limites[i + 1], 120)
        termo = np.divide(C, (raios / resultado["b"])**3,
                          out=np.zeros_like(raios), where=raios > 0)
        valores = mus[i] * np.abs(A + (termo if direcao == "Equador" else -2 * termo))
        fig.add_trace(go.Scatter(x=raios * 100, y=valores * B0 * 1000,
                                 name=nomes[i], mode="lines"))
    for i, linha in enumerate(tabela):
        fig.add_vrect(x0=linha["Raio interno (cm)"], x1=linha["Raio externo (cm)"],
                      fillcolor=CORES[i % len(CORES)], opacity=0.15, line_width=0)
    for meta, nome in [(meta_passiva, "Meta passiva"), (meta_final, "Meta final")]:
        fig.add_hline(y=meta, line_dash="dot")
        fig.add_annotation(x=1, xref="paper", xanchor="right", y=np.log10(meta),
                           yref="y", text=nome, showarrow=False, yshift=10)
    fig.update_layout(title=f"{direcao} — campo conjunto (solução exata)",
                      xaxis_title="Distância ao centro (cm)",
                      yaxis_title="|B| (nT)", yaxis_type="log", height=520)
    return fig


def linhas_fluxo(resultado):
    """Linhas exatas por fluxo poloidal constante, sem interpolar interfaces.

    2*Psi = mu*(A*r² - 2*C*b³/r)*sin²(theta). Cada linha é identificada
    pelo raio onde cruza o equador; os raios estão em metros.
    """
    a, b = resultado["a"], resultado["b"]
    limites = np.array([a] + [r for r, _ in geometria(resultado)])
    mus = np.array([1] + [r["µr"] for r in resultado["tabela"]] + [1])
    coefs = resultado["coeficientes"]

    def fluxo_equador(r):
        i = np.searchsorted(limites, r, side="right")
        A, C = coefs[i, 0], coefs[i, 1]
        return mus[i] * (A * r**2 - 2 * C * b**3 / r)

    sementes = [0.25 * a, 0.65 * a]
    sementes += list((limites[:-1] + limites[1:]) / 2)
    sementes += [1.1 * b, 1.3 * b]
    linhas = []
    for inicio in sementes:
        pontos = [inicio] + [r for r in limites if r > inicio] + [1.7 * b]
        raios = np.unique(np.concatenate([
            lo + (hi - lo) * np.linspace(0, 1, 80)**2
            for lo, hi in zip(pontos[:-1], pontos[1:])]))
        sen2 = np.clip(fluxo_equador(inicio) / fluxo_equador(raios), 0, 1)
        rho = raios * np.sqrt(sen2)
        z = raios * np.sqrt(1 - sen2)
        linhas.append(np.column_stack((np.r_[rho[::-1], rho[1:]],
                                       np.r_[-z[::-1], z[1:]])))
    return linhas


def figura_3d(resultado):
    fig = go.Figure()
    corte = 1.5 * np.pi
    theta = np.linspace(0, np.pi, 45)
    TH, PH = np.meshgrid(theta, np.linspace(0, corte, 61))
    for i, linha in enumerate(resultado["tabela"]):
        cor = CORES[i % len(CORES)]
        nome = f"Camada {i + 1}: {linha['Material']}"
        interno, externo = linha["Raio interno (cm)"], linha["Raio externo (cm)"]
        raios = [externo] if i else [interno, externo]
        for r in raios:
            fig.add_trace(go.Surface(
                x=r * np.sin(TH) * np.cos(PH), y=r * np.sin(TH) * np.sin(PH),
                z=r * np.cos(TH), surfacecolor=np.zeros_like(TH),
                colorscale=[[0, cor], [1, cor]], showscale=False, opacity=0.22,
                name=nome, legendgroup=str(i), showlegend=(r == externo),
                hovertemplate=nome + "<extra></extra>"))
        RR, TT = np.meshgrid(np.linspace(interno, externo, 3), theta)
        for phi in (0, corte):
            fig.add_trace(go.Surface(
                x=RR * np.sin(TT) * np.cos(phi), y=RR * np.sin(TT) * np.sin(phi),
                z=RR * np.cos(TT), surfacecolor=np.zeros_like(RR),
                colorscale=[[0, cor], [1, cor]], showscale=False,
                opacity=0.85, name=nome, hovertemplate=nome + "<extra></extra>"))
    linhas = linhas_fluxo(resultado)
    modulos = [np.hypot(*campo(resultado, lin[:, 0], lin[:, 1])) for lin in linhas]
    cmin = np.log10(min(v.min() for v in modulos))
    cmax = np.log10(max(1, max(v.max() for v in modulos)))
    for j, (lin, modulo) in enumerate(zip(linhas, modulos)):
        for k, phi in enumerate(np.linspace(0, corte, 4)):
            fig.add_trace(go.Scatter3d(
                x=100 * lin[:, 0] * np.cos(phi), y=100 * lin[:, 0] * np.sin(phi),
                z=100 * lin[:, 1], mode="lines", showlegend=False,
                customdata=modulo,
                hovertemplate="|B|/B₀ = %{customdata:.3g}<extra></extra>",
                line=dict(color=np.log10(modulo), colorscale="Plasma", width=3,
                          cmin=cmin, cmax=cmax, showscale=(j == 0 and k == 0),
                          colorbar=dict(title="log₁₀(|B|/B₀)"))))
    fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode="markers",
                               name="Cavidade protegida", marker=dict(color="limegreen", size=5)))
    L = resultado["b"] * 100
    fig.add_trace(go.Cone(x=[-1.3 * L], y=[-1.3 * L], z=[0], u=[0], v=[0], w=[1],
                          sizemode="absolute", sizeref=0.3 * L,
                          showscale=False, name="Campo aplicado +z"))
    fig.update_layout(height=680, scene=dict(aspectmode="data", xaxis_title="x (cm)",
                                            yaxis_title="y (cm)", zaxis_title="z (cm)"),
                      legend=dict(orientation="h", y=-0.1), margin=dict(l=0, r=0, t=20, b=0))
    return fig


def fator_das_entradas(b_cm, entradas):
    a = b_cm / 100 - sum(e[1] for e in entradas) / 1000
    raio = a
    camadas = []
    for _, t, mu, *_ in entradas:
        raio += t / 1000
        camadas.append((raio, mu))
    return fator_exato_camadas(a, camadas)


def varrer(b_cm, entradas, indice, parametro):
    coluna = 1 if parametro == "Espessura (mm)" else 2
    atual = entradas[indice][coluna]
    minimo, maximo = (atual * 0.2, atual * 2) if coluna == 1 else (max(1., atual / 10), atual * 10)
    if coluna == 1:
        outras = sum(e[1] for i, e in enumerate(entradas) if i != indice)
        maximo = min(maximo, (6 * b_cm - outras) * (1 - 1e-8))
    valores = np.unique(np.r_[np.geomspace(minimo, maximo, 31), atual])
    fatores = []
    for valor in valores:
        alteradas = [list(e) for e in entradas]
        alteradas[indice][coluna] = valor
        fatores.append(fator_das_entradas(b_cm, alteradas))
    return valores, fatores


def mostrar_visualizacoes(resultado, base, entradas, b_cm, B0,
                          meta_passiva, meta_final, trava):
    abas = st.tabs(ABAS)
    with abas[0]:
        st.caption("Campo da solução exata de todas as camadas. As fronteiras "
                   "têm seus raios reais; camadas muito finas podem não ser "
                   "resolvidas pelos pixels do mapa. Use o perfil para examiná-las.")
        with trava():
            fig = figura_mapa(resultado)
            st.pyplot(fig)
            plt.close(fig)
    with abas[1]:
        direcao = st.radio("Direção do perfil das camadas", ["Equador", "Eixo vertical z"],
                            horizontal=True, key="perfil_camadas")
        st.plotly_chart(figura_perfil(resultado, B0, direcao, meta_passiva, meta_final),
                        key="grafico_perfil_camadas")
        st.caption("Cada camada é amostrada separadamente. No equador, o campo "
                   "tangencial pode saltar entre materiais; no eixo, o fluxo normal é contínuo.")
    with abas[2]:
        st.plotly_chart(figura_3d(resultado), key="grafico_3d_camadas")
        st.caption("Arraste para girar e aproxime para ver as camadas finas. "
                   "As superfícies identificam os materiais; a fatia removida "
                   "mostra o interior. As linhas seguem o campo exato conjunto; "
                   "as cores indicam sua intensidade. O espaçamento entre linhas é ilustrativo.")
    with abas[3]:
        indice = st.selectbox("Camada a variar", list(range(len(entradas))),
                               format_func=lambda i: f"{i + 1}: {entradas[i][0]}",
                               key="camada_varredura")
        st.caption("Variações hipotéticas em uma camada, mantendo o raio externo "
                   "e as demais camadas. Ao mudar a espessura, o raio da cavidade "
                   "se ajusta. Curvas calculadas pela solução exata conjunta.")
        for coluna, parametro in zip(st.columns(2), ["Espessura (mm)", "Permeabilidade µr"]):
            xs, ys = varrer(b_cm, entradas, indice, parametro)
            atual = entradas[indice][1 if parametro == "Espessura (mm)" else 2]
            fig = go.Figure(go.Scatter(x=xs, y=ys, name="Solução exata", mode="lines"))
            fig.add_trace(go.Scatter(x=[atual], y=[resultado["fator"]],
                                     name="FEM atual", mode="markers", marker=dict(size=12)))
            fig.update_layout(xaxis_title=parametro, yaxis_title="Blindagem conjunta",
                              xaxis_type="log", yaxis_type="log", height=450)
            coluna.plotly_chart(fig, key=f"curva_camadas_{parametro}")
        invertido = fator_das_entradas(b_cm, list(reversed(entradas)))
        st.write(f"Invertendo toda a ordem, a solução exata dá fator **{invertido:.2f}** "
                 f"(ordem atual: **{resultado['exato']:.2f}**).")
    with abas[4]:
        st.markdown("**Materiais usados nesta simulação**")
        st.dataframe(resultado["tabela"], hide_index=True)
        st.markdown("**Catálogo de materiais**")
        tabela = []
        for material in sorted(base.materiais.values(), key=lambda m: (m.classe, m.nome)):
            mid = material.material_id
            linha = {"Material": material.nome, "Classe": material.classe}
            for titulo, props in [("µr inicial", ("mu_r_inicial", "mu_r")),
                                   ("µr máxima", ("mu_r_max",)), ("Bs (T)", ("B_s",)),
                                   ("Densidade (g/cm³)", ("densidade",))]:
                linha[titulo] = formatar_valor(base.escolher(mid, props))
            linha["Fonte"] = " ".join(base.fontes[material.fonte_principal]["referencia"].split())
            tabela.append(linha)
        st.dataframe(tabela, hide_index=True)
        st.caption("As condições e fontes dos valores usados estão em Dados e fontes "
                   "de cada camada, acima. Valores de fichas técnicas podem diferir "
                   "do comportamento na blindagem; os registros aguardam segunda conferência.")
    with abas[5]:
        st.markdown("""### Como as camadas trabalham juntas
O campo atravessa materiais com permeabilidades diferentes. O cálculo resolve
todas as interfaces: o fluxo normal e o potencial magnético são contínuos.
O FEM calcula a blindagem conjunta e a solução exata fornece os campos dos gráficos.

### Experimente
1. Troque os materiais da primeira e da última camada e simule novamente.
   Compare com a previsão de ordem invertida em **Efeito dos parâmetros**.
2. Use o mesmo material em todas as camadas. O resultado equivale a uma casca
   homogênea com a soma das espessuras.
3. Aumente a espessura de uma camada e observe a massa e o raio da cavidade.
4. Mude o campo externo: o fator de blindagem fica igual no modelo linear,
   mas o campo residual e a indução em cada material aumentam proporcionalmente.
5. Compare os perfis no equador e no eixo. As mudanças entre materiais são
   diferentes para as componentes tangencial e normal do campo.

### Limites do modelo
São camadas esféricas fechadas, contíguas e com permeabilidade constante.
O modelo não inclui saturação não linear, aberturas do capacete, histerese ou
dependência com frequência. Confira os avisos de saturação por camada antes
de interpretar uma blindagem elevada como realizável.
""")
