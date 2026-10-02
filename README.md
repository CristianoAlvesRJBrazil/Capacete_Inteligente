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
| F1 | Base de dados dos materiais | base v0.1: 21 materiais, 150 registros |
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
python modelos/verificacao/verificacao_casca_esferica.py
python modelos/verificacao/visualizar_casca_esferica.py   # gráficos didáticos
python modelos/verificacao/visualizar_casca_esferica_3d.py  # cena 3D interativa
```

## Interface gráfica (simulador didático)

```bash
streamlit run interface/app_casca_esferica.py
```

Abre no navegador um simulador da casca esférica: ajuste raio, espessura,
permeabilidade, campo externo e refino da malha; veja o fator de blindagem, a
comparação com a fórmula exata e com as metas do projeto, o mapa do campo, o
perfil, a cena 3D interativa, as curvas de efeito dos parâmetros e exercícios
guiados.

Ao alterar `requisitos/requisitos.yaml`, regenere `docs/requisitos_v1.md` e
rode os testes antes do commit.
