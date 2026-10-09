"""Leitura, validação e uso da base de dados dos materiais (Fase 1).

Uso:
    python -m capacete.materiais                  # resumo no terminal
    python -m capacete.materiais --relatorio ARQ  # cobertura e lacunas em Markdown
"""
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
PASTA_PADRAO = RAIZ / "materiais"
CAMPOS_REGISTRO = ("id_registro", "material_id", "propriedade", "valor", "valor_min",
                   "valor_max", "unidade", "frequencia_Hz", "excitacao",
                   "temperatura_C", "amostra", "processamento", "incerteza",
                   "tipo_dado", "fonte_id", "localizacao", "extraido_por",
                   "data_extracao", "conferido_por", "observacoes")
# Propriedades que o simulador usa diretamente
ESSENCIAIS = ("mu_r_inicial", "mu_r_max", "B_s", "densidade", "espessura_fita")


class BaseInvalida(ValueError):
    """Erro de conteúdo ou de formato na base de materiais."""


def _numero(texto, campo, rid):
    if texto is None or str(texto).strip() == "":
        return None
    try:
        return float(texto)
    except ValueError as erro:
        raise BaseInvalida(f"{rid}: {campo} não numérico ({texto!r})") from erro


@dataclass(frozen=True)
class Registro:
    id_registro: str
    material_id: str
    propriedade: str
    valor: float | None
    valor_min: float | None
    valor_max: float | None
    unidade: str
    frequencia_Hz: float | None
    excitacao: str
    temperatura_C: float | None
    amostra: str
    processamento: str
    incerteza: str
    tipo_dado: str
    fonte_id: str
    localizacao: str
    extraido_por: str
    data_extracao: str
    conferido_por: str
    observacoes: str

    @property
    def so_limite_superior(self) -> bool:
        return self.valor is None and self.valor_min is None and self.valor_max is not None

    @property
    def valor_efetivo(self) -> float:
        """Valor nominal; na falta dele, o limite conservador da faixa."""
        for v in (self.valor, self.valor_min, self.valor_max):
            if v is not None:
                return v
        raise BaseInvalida(f"{self.id_registro}: sem valor")

    def condicao(self) -> str:
        partes = []
        if self.frequencia_Hz is not None:
            partes.append("DC" if self.frequencia_Hz == 0
                          else f"{self.frequencia_Hz:g} Hz")
        for texto in (self.excitacao, self.processamento):
            if texto:
                partes.append(texto)
        if self.temperatura_C is not None:
            partes.append(f"{self.temperatura_C:g} °C")
        return "; ".join(partes) or "condição não informada"


@dataclass(frozen=True)
class Material:
    material_id: str
    nome: str
    classe: str
    fabricante: str
    grau: str
    forma: str
    processamento: str
    fonte_principal: str
    observacoes: str


