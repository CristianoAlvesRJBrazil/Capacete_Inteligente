# Base de dados dos materiais (Fase 1)

Base em formato longo: cada linha de `registros.csv` é uma medição de uma
propriedade, de um material, em uma condição.

| Arquivo | Conteúdo |
|---|---|
| `materiais.csv` | Um registro por material: classe, fabricante, grau, forma, processamento e fonte principal |
| `registros.csv` | As medições, com valor (ou faixa), unidade, condição, tipo de dado, fonte e localização na fonte |
| `dicionario.yaml` | Propriedades aceitas, unidade de cada uma e faixa de plausibilidade |
| `fontes.yaml` | Referência, URL e data de acesso de cada fonte |

O relatório de cobertura, com as lacunas, fica em
[`docs/materiais_cobertura.md`](../docs/materiais_cobertura.md).

## Regras

- Nenhum valor sem unidade, condição de medição (quando a fonte informa),
  fonte e localização na fonte.
- Valor convertido de unidade guarda o valor original em `observacoes`.
- Faixas (por exemplo, "15.000 a 150.000") vão em `valor_min` e `valor_max`;
  limites ("< 3 A/m") usam só um deles.
- `tipo_dado`: `ficha_tecnica`, `medido`, `digitalizado`, `calculado` ou
  `citado` (valor transcrito de outra fonte, ainda não conferido no original).
- `conferido_por` só é preenchido depois que uma segunda pessoa confere o
  registro na fonte original.
- Os PDFs das fontes não são versionados; use as URLs de `fontes.yaml`.

## Como o simulador escolhe os valores

Para cada material, `capacete.materiais.Base.parametros_simulacao` escolhe o
registro na menor frequência informada, na temperatura mais próxima de 25 °C e,
no empate, o menor valor (escolha conservadora). Quando a fonte dá uma faixa,
usa o limite inferior. Os avisos e os registros usados aparecem no simulador.

## Comandos

```bash
python -m capacete.materiais                                  # valida e resume
python -m capacete.materiais --relatorio docs/materiais_cobertura.md
pytest -q tests/test_materiais.py
```

Depois de editar a base, regenere o relatório e rode os testes antes do commit.
