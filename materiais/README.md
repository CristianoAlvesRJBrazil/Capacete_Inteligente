# Base de dados dos materiais (Fase 1)

Base em formato longo: cada linha de `registros.csv` é uma medição de uma
propriedade, de um material, em uma condição.

| Arquivo | Conteúdo |
|---|---|
| `materiais.csv` | Um registro por material: classe, fabricante, grau, forma, processamento e fonte principal |
| `registros.csv` | As medições, com valor (ou faixa), unidade, condição, tipo de dado, fonte e localização na fonte |
| `dicionario.yaml` | Propriedades aceitas, unidade de cada uma e faixa de plausibilidade |
| `fontes.yaml` | Referência, URL e data de acesso de cada fonte |
| `validacao_blindagem.csv` | Fatores de blindagem medidos em montagens de 1 a 4 camadas, para validar o simulador (em construção) |

O relatório de cobertura, com as lacunas, fica em
[`docs/materiais_cobertura.md`](../docs/materiais_cobertura.md).

## Regras

- Nenhum valor sem unidade, condição de medição (quando a fonte informa),
  fonte e localização na fonte.
- Valor convertido de unidade guarda o valor original em `observacoes`.
- Faixas (por exemplo, "15.000 a 150.000") vão em `valor_min` e `valor_max`;
  limites ("< 3 A/m") usam só um deles.
- `tipo_dado`: `ficha_tecnica`, `norma`, `medido`, `digitalizado`, `calculado`
  ou `citado` (valor transcrito de outra fonte, ainda não conferido no original).
  `norma` é um limite garantido por especificação (por exemplo, MIL-N-14411C):
  mínimos vão em `valor_min` e máximos em `valor_max`.
- `conferido_por` só é preenchido depois que uma segunda pessoa confere o
  registro na fonte original.
- Os PDFs das fontes não são versionados; use as URLs de `fontes.yaml`.

## Como o simulador escolhe os valores

Para cada material, `capacete.materiais.Base.parametros_simulacao` escolhe o
registro na menor frequência informada, na temperatura mais próxima de 25 °C e,
no empate, o menor valor (escolha conservadora). Quando a fonte dá uma faixa,
usa o limite inferior. Um registro que só traz limite superior ("≤ X") fica por
último e, se for o único, o simulador avisa que o valor é otimista. Os avisos e os registros usados aparecem no simulador.

## Tabela de validação

`validacao_blindagem.csv` guarda uma montagem por linha, no mesmo formato de
entrada do simulador: a camada 1 é a externa, e `ck_espacamento_mm` é o
espaçamento até a camada seguinte, mais interna. Colunas de camadas que não
existem ficam vazias.

| Colunas | Conteúdo |
|---|---|
| `id_validacao`, `fonte_id`, `localizacao` | identificação e onde o dado está na fonte |
| `geometria` | `esfera`, `cilindro_fechado`, `cilindro_aberto` ou `outra` |
| `raio_cavidade_mm`, `comprimento_mm`, `aberturas` | dimensões; `aberturas` descreve furos e extremidades |
| `n_camadas`, `c1_…` a `c4_…` | por camada: `material_id`, `espessura_mm`, `laminas`, `mu_r` declarada e espaçamento |
| `fb_axial`, `fb_transversal` | fatores de blindagem informados |
| `campo_aplicado_uT`, `frequencia_Hz` | condição da medição |
| `tipo_dado` … `observacoes` | as mesmas regras de `registros.csv` |

As linhas virão da busca bibliográfica da Etapa 1 (blindagem passiva, seção
4.1 do artigo do projeto).

## Extração assistida a partir dos PDFs

`capacete.extracao` lê os PDFs dos artigos e propõe valores para a base. Nada
entra sem revisão:

1. `python -m capacete.extracao extrair PASTA_DOS_PDFS` lê cada PDF e grava em
   `resultados/extracao/`, fora do git:
   - `candidatos.csv`: um valor por linha, já convertido para a unidade do
     dicionário e dentro da faixa plausível, com página, trecho, condição
     (frequência, amplitude) e material detectado;
   - `candidatos_validacao.csv`: fatores de blindagem citados nos textos;
   - `relatorio_extracao.md`: o que saiu de cada PDF.

   Se a pasta tiver o `pdfs.csv` do agente pesquisador, o DOI e a referência
   de cada PDF vêm dele. Valores de frases que citam outro trabalho saem como
   `citado`. A coluna `registro_existente` compara com o que a base já tem da
   mesma fonte: serve para conferir no original os registros `citado`.
2. Abra `candidatos.csv`, confira cada linha no PDF e marque `s` em `aprovar`.
   `material_id` tem de existir em `materiais.csv`; cadastre o material antes,
   se for novo.
3. `python -m capacete.extracao importar resultados/extracao/candidatos.csv --revisor NOME`
   - acrescenta as linhas aprovadas a `registros.csv`, com `extraido_por` = revisor
     e `conferido_por` vazio, à espera da segunda pessoa;
   - cadastra em `fontes.yaml` as fontes novas;
   - valida a base inteira numa cópia antes de gravar: se algo falhar, nada muda;
   - regenera `docs/materiais_cobertura.md`.

   `--simular` só valida. Rodar de novo não duplica: as linhas importadas ficam
   marcadas em `importado`.

Os fatores de blindagem de `candidatos_validacao.csv` vão para
`validacao_blindagem.csv` à mão, porque a montagem (raios, espessuras,
espaçamentos) precisa ser lida no artigo.

A extração é por padrões de texto. Valores que só aparecem em tabelas ou em
figuras escapam, e PDF de imagem precisa de OCR antes.

## Comandos

```bash
python -m capacete.materiais                                  # valida e resume
python -m capacete.materiais --relatorio docs/materiais_cobertura.md
pytest -q tests/test_materiais.py
```

Depois de editar a base, regenere o relatório e rode os testes antes do commit.
