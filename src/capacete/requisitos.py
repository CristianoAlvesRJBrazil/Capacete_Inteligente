"""Leitura, validação e relatório dos requisitos de projeto (Fase 0).

Uso:
    python -m capacete.requisitos                  # resumo no terminal
    python -m capacete.requisitos --markdown ARQ   # relatório em Markdown
"""
from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
ARQUIVO_PADRAO = RAIZ / "requisitos" / "requisitos.yaml"

SITUACOES = ("definido", "provisorio", "a_definir")
FASES = tuple(f"F{i}" for i in range(9))
OBJETIVOS = tuple(f"O{i}" for i in range(1, 11))

# Fator multiplicativo para o SI; None indica unidade aceita sem conversão.
UNIDADES = {
    "uT": 1e-6, "nT": 1e-9, "mm": 1e-3, "cm": 1e-2, "kg": 1.0, "Hz": 1.0,
    "W": 1.0, "nT/cm": 1e-7, "fT/sqrt(Hz)": 1e-15, "degC": None, "-": None,
}
CAMPOS_TEXTO = ("id", "chave", "parametro", "unidade", "situacao",
                "justificativa", "origem", "fase_responsavel")


class RequisitoInvalido(ValueError):
    """Erro de conteúdo ou de formato no arquivo de requisitos."""


@dataclass(frozen=True)
class Requisito:
    id: str
    chave: str
    parametro: str
    valor: float | list | None
    unidade: str
    situacao: str
    justificativa: str
    origem: str
    fase_responsavel: str
    objetivos: tuple

    def em_si(self) -> float:
        """Valor escalar convertido para o SI."""
        fator = UNIDADES[self.unidade]
        if fator is None or not isinstance(self.valor, (int, float)):
            raise RequisitoInvalido(f"{self.id}: valor sem conversão escalar")
        return self.valor * fator


def _validar(item: dict) -> Requisito:
    rid = item.get("id", "?")
    faltando = [c for c in CAMPOS_TEXTO if not str(item.get(c) or "").strip()]
    if faltando:
        raise RequisitoInvalido(f"{rid}: campos ausentes {faltando}")
    if not re.fullmatch(r"R\d{2}", item["id"]):
        raise RequisitoInvalido(f"{rid}: id deve seguir o padrão R00")
    if item["situacao"] not in SITUACOES:
        raise RequisitoInvalido(f"{rid}: situação '{item['situacao']}'")
    if item["unidade"] not in UNIDADES:
        raise RequisitoInvalido(f"{rid}: unidade '{item['unidade']}'")
    if item["fase_responsavel"] not in FASES:
        raise RequisitoInvalido(f"{rid}: fase '{item['fase_responsavel']}'")
    objetivos = tuple(item.get("objetivos") or ())
    if not objetivos or not set(objetivos) <= set(OBJETIVOS):
        raise RequisitoInvalido(f"{rid}: objetivos {objetivos}")
    valor = item.get("valor")
    if (valor is None) != (item["situacao"] == "a_definir"):
        raise RequisitoInvalido(
            f"{rid}: valor nulo se, e somente se, a situação for a_definir")
    if isinstance(valor, list) and not (
            len(valor) == 2 and valor[0] < valor[1]):
        raise RequisitoInvalido(f"{rid}: intervalo deve ser [min, max]")
    campos = {c: item[c] for c in CAMPOS_TEXTO}
    return Requisito(valor=valor, objetivos=objetivos, **campos)


def carregar(caminho: Path | str = ARQUIVO_PADRAO) -> dict[str, Requisito]:
    """Lê e valida o arquivo; retorna os requisitos indexados pela chave."""
    dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))
    reqs = [_validar(item) for item in dados["requisitos"]]
    for nome in ("id", "chave"):
        valores = [getattr(r, nome) for r in reqs]
        repetidos = {v for v in valores if valores.count(v) > 1}
        if repetidos:
            raise RequisitoInvalido(f"{nome} repetido: {sorted(repetidos)}")
    return {r.chave: r for r in reqs}


def fatores_blindagem(reqs: dict[str, Requisito]) -> dict[str, float]:
    """Fatores de blindagem derivados dos requisitos de campo (Eq. 1)."""
    externo = reqs["campo_externo"].em_si()
    final = reqs["campo_residual_final"].em_si()
    passivo = reqs["campo_residual_passivo"].em_si()
    fatores = {"total": externo / final, "passivo": externo / passivo,
               "ativo": passivo / final}
    fatores.update({f"{k}_dB": 20 * math.log10(v)
                    for k, v in list(fatores.items())})
    return fatores


def pendencias(reqs: dict[str, Requisito]) -> list[Requisito]:
    """Requisitos ainda não definidos, ordenados por fase e id."""
    abertos = [r for r in reqs.values() if r.situacao != "definido"]
    return sorted(abertos, key=lambda r: (r.fase_responsavel, r.id))


def _valor_texto(r: Requisito) -> str:
    if r.valor is None:
        return "a definir"
    if isinstance(r.valor, list):
        texto = f"{r.valor[0]:g}–{r.valor[1]:g}"
    else:
        texto = f"{r.valor:g}"
    return texto if r.unidade == "-" else f"{texto} {r.unidade}"


def relatorio_markdown(reqs: dict[str, Requisito]) -> str:
    f = fatores_blindagem(reqs)
    linhas = [
        "# Requisitos de projeto — versão 1",
        "",
        "Gerado automaticamente a partir de `requisitos/requisitos.yaml` "
        "por `python -m capacete.requisitos --markdown`. Não editar à mão.",
        "",
        "| Id | Parâmetro | Valor | Situação | Fase | Objetivos | Origem |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(reqs.values(), key=lambda r: r.id):
        linhas.append(
            f"| {r.id} | {r.parametro} | {_valor_texto(r)} | {r.situacao} | "
            f"{r.fase_responsavel} | {', '.join(r.objetivos)} | {r.origem} |")
    linhas += [
        "",
        "## Fatores de blindagem derivados",
        "",
        "| Fator | Valor | dB |",
        "|---|---|---|",
        f"| Total (R01/R02) | {f['total']:.0f} | {f['total_dB']:.1f} |",
        f"| Passivo (R01/R03) | {f['passivo']:.0f} | {f['passivo_dB']:.1f} |",
        f"| Ativo (R03/R02) | {f['ativo']:.1f} | {f['ativo_dB']:.1f} |",
        "",
        "## Pendências",
        "",
    ]
    for r in pendencias(reqs):
        linhas.append(f"- **{r.id}** ({r.situacao}, {r.fase_responsavel}) "
                      f"{r.parametro}: {r.justificativa}")
    return "\n".join(linhas) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arquivo", default=ARQUIVO_PADRAO)
    parser.add_argument("--markdown", help="grava o relatório neste arquivo")
    args = parser.parse_args()
    reqs = carregar(args.arquivo)
    if args.markdown:
        Path(args.markdown).write_text(relatorio_markdown(reqs),
                                       encoding="utf-8")
        print(f"Relatório gravado em {args.markdown}")
        return
    f = fatores_blindagem(reqs)
    print(f"{len(reqs)} requisitos; {len(pendencias(reqs))} pendentes")
    print(f"SF total = {f['total']:.0f} ({f['total_dB']:.1f} dB); "
          f"passivo = {f['passivo']:.0f}; ativo = {f['ativo']:.1f}")


if __name__ == "__main__":
    main()