@dataclass
class Base:
    materiais: dict[str, Material]
    registros: list[Registro]
    fontes: dict
    dicionario: dict
    avisos: list[str] = field(default_factory=list)

    def registros_de(self, material_id, propriedade=None):
        return [r for r in self.registros if r.material_id == material_id
                and (propriedade is None or r.propriedade == propriedade)]

    def escolher(self, material_id, propriedades):
        """Registro da primeira propriedade disponível: menor frequência
        informada, temperatura mais próxima de 25 °C e, no empate, o menor
        valor (escolha conservadora). Registro que só traz limite superior
        ("≤ X") fica por último: usá-lo como valor seria otimista."""
        def chave(r):
            dt = abs(r.temperatura_C - 25) if r.temperatura_C is not None else 0
            return (r.so_limite_superior, r.frequencia_Hz is None, r.frequencia_Hz or 0, dt,
                    r.valor_efetivo)

        for prop in propriedades:
            candidatos = self.registros_de(material_id, prop)
            if candidatos:
                return min(candidatos, key=chave)
        return None

    def parametros_simulacao(self, material_id, permeabilidade="inicial"):
        """Entradas do simulador para um material, com os registros de origem."""
        ordem = (("mu_r_inicial", "mu_r", "mu_r_max") if permeabilidade == "inicial"
                 else ("mu_r_max", "mu_r", "mu_r_inicial"))
        mu = self.escolher(material_id, ordem)
        usados = {"mu_r": mu,
                  "B_s": self.escolher(material_id, ("B_s",)),
                  "densidade": self.escolher(material_id, ("densidade",)),
                  "espessura_fita": self.escolher(material_id, ("espessura_fita",))}
        avisos = []
        if mu is not None and mu.propriedade != ordem[0]:
            avisos.append(f"Sem '{ordem[0]}' na base; usado '{mu.propriedade}'.")
        if mu is not None and mu.so_limite_superior:
            avisos.append(f"A fonte só dá um limite superior de permeabilidade (≤ {mu.valor_max:g}); "
                          "o valor usado é otimista.")
        elif mu is not None and mu.valor is None and mu.valor_max is None:
            avisos.append(f"A fonte dá um mínimo de permeabilidade (≥ {mu.valor_min:g}); "
                          "usado esse mínimo (conservador).")
        elif mu is not None and mu.valor is None:
            avisos.append("A fonte dá uma faixa de permeabilidade; usado o limite "
                          "inferior (conservador).")
        valores = {k: (r.valor_efetivo if r else None) for k, r in usados.items()}
        return dict(valores=valores, registros=usados, avisos=avisos)

    def simulaveis(self):
        """Materiais com permeabilidade registrada."""
        com_mu = {r.material_id for r in self.registros
                  if r.propriedade.startswith("mu_r")}
        return [m for m in self.materiais.values() if m.material_id in com_mu]


