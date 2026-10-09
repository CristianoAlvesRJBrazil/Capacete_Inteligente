"""Extração assistida de valores dos PDFs para a base de materiais (Fase 1).

As regras da base exigem unidade, condição, fonte, localização e conferência
humana de cada valor; por isso a extração tem duas etapas, com revisão no meio:

    python -m capacete.extracao extrair PASTA_DOS_PDFS [--saida DIR]
        Lê cada PDF (pdftotext), procura as propriedades do dicionário com valor
        e unidade, converte para a unidade da base, descarta o que sai da faixa
        plausível e grava, em DIR (padrão: resultados/extracao):
          candidatos.csv            um valor por linha, com página e trecho
          candidatos_validacao.csv  fatores de blindagem citados nos textos
          relatorio_extracao.md     o que saiu de cada PDF

    python -m capacete.extracao importar DIR/candidatos.csv --revisor NOME
        Acrescenta à base só as linhas com aprovar = s; cadastra a fonte em
        fontes.yaml se faltar; valida a base inteira numa cópia e só então grava
        (nada muda se algo falhar); regenera docs/materiais_cobertura.md.

A extração é por padrões de texto: acha o que está escrito em frases do tipo
"initial permeability of 7 × 10^4 at 1 kHz". Valores só em tabelas ou em
figuras escapam, e PDF de imagem precisa de OCR antes.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import shutil
import subprocess
import tempfile
import textwrap
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


from .materiais import CAMPOS_REGISTRO, PASTA_PADRAO, RAIZ, carregar, relatorio_cobertura

SAIDA_PADRAO = RAIZ / "resultados" / "extracao"
RELATORIO_COBERTURA = RAIZ / "docs" / "materiais_cobertura.md"
APROVADO = {"s", "sim", "x", "1", "ok"}

COLUNAS = ["aprovar", "material_id", "material_detectado", "propriedade", "valor",
           "valor_min", "valor_max", "unidade", "valor_original", "frequencia_Hz",
           "excitacao", "temperatura_C", "processamento", "tipo_dado", "fonte_id", "localizacao",
           "confianca", "registro_existente", "trecho", "arquivo", "doi", "referencia",
           "observacoes", "importado"]
COLUNAS_VALIDACAO = ["arquivo", "doi", "pagina", "fator_blindagem", "valor_original", "eixo",
                     "n_camadas", "geometria", "frequencia_Hz", "trecho", "observacoes"]


# --------------------------------------------------------------------- texto
_SOBRESCRITO = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")
_LIGADURAS = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "µ": "μ",
              "−": "-", "‒": "-", "⋅": "·", "∙": "·", "℃": "°C", "Ω": "Ω", "◦": "°", "º": "°"}


def normalizar(texto: str) -> str:
    """Uma linha por página: ligaduras desfeitas, sobrescritos viram '^',
    hifenização de fim de linha desfeita, espaços colapsados."""
    for a, b in _LIGADURAS.items():
        texto = texto.replace(a, b)
    texto = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+", lambda m: "^" + m.group().translate(_SOBRESCRITO), texto)
    texto = re.sub(r"(?<=\d)[  ](?=\d{3}\b)", "", texto)       # 100 000 (espaço fino)
    texto = re.sub(r"([a-z])-\n([a-z])", r"\1\2", texto)
    texto = re.sub(r"°\s+([CF])\b", r"°\1", texto)
    return re.sub(r"\s+", " ", texto.replace(" ", " ")).strip()


def sem_referencias(paginas: list) -> list:
    """Corta a lista de referências: valores citados de outros trabalhos ficam fora."""
    for i in range(len(paginas) - 1, -1, -1):
        m = re.search(r"\n\s*(?:References|REFERENCES|Bibliography|Literature Cited)\s*\n", paginas[i])
        if m and i >= len(paginas) // 2:
            return paginas[:i] + [paginas[i][:m.start()]]
    return paginas


def ler_pdf(caminho: Path) -> list:
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("pdftotext não encontrado: instale o poppler "
                           "(apt install poppler-utils ou conda install -c conda-forge poppler)")
    r = subprocess.run([exe, "-enc", "UTF-8", str(caminho), "-"], capture_output=True, timeout=180)
    return r.stdout.decode("utf-8", errors="replace").split("\f")


# --------------------------------------------------------------------- números
NUM = (r"(?:(?:\d{1,3}(?:[, ]\d{3})+(?!\d)|\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?"
       r"(?:\s*[×x·]\s*10\s*\^?\s*-?\s*\d{1,2})?|10\s*\^\s*-?\d{1,2})")
_FAIXA = re.compile(rf"(?P<a>{NUM})(?:\s*(?:–|-|to|~)\s*(?P<b>{NUM}))?")
_QUALIF_MIN = re.compile(r"(?:>|≥|over|above|exceed\w*|more than|higher than|greater than|at least)\s*$", re.I)
_QUALIF_MAX = re.compile(r"(?:<|≤|below|less than|lower than|under|up to)\s*$", re.I)
_APROX = re.compile(r"(?:~|≈|about|approximately|around|nearly|roughly)\s*$", re.I)
# após um número, qualquer uma destas marcas o torna grandeza com unidade
_ALGUMA_UNIDADE = re.compile(
    r"\s*-?\s*(?:%|[kMG]?Hz|[mμnpf]?T\b|Tesla|k?A/m|m?A/cm|m?Oe|[μmnc]m\b|um\b|°C|K\b|dB|k?Gs?\b|"
    r"g/cm|kg|emu|S/m|Ω|ohm|ppm|layers?|times|-?fold|days?|h\b|min\b|s\b|wt|at\.?\s?%|mm|V\b|W\b|J\b)")


def para_float(texto: str) -> float:
    t = texto.replace(",", "").replace(" ", "")
    m = re.fullmatch(r"10\^(-?\d+)", t)
    if m:
        return 10.0 ** int(m.group(1))
    m = re.fullmatch(r"([\d.eE+-]+)[×x·]10\^?(-?\d+)", t)
    if m:
        return float(m.group(1)) * 10.0 ** int(m.group(2))
    return float(t)


# --------------------------------------------------------------------- regras
@dataclass(frozen=True)
class Regra:
    propriedade: str
    chave: str                                  # regex da palavra-chave
    unidades: tuple = ()                        # (regex, fator, deslocamento); fator None = não convertível
    adimensional: bool = False
    inverso: bool = False                       # condutividade -> resistividade
    nota: str = ""


_U_PERCENT = ((r"%", 0.01, 0),)
# palavras em (?i:...); símbolos (Bs, Hc, μr) distinguem maiúsculas: "ms" não é Ms
REGRAS = (
    Regra("mu_r_inicial", r"(?i:initial (?:relative |magnetic )?permeabilit(?:y|ies))|μ_?(?:i|in|ini)\b", adimensional=True),
    Regra("mu_r_max", r"(?i:maximum (?:relative |magnetic )?permeabilit(?:y|ies))|μ_?max\b|μ_?m,max", adimensional=True),
    Regra("mu_r", r"(?i:(?:relative |effective |magnetic |DC |static )?permeabilit(?:y|ies))|μ_?r\b", adimensional=True),
    Regra("B_s", r"(?i:saturation (?:magnetic )?(?:flux density|induction|polari[sz]ation|magneti[sz]ation))|\b[BJM]_?s\b",
          ((r"T(?![a-zA-Z0-9_/])|[Tt]esla", 1.0, 0), (r"mT\b", 1e-3, 0), (r"kGs?\b", 0.1, 0),
           (r"emu/g|A\s*·?\s*m\^?2/kg", None, 0))),
    Regra("H_c", r"(?i:coerciv(?:ity|e force|e field))|\bH_?c\b",
          ((r"kA/m", 1e3, 0), (r"mA/cm", 0.1, 0), (r"A/cm", 100.0, 0), (r"A/m|A\s*·?\s*m\^-1", 1.0, 0),
           (r"mOe", 0.0795775, 0), (r"Oe", 79.5775, 0))),
    Regra("razao_Br_Bs", r"(?i:squareness(?: ratio)?|remanence ratio)|[BM]_?r\s*/\s*[BM]_?s",
          _U_PERCENT, adimensional=True),
    Regra("espessura_fita", r"(?i:(?:ribbon|foil|sheet|strip|lamination|layer)s? (?:with a |of )?thickness(?: of)?|"
                            r"thickness of (?:the )?(?:ribbon|foil|sheet|strip|lamination)s?)",
          ((r"μm|um\b|microns?", 1.0, 0), (r"mm\b", 1000.0, 0), (r"nm\b", 1e-3, 0))),
    Regra("fator_empilhamento", r"(?i:(?:stacking|lamination|space|filling|fill|packing) factor)", _U_PERCENT,
          adimensional=True),
    Regra("densidade", r"(?i:(?<!flux )(?<!current )(?<!noise )(?<!power )(?<!spectral )(?<!energy )\bdensity\b)",
          ((r"g\s*/\s*cm\^?3|g\s*·?\s*cm\^?-3", 1.0, 0), (r"kg\s*/\s*m\^?3|kg\s*·?\s*m\^?-3", 1e-3, 0))),
    Regra("resistividade", r"(?i:(?:electrical )?resistivit(?:y|ies))",
          ((r"μΩ\s*·?\s*cm|μohm\s*·?\s*cm|micro-?ohm\s*·?\s*cm", 1e-8, 0), (r"mΩ\s*·?\s*cm", 1e-5, 0),
           (r"Ω\s*·?\s*cm|ohm\s*·?\s*cm", 1e-2, 0), (r"μΩ\s*·?\s*m\b", 1e-6, 0), (r"Ω\s*·?\s*mm\b", 1e-3, 0),
           (r"Ω\s*·?\s*m\b|ohm\s*·?\s*m\b", 1.0, 0))),
    Regra("resistividade", r"(?i:(?<!thermal )(?:electrical )?conductivit(?:y|ies))",
          ((r"MS\s*/\s*m|MS\s*·?\s*m\^-1", 1e6, 0), (r"S\s*/\s*m|S\s*·?\s*m\^-1", 1.0, 0)),
          inverso=True, nota="convertido de condutividade (ρ = 1/σ)"),
    Regra("magnetostricao_sat", r"(?i:(?:saturation )?magnetostriction(?: constant| coefficient)?)|λ_?s\b",
          ((r"ppm", 1.0, 0),)),
    Regra("temperatura_curie", r"(?i:Curie (?:temperature|point))",
          ((r"°C|oC\b", 1.0, 0), (r"K\b", 1.0, -273.15))),
    Regra("condutividade_termica", r"(?i:thermal conductivit(?:y|ies))",
          ((r"W\s*/\s*\(?m\s*·?\s*K\)?|W\s*·?\s*m\^-1\s*·?\s*K\^-1", 1.0, 0),)),
)
_REGRAS_RX = [(r, re.compile(r.chave)) for r in REGRAS]
# materiais de blindagem têm μr >> 100; abaixo disso o número quase sempre vem
# de equação, legenda ou eixo de figura (a faixa do dicionário continua valendo)
MU_MIN_EXTRACAO = 100
_SOBRESCRITO_PERDIDO = re.compile(r"10([2-7])")      # "10⁴" que o PDF entregou como "104"
_CITACAO = re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]|\bet al\.")
_NAO_MATERIAL = re.compile(r"(?i)vacuum|free space|μ_?0\b")          # permeabilidade do vácuo
_REFERENCIA_ANTES = re.compile(r"(?i)(?:fig(?:ure)?s?\.?|tables?|eqs?\.?|equations?|refs?\.?|sections?|no\.)\s*\(?$")

_SF = re.compile(r"(?:(?P<eixo>axial|longitudinal|transverse|transversal|radial)\s+)?(?:magnetic\s+)?"
                 r"shielding (?:factor|coefficient|ratio|effectiveness)s?", re.I)
_CAMADAS = {"single": 1, "one": 1, "two": 2, "double": 2, "three": 3, "triple": 3, "four": 4,
            "five": 5, "six": 6}
_N_CAMADAS = re.compile(r"\b(single|one|two|three|four|five|six|double|triple|\d)[- ](?:layers?|shells?)\b", re.I)


# --------------------------------------------------------------------- materiais
# códigos de grau comercial -> material_id da base (casamento exato)
GRAUS = {
    "finemet_ft3m": r"\bFT-?3M\b", "finemet_ft3h": r"\bFT-?3H\b", "finemet_ft3l": r"\bFT-?3L\b",
    "finemet_ft3s": r"\bFT-?3S\b", "vitroperm_500f": r"VITROPERM\s*500\s*F", "metglas_2705m": r"\b2705\s?M\b",
    "vitrovac_6025": r"VITROVAC\s*6025", "mumetall": r"\bMUMETALL\b", "ultraperm_10": r"ULTRAPERM\s*10\b",
    "vacoperm_100": r"VACOPERM\s*100\b", "ferrita_n87_tdk": r"\bN87\b",
}
# nomes genéricos: indicam a classe, mas o material exato fica para o revisor
GENERICOS = (
    ("mu-metal", r"\bmu-?metals?\b|μ-?metals?\b|\bmumetals?\b"), ("permalloy", r"\bpermalloys?\b"),
    ("1J85", r"\b1J8[05]\b"), ("1J79", r"\b1J79\b"), ("1K107", r"\b1K10[17]\b"), ("FINEMET", r"\bFINEMET\b"),
    ("VITROPERM", r"\bVITROPERM\b"), ("Metglas", r"\bMetglas\b"), ("Fe nanocristalino", r"\bnanocrystalline\b"),
    ("Co amorfo", r"\bCo-based amorphous|cobalt-based amorphous"), ("Fe amorfo", r"\bFe-based amorphous"),
    ("ferrita MnZn", r"\bMn-?Zn ferrites?\b"), ("aço silício", r"\bsilicon steel|electrical steel\b"),
    ("ferro puro", r"\bpure iron\b"),
)
_GRAUS_RX = {mid: re.compile(rx) for mid, rx in GRAUS.items()}
_GENERICOS_RX = [(nome, re.compile(rx, re.I)) for nome, rx in GENERICOS]


def _material_na_frase(frase: str):
    for mid, rx in _GRAUS_RX.items():
        if rx.search(frase):
            return mid, ""
    for nome, rx in _GENERICOS_RX:
        if rx.search(frase):
            return "", nome
    return "", ""


# --------------------------------------------------------------------- extração
@dataclass
class Documento:
    arquivo: str
    doi: str = ""
    fonte_id: str = ""
    referencia: str = ""
    material_padrao: str = ""            # material da base ligado a esta fonte
    existentes: list = field(default_factory=list)   # registros da base desta fonte


_FIM_FRASE = re.compile(r"[.!?]\s+(?=[A-Z(])")


def _frase(texto: str, ini: int, fim: int) -> str:
    """A frase que contém texto[ini:fim] (no máximo 400 caracteres para cada lado)."""
    inicio = max(0, ini - 400)
    cortes = [m.end() for m in _FIM_FRASE.finditer(texto, inicio, ini)]
    a = cortes[-1] if cortes else inicio
    m = _FIM_FRASE.search(texto, fim, fim + 400)
    b = m.start() + 1 if m else min(len(texto), fim + 400)
    return texto[a:b].strip()


def _frequencia(frase: str):
    m = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(Hz|kHz|MHz)\b", frase)
    if m:
        return float(m.group(1)) * {"Hz": 1, "kHz": 1e3, "MHz": 1e6}[m.group(2)]
    return 0.0 if re.search(r"\b(?:DC|d\.c\.|quasi-?static)\b", frase) else None


def _temperatura(frase: str):
    """Temperatura declarada como 'at 300 K' ou 'at 25 °C', em °C."""
    m = re.search(r"\bat (-?\d+(?:\.\d+)?)\s*(K|°C)\b", frase)
    if not m:
        return None
    t = float(m.group(1))
    return t - 273.15 if m.group(2) == "K" else t


def _excitacao(frase: str) -> str:
    m = re.search(r"(?<![\w.])(\d+(?:\.\d+)?\s*(?:mA/m|A/m|mOe|Oe|μT|nT))\b", frase)
    return f"amplitude {m.group(1)} (texto)" if m else ""


def _unidade(regra: Regra, depois: str):
    """(fator, deslocamento, texto da unidade) se `depois` começa com uma unidade da regra."""
    for rx, fator, desloc in regra.unidades:
        m = re.match(rf"\s*(?:{rx})", depois)
        if m:
            return fator, desloc, m.group().strip()
    return None


def _valores(regra: Regra, janela: str, inicio_janela: int):
    """Primeiro valor válido para a regra dentro da janela após a palavra-chave."""
    for m in _FAIXA.finditer(janela):
        antes, depois = janela[:m.start()], janela[m.end():]
        if antes[-1:].isalpha() or antes[-1:] in "_[" or depois[:1] == "]":
            continue                                  # Fe73.5, 1J85, [12]
        if _REFERENCIA_ANTES.search(antes):
            continue                                  # Fig. 3, Table 2, Eq. (5)
        if antes.rstrip()[-1:] in ("×", "/", ":"):
            continue                                  # (×10^4) de cabeçalho, URL, DOI, arXiv
        txt_a, txt_b = m.group("a"), m.group("b")
        if txt_b and re.fullmatch(r"10-\d{1,2}", m.group()):
            txt_a, txt_b = f"10^-{txt_b}", None       # "10-6": expoente que perdeu o sobrescrito
        elif txt_b and para_float(txt_b) < para_float(txt_a):
            continue                                  # "174402-3" é paginação, não faixa
        a = para_float(txt_a)
        b = para_float(txt_b) if txt_b else None
        u = _unidade(regra, depois)
        if u is None and regra.propriedade == "magnetostricao_sat" and abs(a) < 1e-3:
            u = (1e6, 0, "")                          # 2 × 10^-6 sem unidade -> 2 ppm
        if u is None:
            if not regra.adimensional or _ALGUMA_UNIDADE.match(depois):
                continue
            u = (1.0, 0, "")
        fator, desloc, txt_u = u
        expoente = ""
        if regra.propriedade.startswith("mu_r") and not txt_u:
            ea, eb = _SOBRESCRITO_PERDIDO.fullmatch(txt_a), _SOBRESCRITO_PERDIDO.fullmatch(txt_b or "")
            if ea:
                a = 10.0 ** int(ea.group(1))
            if eb:
                b = 10.0 ** int(eb.group(1))
            if ea or eb:
                expoente = "expoente reconstruído (o PDF perdeu o sobrescrito: 104 = 10^4); conferir"
        if regra.propriedade == "magnetostricao_sat" and antes.rstrip().endswith("-"):
            a = -a
        if regra.adimensional and not txt_u and regra.unidades == _U_PERCENT and a > 1:
            continue                                  # razão/fator sem % deve ser <= 1
        orig = f"{m.group().strip()} {txt_u}".strip()
        posicao = dict(ini=inicio_janela + m.start(), fim=inicio_janela + m.end() + len(txt_u))
        if fator is None:
            return dict(original=orig, convertivel=False, **posicao)
        conv = (lambda v: 1.0 / (v * fator)) if regra.inverso else (lambda v: v * fator + desloc)
        qual = "aprox" if _APROX.search(antes) else ("min" if _QUALIF_MIN.search(antes)
                                                     else "max" if _QUALIF_MAX.search(antes) else "")
        valores = sorted(conv(v) for v in (a, b) if v is not None)
        return dict(original=orig, convertivel=True, valores=valores, qualificador=qual, expoente=expoente,
                    convertido=bool(txt_u and (fator != 1 or desloc or regra.inverso)), **posicao)
    return None


def _formatar(v) -> str:
    return "" if v is None else f"{v:.6g}"


def extrair_paginas(paginas: list, doc: Documento, faixas: dict):
    """Candidatos (linhas de candidatos.csv), candidatos de validação e
    contagem de descartes por faixa, para as páginas de um documento."""
    candidatos, validacao, descartes, vistos = [], [], 0, set()
    for n_pag, bruto in enumerate(paginas, 1):
        texto = normalizar(bruto)
        for regra, rx in _REGRAS_RX:
            for k in rx.finditer(texto):
                if regra.propriedade.startswith("mu_r"):
                    if regra.propriedade == "mu_r" and re.search(r"(?i)(?:initial|maximum)\s+(?:relative |magnetic )?$",
                                                                  texto[max(0, k.start() - 30):k.start()]):
                        continue                      # já coberto por mu_r_inicial / mu_r_max
                    if _NAO_MATERIAL.search(texto[max(0, k.start() - 20):k.end() + 25]):
                        continue
                janela = texto[k.end():k.end() + 90]
                corte = re.search(r"[.;]\s+(?=[A-Z])", janela)
                janela = janela[:corte.start()] if corte else janela
                achado = _valores(regra, janela, k.end())
                if not achado:
                    continue
                frase = _frase(texto, k.start(), achado["ini"])
                mid, generico = _material_na_frase(frase)
                confianca = "alta" if mid else ("media" if generico else "baixa")
                if not mid and not generico and doc.material_padrao:
                    mid, confianca = doc.material_padrao, "media"
                linha = dict.fromkeys(COLUNAS, "")
                linha.update(material_id=mid, material_detectado=generico or mid, propriedade=regra.propriedade,
                             unidade=faixas[regra.propriedade][2], valor_original=achado["original"],
                             tipo_dado="medido", fonte_id=doc.fonte_id, localizacao=f"p. {n_pag} (texto)",
                             confianca=confianca, trecho=frase[:300], arquivo=doc.arquivo, doi=doc.doi,
                             referencia=doc.referencia)
                notas = [regra.nota] if regra.nota else []
                if achado["convertivel"]:
                    vals = achado["valores"]
                    baixo, alto = faixas[regra.propriedade][:2]
                    if any(not baixo <= v <= alto for v in vals) or (
                            regra.propriedade.startswith("mu_r") and max(vals) < MU_MIN_EXTRACAO):
                        descartes += 1
                        continue
                    if len(vals) == 2:
                        linha.update(valor_min=_formatar(vals[0]), valor_max=_formatar(vals[1]))
                    elif achado["qualificador"] == "min":
                        linha["valor_min"] = _formatar(vals[0])
                    elif achado["qualificador"] == "max":
                        linha["valor_max"] = _formatar(vals[0])
                    else:
                        linha["valor"] = _formatar(vals[0])
                    if achado["qualificador"] == "aprox":
                        notas.append("valor aproximado na fonte")
                    if achado["convertido"]:
                        notas.append(f"original {achado['original']}")
                    if achado["expoente"]:
                        notas.append(achado["expoente"])
                else:
                    notas.append(f"unidade não convertível sem dado adicional: {achado['original']} "
                                 "(Bs = μ0·σ·ρ precisa da densidade)")
                if _CITACAO.search(frase):
                    linha["tipo_dado"] = "citado"
                    notas.append("a frase cita outro trabalho: conferir na fonte original")
                freq = _frequencia(frase)
                linha["frequencia_Hz"] = "" if freq is None else f"{freq:g}"
                temp = _temperatura(frase)
                linha["temperatura_C"] = "" if temp is None else f"{temp:g}"
                if regra.propriedade.startswith("mu_r"):
                    linha["excitacao"] = _excitacao(frase)
                linha["observacoes"] = "; ".join(notas)
                linha["registro_existente"] = _comparar(linha, doc)
                chave = (linha["propriedade"], linha["valor"], linha["valor_min"], linha["valor_max"],
                         linha["material_id"] or linha["material_detectado"], linha["valor_original"])
                if chave not in vistos:
                    vistos.add(chave)
                    candidatos.append(linha)
        validacao += _validacao(texto, n_pag, doc)
    return candidatos, validacao, descartes


def _comparar(linha: dict, doc: Documento) -> str:
    """Compara com os registros que a base já tem desta mesma fonte (p. ex. um
    valor 'citado' de segunda mão que agora pode ser conferido no original)."""
    if not linha["valor"]:
        return ""
    v = float(linha["valor"])
    out = []
    for r in doc.existentes:
        if r.propriedade == linha["propriedade"] and r.material_id == linha["material_id"]:
            ref = r.valor_efetivo
            igual = math.isclose(ref, v, rel_tol=0.02)
            out.append(f"{'confere com' if igual else 'difere de'} {r.id_registro} ({ref:g})")
    return "; ".join(out)


def _fator(janela: str, efetividade: bool):
    """(fator, texto original, notas) do primeiro número válido da janela."""
    for m in _FAIXA.finditer(janela):
        antes, depois = janela[:m.start()], janela[m.end():]
        if antes.count(",") > 1:
            return None                               # já passou para outra oração
        if (antes[-1:].isalpha() or antes[-1:] in "_[" or depois[:1] == "]" or _REFERENCIA_ANTES.search(antes)
                or antes.rstrip()[-1:] in ("×", "/", ":")):
            continue
        db = re.match(r"\s*dB\b", depois)
        if not db and _ALGUMA_UNIDADE.match(depois):
            continue                                  # 10 Hz, 2 mm, 3 layers...
        txt, notas = m.group("a"), []
        v = para_float(txt)
        if _SOBRESCRITO_PERDIDO.fullmatch(txt):
            v = 10.0 ** int(txt[2:])
            notas.append("expoente reconstruído (o PDF perdeu o sobrescrito: 104 = 10^4); conferir")
        if db or (efetividade and not re.match(r"\s*(?:times|-?fold)", depois)):
            if not db:
                notas.append("shielding effectiveness sem unidade: assumido em dB")
            v = 10 ** (v / 20)
        return v, (m.group("a") + (" dB" if db else "")).strip(), notas
    return None


def _validacao(texto: str, n_pag: int, doc: Documento) -> list:
    saida = []
    for k in _SF.finditer(texto):
        achado = _fator(texto[k.end():k.end() + 70], "effectiveness" in k.group().lower())
        if not achado or not 2 < achado[0] < 1e9:
            continue
        v, original, notas = achado
        frase = _frase(texto, k.start(), k.end())
        viz = texto[max(0, k.start() - 300):k.end() + 300]
        nc = _N_CAMADAS.search(viz)
        n = (_CAMADAS.get(nc.group(1).lower()) or int(nc.group(1))) if nc else ""
        geo = ("esfera" if re.search(r"spher", viz, re.I) else
               "cilindro_aberto" if re.search(r"open[- ]ended|open ends", viz, re.I) else
               "cilindro" if re.search(r"cylind", viz, re.I) else
               "sala" if re.search(r"shielded room|\bMSR\b", viz) else "")
        eixo = (k.group("eixo") or "").lower()
        eixo = "axial" if eixo in ("axial", "longitudinal") else ("transversal" if eixo else "")
        if re.search(r"(?i)axial\b.{0,20}\b(?:and|or)\b.{0,10}\b(?:transverse|transversal|radial)", frase):
            eixo, notas = "", notas + ["a frase dá os fatores axial e transversal: separar pelo trecho"]
        if _CITACAO.search(frase):
            notas.append("a frase cita outro trabalho")
        freq = _frequencia(frase)
        saida.append(dict(arquivo=doc.arquivo, doi=doc.doi, pagina=n_pag, fator_blindagem=f"{v:.6g}",
                          valor_original=original, eixo=eixo, n_camadas=n, geometria=geo,
                          frequencia_Hz="" if freq is None else f"{freq:g}", trecho=frase[:300],
                          observacoes="; ".join(notas)))
    return saida


# --------------------------------------------------------------------- fontes e metadados
def _doi_norm(d: str) -> str:
    d = (d or "").strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    return d.rstrip(".;,)")


def dois_das_fontes(fontes: dict) -> dict:
    """DOI -> chave de fontes.yaml (o DOI aparece na referência ou na URL)."""
    out = {}
    for chave, f in fontes.items():
        for campo in ("referencia", "url"):
            for d in re.findall(r"10\.\d{4,9}/[^\s\"<>]+", str(f.get(campo, ""))):
                out.setdefault(_doi_norm(d), chave)
    return out


def _slug(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def referencia_de(meta: dict) -> str:
    autores = [a.strip() for a in (meta.get("Autores") or "").split(";") if a.strip()]
    if autores:
        partes = autores[0].split()
        primeiro = f"{partes[-1].upper()}, {' '.join(p[0] + '.' for p in partes[:-1])}".strip(", ")
        autor = primeiro + (" et al." if len(autores) > 1 else "")
    else:
        autor = "AUTOR NÃO INFORMADO."
    doi = meta.get("DOI", "")
    return f"{autor} {meta.get('Titulo', '').strip()}. {meta.get('Ano', '')}." + (f" DOI: {doi}." if doi else "")


def documentos(pasta: Path, base) -> list:
    """Um Documento por PDF, com DOI, fonte e material padrão. Usa o pdfs.csv
    do agente pesquisador, se estiver na pasta; senão, procura o DOI no texto."""
    meta = {}
    arq_meta = pasta / "pdfs.csv"
    if arq_meta.exists():
        with open(arq_meta, encoding="utf-8-sig", newline="") as f:
            meta = {l["Arquivo"]: l for l in csv.DictReader(f) if l.get("Arquivo")}
    por_doi = dois_das_fontes(base.fontes)
    usadas = set(base.fontes)
    docs = []
    for pdf in sorted(pasta.glob("*.pdf")):
        m = meta.get(pdf.name, {})
        doc = Documento(arquivo=pdf.name, doi=_doi_norm(m.get("DOI", "")))
        doc.referencia = referencia_de(m) if m else ""
        if doc.doi and doc.doi in por_doi:
            doc.fonte_id = por_doi[doc.doi]
        elif m:
            autores = (m.get("Autores") or "sem autor").split(";")[0].split()
            proposta = f"{_slug(autores[-1] if autores else 'sem')}{m.get('Ano', '')}"
            chave, k = proposta, 1
            while chave in usadas:
                chave, k = f"{proposta}{'bcdefghij'[k - 1]}", k + 1
            usadas.add(chave)
            doc.fonte_id = chave
        ligados = [mt.material_id for mt in base.materiais.values() if doc.fonte_id and mt.fonte_principal == doc.fonte_id]
        doc.material_padrao = ligados[0] if len(ligados) == 1 else ""
        doc.existentes = [r for r in base.registros if doc.fonte_id and r.fonte_id == doc.fonte_id]
        docs.append(doc)
    return docs


# --------------------------------------------------------------------- comando extrair
def _gravar_csv(caminho: Path, colunas: list, linhas: list) -> None:
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas)
        w.writeheader()
        w.writerows(linhas)


def extrair(pasta_pdfs: Path, saida: Path = SAIDA_PADRAO, pasta_base: Path = PASTA_PADRAO, log=print) -> dict:
    base = carregar(pasta_base)
    props = base.dicionario["propriedades"]
    faixas = {p: (float(d["faixa"][0]), float(d["faixa"][1]), d["unidade"]) for p, d in props.items()}
    docs = documentos(Path(pasta_pdfs), base)
    if not docs:
        raise FileNotFoundError(f"nenhum PDF em {pasta_pdfs}")
    saida.mkdir(parents=True, exist_ok=True)
    todos, validacao, resumo = [], [], []
    for i, doc in enumerate(docs, 1):
        paginas = ler_pdf(Path(pasta_pdfs) / doc.arquivo)
        n_car = sum(len(p.strip()) for p in paginas)
        cands, val, desc = extrair_paginas(sem_referencias(paginas), doc, faixas)
        todos += cands
        validacao += val
        resumo.append((doc, len(paginas), n_car, cands, val, desc))
        log(f"  [{i:2}/{len(docs)}] {len(cands):3} candidatos, {len(val):2} fatores de blindagem  {doc.arquivo[:70]}")
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    todos.sort(key=lambda l: (l["arquivo"], ordem[l["confianca"]], l["propriedade"]))
    _gravar_csv(saida / "candidatos.csv", COLUNAS, todos)
    _gravar_csv(saida / "candidatos_validacao.csv", COLUNAS_VALIDACAO, validacao)
    (saida / "relatorio_extracao.md").write_text(_relatorio(resumo, pasta_pdfs, props), encoding="utf-8")
    return dict(pdfs=len(docs), candidatos=len(todos), validacao=len(validacao),
                sem_texto=sum(1 for r in resumo if r[2] < 500))


def _relatorio(resumo: list, pasta, props: dict) -> str:
    total = [c for r in resumo for c in r[3]]
    por_prop = {p: sum(1 for c in total if c["propriedade"] == p) for p in props}
    conf = {n: sum(1 for c in total if c["confianca"] == n) for n in ("alta", "media", "baixa")}
    out = ["# Extração assistida dos PDFs", "",
           f"Pasta: `{pasta}`  ", f"Gerado em: {date.today().isoformat()}", "",
           "| | Quantidade |", "|---|---:|",
           f"| PDFs lidos | {len(resumo)} |",
           f"| PDFs sem texto (imagem: precisam de OCR) | {sum(1 for r in resumo if r[2] < 500)} |",
           f"| Candidatos a registro | {len(total)} |",
           f"| ... confiança alta (material identificado na frase) | {conf['alta']} |",
           f"| ... confiança média (material genérico ou da fonte) | {conf['media']} |",
           f"| ... confiança baixa (sem material na frase) | {conf['baixa']} |",
           f"| Conferem ou divergem de registros já na base | {sum(1 for c in total if c['registro_existente'])} |",
           f"| Fatores de blindagem citados (validação) | {sum(len(r[4]) for r in resumo)} |",
           f"| Valores descartados por sair da faixa plausível | {sum(r[5] for r in resumo)} |", "",
           "## Candidatos por propriedade", "", "| Propriedade | Candidatos |", "|---|---:|"]
    out += [f"| {props[p]['nome']} (`{p}`) | {n} |" for p, n in por_prop.items() if n]
    out += ["", "## Por PDF", "", "| PDF | Páginas | Candidatos | Fatores de blindagem | Fonte |",
            "|---|---:|---:|---:|---|"]
    for doc, n_pag, n_car, cands, val, _ in resumo:
        nome = doc.arquivo if n_car >= 500 else f"{doc.arquivo} (sem texto)"
        out.append(f"| {nome} | {n_pag} | {len(cands)} | {len(val)} | `{doc.fonte_id or '?'}` |")
    out += ["", "## Como revisar", "",
            "1. Abra `candidatos.csv` (LibreOffice ou Excel) e confira cada linha no PDF, "
            "pela página e pelo trecho.",
            "2. Para aceitar, escreva `s` em `aprovar`. Preencha `material_id` com um id de "
            "`materiais/materiais.csv` (cadastre o material antes, se for novo) e corrija "
            "`tipo_dado`, condição (`frequencia_Hz`, `excitacao`, `processamento`) e "
            "`localizacao` se preciso.",
            "3. `python -m capacete.extracao importar <pasta>/candidatos.csv --revisor SEU_NOME`.",
            "4. Os fatores de blindagem de `candidatos_validacao.csv` vão para "
            "`materiais/validacao_blindagem.csv` à mão: a montagem (raios, espessuras, "
            "espaçamentos) precisa ser lida no artigo.", ""]
    return "\n".join(out)


# --------------------------------------------------------------------- comando importar
def _proximo_id(registros) -> int:
    return max((int(r.id_registro[2:]) for r in registros), default=0) + 1


def _bloco_fonte(chave: str, linha: dict, revisor: str) -> str:
    ref = textwrap.fill(" ".join(linha["referencia"].split()) or chave, 76,
                        initial_indent="    ", subsequent_indent="    ")
    doi = _doi_norm(linha["doi"])
    return (f"\n{chave}:\n  referencia: >-\n{ref}\n"
            + (f"  url: https://doi.org/{doi}\n" if doi else "")
            + f"  tipo: artigo\n  acesso: \"{date.today().isoformat()}\"\n"
            f"  observacoes: >-\n    PDF de acesso aberto; valores extraídos com capacete.extracao\n"
            f"    e aprovados por {revisor}.\n")


_CONDICAO = ("frequencia_Hz", "excitacao", "temperatura_C", "processamento")


def _conferir(reg: dict, linha: dict, revisor: str) -> None:
    """Registro que a base já tinha (p. ex. 'citado' de segunda mão) e que o
    revisor conferiu no original: passa a apontar para o original."""
    anterior = reg["localizacao"]
    reg["tipo_dado"] = linha["tipo_dado"].strip() or reg["tipo_dado"]
    reg["localizacao"] = linha["localizacao"].strip()
    segunda_pessoa = revisor.strip().lower() != reg["extraido_por"].strip().lower()
    if segunda_pessoa:                                # quem extraiu não confere o próprio registro
        reg["conferido_por"] = revisor
    for campo in _CONDICAO:
        if not reg[campo] and linha.get(campo, "").strip():
            reg[campo] = linha[campo].strip()
    nota = (f"conferido no original ({reg['localizacao']}) por {revisor} em {date.today().isoformat()}; "
            f"localização anterior: {anterior}"
            + ("" if segunda_pessoa else "; falta a conferência por uma segunda pessoa"))
    reg["observacoes"] = "; ".join(x for x in (reg["observacoes"], nota) if x)


def importar(candidatos: Path, revisor: str, pasta: Path = PASTA_PADRAO, simular: bool = False) -> dict:
    """Leva para a base as linhas aprovadas: cria registros novos ou, quando a
    linha 'confere com M-xxxx', marca esse registro como conferido no original.
    Devolve {"novos": [...], "conferidos": [...]}. Valida a base inteira numa
    cópia antes de gravar; em erro, levanta BaseInvalida e nada muda."""
    if not revisor.strip():
        raise ValueError("informe --revisor")
    pasta = Path(pasta)
    with open(candidatos, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    aprovadas = [l for l in linhas if (l.get("aprovar") or "").strip().lower() in APROVADO
                 and not (l.get("importado") or "").strip()]
    resultado = {"novos": [], "conferidos": []}
    if not aprovadas:
        return resultado
    base = carregar(pasta)
    ja = {(r.material_id, r.propriedade, r.valor, r.valor_min, r.valor_max, r.fonte_id) for r in base.registros}
    num = lambda t: float(t) if str(t).strip() else None  # noqa: E731
    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / "materiais"
        shutil.copytree(pasta, copia)
        with open(copia / "registros.csv", encoding="utf-8", newline="") as f:
            registros = list(csv.DictReader(f))
        por_id = {r["id_registro"]: r for r in registros}
        n, fontes_novas = _proximo_id(base.registros), {}
        for l in aprovadas:
            conf = re.match(r"confere com (M-\d{4})", (l.get("registro_existente") or "").strip())
            if conf and conf.group(1) in por_id:
                _conferir(por_id[conf.group(1)], l, revisor)
                resultado["conferidos"].append(conf.group(1))
                l["importado"] = f"conferiu {conf.group(1)}"
                continue
            chave = (l["material_id"].strip(), l["propriedade"].strip(), num(l["valor"]), num(l["valor_min"]),
                     num(l["valor_max"]), l["fonte_id"].strip())
            if chave in ja:
                l["importado"] = "já estava na base"
                continue
            ja.add(chave)
            if l["fonte_id"].strip() not in base.fontes and l["fonte_id"].strip() not in fontes_novas:
                fontes_novas[l["fonte_id"].strip()] = _bloco_fonte(l["fonte_id"].strip(), l, revisor)
            rid = f"M-{n:04d}"
            n += 1
            obs = "; ".join(x for x in (l.get("observacoes", "").strip(),
                                        f"extração assistida de {l['arquivo']}; aprovado por {revisor}") if x)
            reg = dict.fromkeys(CAMPOS_REGISTRO, "")
            reg.update(id_registro=rid, **{k: l.get(k, "").strip() for k in
                                           ("material_id", "propriedade", "valor", "valor_min", "valor_max",
                                            "unidade", "tipo_dado", "fonte_id", "localizacao") + _CONDICAO},
                       extraido_por=revisor, data_extracao=date.today().isoformat(), observacoes=obs)
            registros.append(reg)
            resultado["novos"].append(rid)
            l["importado"] = rid
        # o csv do módulo padrão grava CRLF, como o arquivo original
        with open(copia / "registros.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS_REGISTRO)
            w.writeheader()
            w.writerows(registros)
        if fontes_novas:
            with open(copia / "fontes.yaml", "a", encoding="utf-8") as f:
                f.write("".join(fontes_novas.values()))
        nova = carregar(copia)                        # BaseInvalida aqui: nada foi gravado
        if not simular:
            for nome in ("registros.csv", "fontes.yaml"):
                shutil.copy2(copia / nome, pasta / nome)
            if pasta.resolve() == PASTA_PADRAO.resolve():
                RELATORIO_COBERTURA.write_text(relatorio_cobertura(nova), encoding="utf-8")
            _gravar_csv(Path(candidatos), list(linhas[0].keys()), linhas)
    return resultado


# --------------------------------------------------------------------- linha de comando
def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extrair", help="lê os PDFs e grava candidatos para revisão")
    e.add_argument("pasta_pdfs")
    e.add_argument("--saida", default=SAIDA_PADRAO, type=Path)
    i = sub.add_parser("importar", help="leva à base as linhas aprovadas (aprovar = s)")
    i.add_argument("candidatos", type=Path)
    i.add_argument("--revisor", required=True)
    i.add_argument("--simular", action="store_true", help="valida sem gravar")
    a = p.parse_args(argv)
    if a.cmd == "extrair":
        r = extrair(Path(a.pasta_pdfs), a.saida)
        print(f"\n{r['pdfs']} PDFs ({r['sem_texto']} sem texto): {r['candidatos']} candidatos a registro e "
              f"{r['validacao']} fatores de blindagem.\nRevise {a.saida / 'candidatos.csv'} "
              f"(relatório: {a.saida / 'relatorio_extracao.md'}).")
    else:
        r = importar(a.candidatos, a.revisor, simular=a.simular)
        if not (r["novos"] or r["conferidos"]):
            print("Nenhuma linha nova aprovada (aprovar = s) para importar.")
        else:
            verbo = "Validaria" if a.simular else "Base validada"
            print(f"{verbo}: {len(r['novos'])} registros novos ({', '.join(r['novos']) or '-'}) e "
                  f"{len(r['conferidos'])} conferidos no original ({', '.join(r['conferidos']) or '-'})."
                  + ("" if a.simular else " docs/materiais_cobertura.md regenerado."))


if __name__ == "__main__":
    main()
