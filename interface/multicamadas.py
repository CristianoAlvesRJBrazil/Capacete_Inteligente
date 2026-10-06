"""Controles e resultados de cascas esféricas com materiais sobrepostos."""
import csv
import io
from threading import RLock

import numpy as np
import streamlit as st

from visualizacoes_camadas import mostrar_visualizacoes

from verificacao_casca_esferica import (
    coeficientes_camadas, fator_blindagem_camadas,
)


@st.cache_resource(show_spinner=False)
def trava_matplotlib():
    """Matplotlib compartilha estado entre as sessões do Streamlit."""
    return RLock()


@st.cache_data(show_spinner=False)
def simular_camadas(b_cm, B0, n, entradas):
    a = b_cm / 100 - sum(t for _, t, _, _, _ in entradas) / 1000
    raio = a
    camadas, tabela = [], []
    for nome, t, mu, densidade, saturacao in entradas:
        externo = raio + t / 1000
        massa = (4 / 3 * np.pi * (externo**3 - raio**3)
                 * densidade * 1000 if densidade is not None else None)
        camadas.append((externo, mu))
        tabela.append({"Camada": len(camadas), "Material": nome,
                       "Espessura (mm)": t, "µr": mu,
                       "Raio interno (cm)": raio * 100,
                       "Raio externo (cm)": externo * 100,
                       "Massa (kg)": massa, "Bs (T)": saturacao})
        raio = externo
    fator = fator_blindagem_camadas(a, camadas, n=n, R=20 * raio)
    exato, coeficientes = coeficientes_camadas(a, camadas)
    # Na esfera, B tangencial é máximo no equador e B radial nos polos.
    # |A +/- B/r³| é monótono em cada região: basta verificar suas faces.
    for i, linha in enumerate(tabela):
        A, C = coeficientes[i + 1]
        faces = np.array([linha["Raio interno (cm)"],
                          linha["Raio externo (cm)"]]) / (raio * 100)
        pico = linha["µr"] * max(np.max(np.abs(A + C / faces**3)),
                                 np.max(np.abs(A - 2 * C / faces**3)))
        linha["Indução máxima (mT)"] = pico * B0 / 1000
        linha["Saturação (%)"] = (pico * B0 * 1e-6 / linha["Bs (T)"] * 100
                                  if linha["Bs (T)"] else None)
    return dict(fator=fator, exato=exato, campo=1000 * B0 / fator,
                tabela=tabela, coeficientes=coeficientes, a=a, b=raio)


