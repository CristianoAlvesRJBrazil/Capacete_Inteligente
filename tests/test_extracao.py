"""Extração assistida dos PDFs: padrões de texto, conversões, filtros e a
importação com validação (sem PDFs: o texto entra direto)."""
import csv
import shutil

import pytest

from capacete.extracao import (COLUNAS, Documento, extrair_paginas, importar, para_float,
                               sem_referencias)
from capacete.materiais import PASTA_PADRAO, BaseInvalida, carregar


@pytest.fixture(scope="module")
def base():
    return carregar()


@pytest.fixture(scope="module")
def faixas(base):
    return {p: (float(d["faixa"][0]), float(d["faixa"][1]), d["unidade"])
            for p, d in base.dicionario["propriedades"].items()}


def extrair(texto, faixas, doc=None):
    cands, val, _ = extrair_paginas([texto], doc or Documento("teste.pdf"), faixas)
    return {c["propriedade"]: c for c in cands}, val


def test_numeros():
    assert para_float("1.2 × 10^5") == pytest.approx(1.2e5)
    assert para_float("1.2×10^-6") == pytest.approx(1.2e-6)
    assert para_float("100,000") == 100000
    assert para_float("64 000") == 64000
    assert para_float("10^4") == 1e4


def test_extrai_converte_e_pega_a_condicao(faixas):
    c, _ = extrair(
        "The FINEMET FT-3M ribbon has a ribbon thickness of 18 μm and an initial permeability of "
        "7.0 × 104 at 1 kHz and 0.4 A/m. The coercivity of FT-3M is 10 mOe. The stacking factor "
        "was 80%. The electrical resistivity of permalloy is 55 μΩ·cm and its density is 8.7 g/cm3.",
        faixas)
    mu = c["mu_r_inicial"]
    assert (mu["valor"], mu["frequencia_Hz"], mu["material_id"], mu["confianca"]) == \
        ("70000", "1000", "finemet_ft3m", "alta")
    assert "0.4 A/m" in mu["excitacao"]
    assert float(c["H_c"]["valor"]) == pytest.approx(0.795775)          # 10 mOe
    assert "original 10 mOe" in c["H_c"]["observacoes"]
    assert c["espessura_fita"]["valor"] == "18"
    assert float(c["fator_empilhamento"]["valor"]) == pytest.approx(0.8)
    assert float(c["resistividade"]["valor"]) == pytest.approx(5.5e-7)
    assert c["resistividade"]["material_detectado"] == "permalloy"
    assert c["densidade"]["valor"] == "8.7"


def test_condutividade_vira_resistividade_e_expoente_perdido(faixas):
    c, _ = extrair("The electrical conductivity of 1.7 × 10^6 S/m was used.", faixas)
    assert float(c["resistividade"]["valor"]) == pytest.approx(1 / 1.7e6, rel=1e-4)
    c, _ = extrair("The resistivity of mu-metal is 55·10-6 Ω cm.", faixas)   # 10⁻⁶ sem sobrescrito
    assert float(c["resistividade"]["valor"]) == pytest.approx(5.5e-7)
    c, _ = extrair("Fe-based nanocrystalline alloys have an initial permeability of 104 –106.", faixas)
    assert (c["mu_r_inicial"]["valor_min"], c["mu_r_inicial"]["valor_max"]) == ("10000", "1e+06")
    assert "expoente reconstruído" in c["mu_r_inicial"]["observacoes"]


def test_filtros_de_falsos_positivos(faixas):
    textos = (
        "The vacuum permeability μ0 = 4π × 10^-7 H/m.",                  # constante física
        "The relative permeability (Fig. 3) is shown for the sample.",     # número de figura
        "The condition is μr t/a ≫ 1 for field confinement.",              # μ < 100: equação
        "The permeability of the https://doi.org/10.3390/ma19101986",      # DOI
        "The dynamic permeability is given in Phys. Rev. B 174402-3.",     # paginação
        "Each step took 20 ms and the noise spectral density was 5 fT.",   # ms não é Ms
        "The magnetostriction is near zero for permalloy films (x 81).",   # teor de Ni
    )
    for t in textos:
        c, _ = extrair(t, faixas)
        assert not c, (t, c)


def test_valor_de_outro_trabalho_vira_citado(faixas):
    c, _ = extrair("Shen et al. [21] fabricated Fe-based nanocrystalline ribbons with a permeability "
                   "of 64,000.", faixas)
    assert c["mu_r"]["tipo_dado"] == "citado" and c["mu_r"]["valor"] == "64000"


def test_compara_com_o_registro_da_mesma_fonte(base, faixas):
    doc = Documento("Shen.pdf", fonte_id="shen2026", material_padrao="fe_nano_shen2026",
                    existentes=[r for r in base.registros if r.fonte_id == "shen2026"])
    c, _ = extrair("The Fe-Nanos exhibit excellent soft magnetic properties with the permeability "
                   "of 64 000, indicating superior shielding.", faixas, doc)
    assert c["mu_r"]["material_id"] == "fe_nano_shen2026"
    assert c["mu_r"]["registro_existente"].startswith("confere com M-0144")


def test_fatores_de_blindagem(faixas):
    _, val = extrair("The three-layer cylindrical shield reached an axial shielding factor of "
                     "1.2 × 10^4 at 10 Hz. The passive shielding factor of the room was about 40 dB.",
                     faixas)
    assert [(v["fator_blindagem"], v["eixo"], v["n_camadas"], v["geometria"], v["frequencia_Hz"])
            for v in val][0] == ("12000", "axial", 3, "cilindro", "10")
    assert val[1]["fator_blindagem"] == "100"                             # 40 dB


