# Convenções do projeto (v1)

Estas convenções valem para todos os modelos, dados e relatórios. Alterações
exigem nova versão deste arquivo e revisão dos resultados afetados.

## Unidades

- Cálculos internos no SI: T, A/m, m, s, kg, W, K.
- Arquivos de entrada podem usar unidades práticas (uT, nT, mm, cm), sempre
  com o campo `unidade` explícito. A conversão para o SI é feita pelo código
  (`capacete.requisitos.UNIDADES`), nunca à mão.
- Campos magnéticos são reportados como densidade de fluxo *B* (nT ou uT).
  Quando *H* for usado, informar a unidade (A/m).
- Densidade espectral de ruído em fT/sqrt(Hz), unilateral.
- Decibéis sempre pela razão entre amplitudes: dB = 20 log10(razão).

## Sistema de coordenadas

- Coordenadas de cabeça na convenção usual de MEG: origem no ponto médio entre
  os pontos pré-auriculares; **x** para o pré-auricular direito; **y** para o
  násio; **z** para o vértice (sistema dextrógiro).
- **Eixo axial** do casco: **z**, normal ao plano da abertura cervical.
  **Eixos transversais**: x e y.
- Modelos axissimétricos usam (rho, z), com o eixo de simetria em z.

## Campo aplicado

- Campo externo uniforme com amplitude R01 (90 uT), aplicado separadamente
  nos três eixos (x, y, z).
- Para representar a rotação da cabeça, varre-se a orientação do campo
  externo em relação ao casco.

## Métricas nos sensores

- **Volume sensível**: volume da célula de vapor de cada OPM, nas posições
  definidas em R14. A geometria e a profundidade da célula vêm da ficha técnica
  (pendência P-F1).
- **Campo residual por sensor**: módulo de *B* no volume sensível; reportar o
  valor máximo (critério de aceitação) e a média.
- **Fator de blindagem por sensor e por eixo**: SF = |B_ext| / |B_res|, com
  B_ext aplicado no eixo considerado e B_res avaliado no volume sensível.
- **Gradiente**: máximo de |dB_i/dx_j| no volume sensível, em nT/cm.
- **Margem de saturação**: razão entre a indução máxima no material e a
  indução de saturação, reportada por camada e por região (bordas e juntas).

## Arquitetura e nomenclatura

- Camadas numeradas de fora para dentro: 1 (aramida + EMI), 2 (Fe
  nanocristalino), 3 (Co amorfo), 4 (insertos MnZn), 5 (compensação ativa),
  6A (aerogel de grafeno), 6B (aerogel aramida/CNT com alojamentos dos OPMs).
- Sequências do núcleo passivo descritas de fora para dentro: Fe–Co, Fe–Fe,
  Fe–Fe–Co, Fe–Fe–Co–Co.
- Requisitos: `R01`…; fases: `F0`…`F8`; objetivos específicos: `O1`…`O10`.

## Arquivos e código

- Nomes de arquivos e identificadores em português, sem acentos, em
  `snake_case`.
- Parâmetros de simulação ficam em arquivos de configuração versionados, não
  no meio do código.
- Resultados gerados não são versionados (pasta `resultados/`), exceto
  relatórios consolidados em `docs/`.