def mostrar_camadas(base, materiais, b_cm, B0, n, meta_passiva, meta_final):
    st.markdown("**Materiais sobrepostos na mesma esfera**, sem espaço entre "
                "as camadas. A camada 1 fica junto à cavidade; as seguintes "
                "a recobrem. O raio externo, campo aplicado e refino vêm "
                "da barra lateral.")
    quantidade = st.number_input("Número de camadas", min_value=2, value=2,
                                 step=1, key="numero_camadas")
    tipo = st.radio("Permeabilidade das camadas", ["inicial", "maxima"],
                    horizontal=True, key="tipo_camadas")
    opcoes = [m.material_id for m in materiais]
    entradas = []
    for i in range(quantidade):
        st.markdown(f"**Camada {i + 1} — "
                    + ("junto à cavidade**" if i == 0 else "sobre a anterior**"))
        esquerda, direita = st.columns(2)
        padrao = "finemet_ft3m" if i == 0 else "ferrita_n87_tdk"
        mid = esquerda.selectbox("Material", opcoes, index=opcoes.index(padrao),
                                  format_func=lambda mid: base.materiais[mid].nome,
                                  key=f"material_camada_{i}")
        t = direita.number_input("Espessura (mm)", min_value=0.001, value=1.0,
                                  step=0.01, format="%.3f", key=f"t_camada_{i}")
        dados = base.parametros_simulacao(mid, tipo)
        valores = dados["valores"]
        entradas.append((base.materiais[mid].nome, t, valores["mu_r"],
                         valores["densidade"], valores["B_s"]))
        st.caption(f"µr = {valores['mu_r']:g}"
                   + (f" · fita de {valores['espessura_fita']:g} µm"
                      if valores["espessura_fita"] else ""))
        with st.expander(f"Dados e fontes da camada {i + 1}"):
            for prop, registro in dados["registros"].items():
                if registro:
                    fonte = base.fontes[registro.fonte_id]["referencia"]
                    st.write(f"{prop}: {registro.valor_efetivo:g} {registro.unidade} "
                             f"— {registro.condicao()} — {fonte}")
            for aviso in dados["avisos"]:
                st.warning(aviso)
    assinatura = (b_cm, B0, n, tipo, tuple(entradas))
    invalida = sum(t for _, t, *_ in entradas) / 10 >= 0.6 * b_cm
    if st.button("Simular camadas sobrepostas", type="primary", key="simular_camadas"):
        if invalida:
            st.error("A espessura total precisa ser menor que 60% do raio externo.")
        else:
            with st.spinner("Resolvendo o campo através de todas as camadas..."):
                resultado = simular_camadas(b_cm, B0, n, tuple(entradas))
            st.session_state.resultado_camadas = (assinatura, resultado)
    salvo = st.session_state.get("resultado_camadas")
    if not salvo:
        return
    if salvo[0] != assinatura or invalida:
        st.info("Os parâmetros mudaram. Simule as camadas novamente para atualizar.")
        return
    resultado = salvo[1]
    fator, exato = resultado["fator"], resultado["exato"]
    erro = 100 * (fator / exato - 1)
    colunas = st.columns(4)
    colunas[0].metric("Blindagem conjunta", f"{fator:.2f}")
    colunas[1].metric("Solução exata das camadas", f"{exato:.2f}")
    colunas[2].metric("Campo na cavidade", f"{resultado['campo']:.1f} nT")
    colunas[3].metric("Erro FEM das camadas", f"{erro:+.3f} %")
    tabela = resultado["tabela"]
    massas = [linha["Massa (kg)"] for linha in tabela]
    if all(massa is not None for massa in massas):
        st.metric("Massa total das camadas", f"{sum(massas):.3f} kg")
    else:
        st.caption("Massa total indisponível: falta densidade em pelo menos uma camada.")
    st.caption(f"Raio externo: {b_cm:g} cm · Campo aplicado: {B0:g} µT · Refino: {n}")
    st.dataframe(tabela, hide_index=True, key="tabela_camadas")
    if abs(erro) > 1:
        st.warning("Erro FEM acima de 1%; aumente o refino da malha.")
    for linha in tabela:
        saturacao = linha["Saturação (%)"]
        if saturacao is not None and saturacao >= 100:
            st.error(f"Camada {linha['Camada']} ({linha['Material']}): a indução "
                     "atinge a saturação; o modelo linear superestima a blindagem.")
        elif saturacao is not None and saturacao > 50:
            st.warning(f"Camada {linha['Camada']}: indução acima de 50% de Bs; "
                       "a permeabilidade constante pode superestimar a blindagem.")
    if resultado["campo"] <= meta_passiva:
        st.success(f"A blindagem conjunta atinge a meta passiva de {meta_passiva:g} nT.")
    else:
        st.warning(f"Campo acima da meta passiva de {meta_passiva:g} nT.")
    mostrar_visualizacoes(resultado, base, entradas, b_cm, B0,
                          meta_passiva, meta_final, trava_matplotlib)
    arquivo = io.StringIO()
    escritor = csv.DictWriter(arquivo, fieldnames=list(tabela[0]))
    escritor.writeheader()
    escritor.writerows(tabela)
    st.download_button("Baixar dados das camadas (CSV)",
                       arquivo.getvalue().encode("utf-8-sig"),
                       file_name="camadas_sobrepostas.csv", mime="text/csv")