def test_corta_a_lista_de_referencias():
    paginas = ["texto 1", "texto 2\nReferences\n[1] permeability of 50,000", "[2] mais"]
    assert sem_referencias(paginas) == ["texto 1", "texto 2"]


def _candidato(**campos):
    linha = dict.fromkeys(COLUNAS, "")
    linha.update(aprovar="s", tipo_dado="medido", localizacao="p. 4 (texto)", arquivo="x.pdf", **campos)
    return linha


def _gravar(caminho, linhas):
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)


def test_importar_valida_cadastra_fonte_e_marca(tmp_path):
    pasta = tmp_path / "materiais"
    shutil.copytree(PASTA_PADRAO, pasta)
    n0 = len(carregar(pasta).registros)
    arq = tmp_path / "candidatos.csv"
    _gravar(arq, [
        _candidato(material_id="fe_nano_shen2026", propriedade="densidade", valor="7.3", unidade="g/cm3",
                   fonte_id="shen2026"),                                  # valor fictício, ausente da base
        _candidato(material_id="finemet_ft3m", propriedade="B_s", valor="1.23", unidade="T",
                   fonte_id="kang2025", doi="10.3390/ma18020330",
                   referencia="KANG, X. et al. Simulation research on magnetic noise. 2025."),
        _candidato(material_id="fe_nano_shen2026", propriedade="mu_r", valor="64000", unidade="-",
                   fonte_id="shen2026"),                                  # já é o M-0144
        dict(_candidato(material_id="mumetall", propriedade="B_s", valor="0.8", unidade="T",
                        fonte_id="shen2026"), aprovar=""),                 # não aprovado
    ])
    ids = importar(arq, "Revisor Teste", pasta=pasta)["novos"]
    assert ids == [f"M-{n0 + 1:04d}", f"M-{n0 + 2:04d}"]
    nova = carregar(pasta)
    assert len(nova.registros) == n0 + 2
    assert "kang2025" in nova.fontes and "10.3390/ma18020330" in nova.fontes["kang2025"]["url"]
    r = nova.registros[-1]
    assert (r.extraido_por, r.conferido_por) == ("Revisor Teste", "")
    marcados = [l["importado"] for l in csv.DictReader(open(arq, encoding="utf-8-sig"))]
    assert marcados == [ids[0], ids[1], "já estava na base", ""]
    assert importar(arq, "Revisor Teste", pasta=pasta) == {"novos": [], "conferidos": []}   # nada em dobro
    assert open(pasta / "registros.csv", "rb").read().count(b"\r\n") == n0 + 3      # CRLF mantido


def test_importar_confere_registro_citado(tmp_path):
    """Linha que confere com um registro 'citado' atualiza esse registro em vez
    de duplicar: passa a 'medido', aponta para o original e ganha conferido_por."""
    pasta = tmp_path / "materiais"
    shutil.copytree(PASTA_PADRAO, pasta)
    n0 = len(carregar(pasta).registros)
    arq = tmp_path / "candidatos.csv"
    _gravar(arq, [dict(_candidato(material_id="fe_nano_shen2026", propriedade="mu_r", valor="64000",
                                  unidade="-", fonte_id="shen2026",
                                  registro_existente="confere com M-0144 (64000)"),
                       localizacao="p. 1 (texto)")])
    assert importar(arq, "Revisor Teste", pasta=pasta) == {"novos": [], "conferidos": ["M-0144"]}
    nova = carregar(pasta)
    assert len(nova.registros) == n0
    r = next(r for r in nova.registros if r.id_registro == "M-0144")
    assert (r.tipo_dado, r.localizacao, r.conferido_por) == ("medido", "p. 1 (texto)", "Revisor Teste")
    assert "localização anterior: revisão v3.0, seção 5.2" in r.observacoes


def test_quem_extraiu_nao_confere_o_proprio_registro(tmp_path):
    pasta = tmp_path / "materiais"
    shutil.copytree(PASTA_PADRAO, pasta)
    arq = tmp_path / "candidatos.csv"
    _gravar(arq, [dict(_candidato(material_id="fe_nano_shen2026", propriedade="mu_r", valor="64000",
                                  unidade="-", fonte_id="shen2026",
                                  registro_existente="confere com M-0144 (64000)"),
                       localizacao="p. 1 (texto)")])
    importar(arq, "claude-assistente", pasta=pasta)                      # mesmo autor do M-0144
    r = next(r for r in carregar(pasta).registros if r.id_registro == "M-0144")
    assert (r.tipo_dado, r.conferido_por) == ("medido", "")
    assert "falta a conferência por uma segunda pessoa" in r.observacoes


def test_temperatura_declarada(faixas):
    c, _ = extrair("As shown in Figure 2a, the Ms is 1.2 T at 300 K and decreases with temperature.", faixas)
    assert float(c["B_s"]["temperatura_C"]) == pytest.approx(26.85)


def test_importar_com_erro_nao_muda_nada(tmp_path):
    pasta = tmp_path / "materiais"
    shutil.copytree(PASTA_PADRAO, pasta)
    antes = (pasta / "registros.csv").read_text("utf-8")
    arq = tmp_path / "candidatos.csv"
    _gravar(arq, [_candidato(material_id="material_que_nao_existe", propriedade="B_s", valor="1.2",
                             unidade="T", fonte_id="shen2026")])
    with pytest.raises(BaseInvalida, match="inexistente"):
        importar(arq, "Revisor Teste", pasta=pasta)
    assert (pasta / "registros.csv").read_text("utf-8") == antes
