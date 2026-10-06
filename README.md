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

### Windows (Python 3.11)

Abra o PowerShell na pasta do projeto. Confirme que o Python 3.11 está disponível
no inicializador do Windows:

```powershell
py -3.11 --version
```

Se o comando `py` não estiver instalado, use o executável do Python 3.11
diretamente. No Python Install Manager, o caminho costuma ser:

```powershell
$python311 = "$env:LOCALAPPDATA\Python\pythoncore-3.11-64\python.exe"
& $python311 --version
& $python311 -m venv .venv
```

Nesse caso, pule o comando `py -3.11 -m venv .venv` abaixo.

Crie o ambiente virtual e instale as dependências do projeto:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

Inicie o simulador no navegador:

```powershell
.\.venv\Scripts\python.exe -m streamlit run interface/app_casca_esferica.py
```

Usar o executável dentro de `.venv` dispensa ativar o ambiente e evita
problemas com a política de execução de scripts do PowerShell. Para abrir o
projeto em outro terminal, repita esse último comando a partir da pasta do
repositório. Se `py -3.11 --version` não funcionar, instale Python 3.11 e marque
“Add Python to PATH” no instalador, ou use o Conda abaixo.

Com conda:

```bash
conda env create -f environment.yml
conda activate capacete-inteligente
pip install -e .
```

Ou com venv no Linux/macOS (Python 3.11):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
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

Na aba **Camadas sobrepostas**, escolha dois ou mais materiais da base e
defina a espessura de cada camada, do interior para o exterior. As camadas
formam uma única casca, sem espaço entre elas. O simulador calcula a blindagem
conjunta por FEM e por uma solução exata que conserva potencial e fluxo em
cada interface. Mostra também campo residual, massa, indução e saturação por
camada. O raio externo, campo aplicado e refino vêm da barra lateral.
Depois de simular, as seis abas internas apresentam **Mapa do campo**,
**Perfil do campo**, **Visão 3D**, **Efeito dos parâmetros**, **Base de materiais**
e **Entenda e experimente**, todas referentes à composição selecionada.
Os gráficos usam a solução exata de todas as interfaces, preservando os raios
reais das camadas. As curvas variam a espessura ou permeabilidade de uma camada
e mostram o efeito de inverter a ordem dos materiais. As abas externas continuam
disponíveis para a simulação de uma casca simples.

Ao alterar `requisitos/requisitos.yaml`, regenere `docs/requisitos_v1.md` e
rode os testes antes do commit.