def _ler_csv(caminho):
    with open(caminho, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def carregar(pasta: Path | str = PASTA_PADRAO) -> Base:
    """Lê e valida a base; levanta BaseInvalida no primeiro erro."""
    pasta = Path(pasta)
    dicionario = yaml.safe_load((pasta / "dicionario.yaml").read_text("utf-8"))
    fontes = yaml.safe_load((pasta / "fontes.yaml").read_text("utf-8"))
    props = dicionario["propriedades"]

    materiais = {}
    for linha in _ler_csv(pasta / "materiais.csv"):
        m = Material(**{k: (v or "").strip() for k, v in linha.items()})
        if m.material_id in materiais:
            raise BaseInvalida(f"material repetido: {m.material_id}")
        if m.classe not in dicionario["classes"]:
            raise BaseInvalida(f"{m.material_id}: classe '{m.classe}'")
        if m.forma not in dicionario["formas"]:
            raise BaseInvalida(f"{m.material_id}: forma '{m.forma}'")
        if m.fonte_principal not in fontes:
            raise BaseInvalida(f"{m.material_id}: fonte '{m.fonte_principal}'")
        materiais[m.material_id] = m

    registros, ids = [], set()
    for linha in _ler_csv(pasta / "registros.csv"):
        rid = linha.get("id_registro", "?")
        if set(linha) != set(CAMPOS_REGISTRO):
            raise BaseInvalida(f"{rid}: colunas diferentes do esquema")
        if not re.fullmatch(r"M-\d{4}", rid) or rid in ids:
            raise BaseInvalida(f"{rid}: id inválido ou repetido")
        ids.add(rid)
        dados = {k: (v or "").strip() for k, v in linha.items()}
        for campo in ("valor", "valor_min", "valor_max", "frequencia_Hz",
                      "temperatura_C"):
            dados[campo] = _numero(dados[campo], campo, rid)
        r = Registro(**dados)
        if r.material_id not in materiais:
            raise BaseInvalida(f"{rid}: material '{r.material_id}' inexistente")
        if r.propriedade not in props:
            raise BaseInvalida(f"{rid}: propriedade '{r.propriedade}' fora do dicionário")
        if r.unidade != props[r.propriedade]["unidade"]:
            raise BaseInvalida(f"{rid}: unidade '{r.unidade}' para {r.propriedade}")
        if r.tipo_dado not in dicionario["tipos_dado"]:
            raise BaseInvalida(f"{rid}: tipo de dado '{r.tipo_dado}'")
        if r.fonte_id not in fontes:
            raise BaseInvalida(f"{rid}: fonte '{r.fonte_id}' inexistente")
        if not r.localizacao:
            raise BaseInvalida(f"{rid}: localização na fonte ausente")
        if all(v is None for v in (r.valor, r.valor_min, r.valor_max)):
            raise BaseInvalida(f"{rid}: sem valor nem faixa")
        if (r.valor_min is not None and r.valor_max is not None
                and r.valor_min > r.valor_max):
            raise BaseInvalida(f"{rid}: valor_min maior que valor_max")
        baixo, alto = (float(x) for x in props[r.propriedade]["faixa"])
        for v in (r.valor, r.valor_min, r.valor_max):
            if v is not None and not baixo <= v <= alto:
                raise BaseInvalida(f"{rid}: {v} fora da faixa plausível "
                                   f"[{baixo}, {alto}] de {r.propriedade}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.data_extracao):
            raise BaseInvalida(f"{rid}: data de extração '{r.data_extracao}'")
        registros.append(r)
    return Base(materiais, registros, fontes, dicionario)


def formatar_valor(r: Registro | None) -> str:
    if r is None:
        return "—"
    if r.valor is not None:
        return f"{r.valor:g}"
    if r.valor_min is not None and r.valor_max is not None:
        return f"{r.valor_min:g}–{r.valor_max:g}"
    return f"≥ {r.valor_min:g}" if r.valor_min is not None else f"≤ {r.valor_max:g}"


def relatorio_cobertura(base: Base) -> str:
    props = base.dicionario["propriedades"]
    nao_conferidos = sum(1 for r in base.registros if not r.conferido_por)
    linhas = [
        "# Base de dados dos materiais — cobertura",
        "",
        "Gerado automaticamente a partir de `materiais/` por "
        "`python -m capacete.materiais --relatorio`. Não editar à mão.",
        "",
        f"- Materiais: {len(base.materiais)}",
        f"- Registros: {len(base.registros)} "
        f"({nao_conferidos} ainda sem conferência por uma segunda pessoa)",
        f"- Fontes: {len(base.fontes)}",
        "",
        "## Propriedades essenciais por material",
        "",
        "Valor na menor frequência disponível (escolha conservadora). "
        "— indica lacuna.",
        "",
        "| Material | Classe | " + " | ".join(
            f"{props[p]['nome']} ({props[p]['unidade']})" for p in ESSENCIAIS) + " |",
        "|---|---|" + "---|" * len(ESSENCIAIS),
    ]
    for m in sorted(base.materiais.values(), key=lambda m: (m.classe, m.nome)):
        celulas = [formatar_valor(base.escolher(m.material_id, (p,))) for p in ESSENCIAIS]
        linhas.append(f"| {m.nome} | {m.classe} | " + " | ".join(celulas) + " |")
    linhas += ["", "## Lacunas das propriedades essenciais", ""]
    for m in sorted(base.materiais.values(), key=lambda m: m.nome):
        faltam = [props[p]["nome"].lower() for p in ESSENCIAIS
                  if not base.registros_de(m.material_id, p)]
        if "mu_r_inicial" in ESSENCIAIS and base.registros_de(m.material_id, "mu_r"):
            faltam = [f for f in faltam if "permeabilidade" not in f]
        if faltam:
            linhas.append(f"- **{m.nome}**: {', '.join(faltam)}")
    linhas += ["", "## Fontes", ""]
    for chave, fonte in base.fontes.items():
        linhas.append(f"- `{chave}`: {' '.join(fonte['referencia'].split())}")
    return "\n".join(linhas) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pasta", default=PASTA_PADRAO)
    parser.add_argument("--relatorio", help="grava o relatório de cobertura")
    args = parser.parse_args()
    base = carregar(args.pasta)
    if args.relatorio:
        Path(args.relatorio).write_text(relatorio_cobertura(base), encoding="utf-8")
        print(f"Relatório gravado em {args.relatorio}")
        return
    print(f"{len(base.materiais)} materiais, {len(base.registros)} registros, "
          f"{len(base.fontes)} fontes; {len(base.simulaveis())} materiais "
          f"com permeabilidade (simuláveis)")


if __name__ == "__main__":
    main()
