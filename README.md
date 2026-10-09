# Capacete Inteligente — plataforma vestível OPM-MEG

Modelagem computacional da blindagem magnética passiva e da compensação ativa
de uma plataforma craniana vestível para magnetoencefalografia com
magnetômetros opticamente bombeados (OPM-MEG). O objetivo é viabilizar
medições fora de salas magneticamente blindadas.

O projeto responde a três perguntas:

1. quanto campo chega aos locais dos OPMs;
2. quais materiais e geometrias de blindagem funcionam melhor;
3. qual compensação ativa será necessária para a condição de operação dos
   sensores.

## Situação

| Fase | Conteúdo | Situação |
|---|---|---|
| F0 | Requisitos e ambiente computacional | em andamento |
| F1 | Base de dados dos materiais | base v0.2: 24 materiais, 165 registros; extração assistida dos PDFs |
| F2 | Verificação e validação dos modelos | caso analítico pronto |
| F3 | Blindagem passiva no casco aberto | — |
| F4 | Resposta e ruído em 4–100 Hz | — |
| F5 | Camadas complementares | — |
| F6 | Compensação ativa | — |
| F7 | Desempenho integrado | — |
| F8 | Viabilidade térmica, mecânica e experimental | — |

Requisitos atuais: [`docs/requisitos_v1.md`](docs/requisitos_v1.md).
Pendências da Fase 0: [`docs/pendencias_fase0.md`](docs/pendencias_fase0.md).

## Estrutura

```
requisitos/   requisitos.yaml (fonte única dos requisitos) e convencoes.md
src/capacete/ código compartilhado (leitura e validação dos requisitos)
modelos/      modelos de simulação; verificacao/ contém os casos analíticos
materiais/    base de dados dos materiais (Fase 1): materiais, registros, fontes
resultados/   saídas geradas (não versionadas)
docs/         relatórios consolidados
tests/        testes automáticos
```

## Ambiente

Com conda:

```bash
conda env create -f environment.yml
conda activate capacete-inteligente
pip install -e .
```

A extração de valores dos PDFs usa o `pdftotext` (poppler): já vem no ambiente
conda; com venv, instale `poppler-utils` pelo gerenciador do sistema.

Ou com venv (Python 3.11):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Uso

```bash
pytest -q                                   # todos os testes
python -m capacete.requisitos               # resumo dos requisitos
python -m capacete.requisitos --markdown docs/requisitos_v1.md
python -m capacete.materiais --relatorio docs/materiais_cobertura.md
python -m capacete.extracao extrair PASTA_DOS_PDFS     # candidatos para a base
python -m capacete.extracao importar resultados/extracao/candidatos.csv --revisor NOME
python modelos/verificacao/verificacao_casca_esferica.py
python modelos/verificacao/casca_multicamada.py          # verificação multicamada
python modelos/verificacao/visualizar_casca_esferica.py   # gráficos didáticos
python modelos/verificacao/visualizar_casca_esferica_3d.py  # cena 3D interativa
```

## Interface gráfica (simulador didático)

```bash
streamlit run interface/app_casca_esferica.py
```

Abre no navegador um simulador de cascas esféricas com até quatro camadas.
Cada camada tem seu material (da base de dados ou personalizado), sua espessura
ou número de lâminas e o espaçamento até a próxima; há exemplos prontos com as
sequências do projeto (Fe–Co, Fe–Fe, Fe–Fe–Co, Fe–Fe–Co–Co). O simulador
mostra o fator de blindagem comparado com a solução exata para cascas
concêntricas, o campo no centro frente às metas do projeto, a indução e a
saturação em cada camada, a massa, o mapa do campo, o perfil, a cena 3D, as
curvas de efeito dos parâmetros (inclusive do espaçamento), a comparação das
sequências e exercícios guiados.

O modelo multicamada e sua solução exata (matrizes de transferência) estão em
`modelos/verificacao/casca_multicamada.py`; executá-lo imprime a tabela de
verificação.

Ao alterar `requisitos/requisitos.yaml`, regenere `docs/requisitos_v1.md` e
rode os testes antes do commit.
