# Requisitos de projeto — versão 1

Gerado automaticamente a partir de `requisitos/requisitos.yaml` por `python -m capacete.requisitos --markdown`. Não editar à mão.

| Id | Parâmetro | Valor | Situação | Fase | Objetivos | Origem |
|---|---|---|---|---|---|---|
| R01 | Campo magnético externo de projeto | 90 uT | provisorio | F0 | O1 | Objetivo O1; IGRF (Alken et al., 2021) |
| R02 | Campo residual nos locais dos OPMs (passivo + ativo) | 30 nT | definido | F7 | O9 | Objetivo O9 |
| R03 | Campo residual nos locais dos OPMs após a blindagem passiva | 400 nT | provisorio | F3 | O4 | Objetivo O4 |
| R04 | Campo ambiente máximo para operação do OPM (QZFM) | 50 nT | provisorio | F0 | O1, O9 | QuSpin, QZFM Gen-3 (acesso em 21/09/2026) |
| R05 | Variação de campo admissível após o zeramento do OPM | a definir | a_definir | F0 | O1, O9 | Ficha técnica do QZFM |
| R06 | Banda de análise das medições neurofisiológicas | 4–100 Hz | definido | F4 | O6 | Objetivo O6 |
| R07 | Gradiente máximo nos locais dos OPMs | a definir | a_definir | F0 | O1, O9 | Objetivos O1 e O9 |
| R08 | Ruído magnético introduzido por materiais e bobinas | a definir | a_definir | F0 | O6, O8 | Objetivos O6 e O8 |
| R09 | Massa total da plataforma | 2.5 kg | provisorio | F8 | O10 | Plano de física computacional (Tabela 2) |
| R10 | Geometria das aberturas facial e cervical | a definir | a_definir | F3 | O5 | Objetivo O5 |
| R11 | Proteção RF/EMI do sistema de medição | a definir | a_definir | F5 | O7 | Objetivo O7 |
| R12 | Temperatura máxima de contato com o escalpo | a definir | a_definir | F0 | O10 | Objetivo O10 |
| R13 | Potência máxima dissipada (OPMs e bobinas) | a definir | a_definir | F0 | O8, O10 | Objetivo O10 |
| R14 | Número e posições dos OPMs | a definir | a_definir | F0 | O1 | Objetivo O1 |
| R15 | Diâmetro transversal do envelope inicial de modelagem | 24 cm | provisorio | F0 | O1, O5 | Revisão de materiais v3.0; Liu et al. (2026) |
| R16 | Distância entre a face sensora do OPM e o escalpo | 3–4 mm | provisorio | F0 | O1 | Revisão de materiais v3.0 |

## Fatores de blindagem derivados

| Fator | Valor | dB |
|---|---|---|
| Total (R01/R02) | 3000 | 69.5 |
| Passivo (R01/R03) | 225 | 47.0 |
| Ativo (R03/R02) | 13.3 | 22.5 |

## Pendências

- **R01** (provisorio, F0) Campo magnético externo de projeto: Condição conservadora de projeto, cerca de 40% acima do limite geomagnético superior (~65 uT); sujeita à caracterização do ambiente de aplicação.
- **R04** (provisorio, F0) Campo ambiente máximo para operação do OPM (QZFM): Valor informado pelo fabricante; confirmar na ficha técnica da geração de sensor adotada.
- **R05** (a_definir, F0) Variação de campo admissível após o zeramento do OPM: Define o limite das flutuações durante o movimento, distinto do campo estático de operação (R04).
- **R07** (a_definir, F0) Gradiente máximo nos locais dos OPMs: Limite compatível com a medição dos sinais biomagnéticos.
- **R08** (a_definir, F0) Ruído magnético introduzido por materiais e bobinas: Comparado ao ruído intrínseco dos OPMs na banda R06.
- **R12** (a_definir, F0) Temperatura máxima de contato com o escalpo: Inclui o calor dos OPMs e das bobinas.
- **R13** (a_definir, F0) Potência máxima dissipada (OPMs e bobinas): Entrada do orçamento térmico e do dimensionamento das bobinas.
- **R14** (a_definir, F0) Número e posições dos OPMs: Define os volumes em que o campo residual e os gradientes são avaliados.
- **R15** (provisorio, F0) Diâmetro transversal do envelope inicial de modelagem: Envelope inicial de modelagem; a dimensão anteroposterior deve ser definida por dados antropométricos, altura dos sensores e camadas.
- **R16** (provisorio, F0) Distância entre a face sensora do OPM e o escalpo: Confirmar se a distância é medida até a face do sensor ou até o centro da célula de vapor.
- **R03** (provisorio, F3) Campo residual nos locais dos OPMs após a blindagem passiva: Meta preliminar intermediária que subsidia o dimensionamento da compensação ativa; viabilidade a verificar por simulação e ensaio.
- **R10** (a_definir, F3) Geometria das aberturas facial e cervical: Definida pelos requisitos de uso; efeito magnético quantificado por simulação; nenhuma porcentagem de área fixada a priori.
- **R11** (a_definir, F5) Proteção RF/EMI do sistema de medição: Faixa de frequências, níveis e condições de ensaio mensuráveis (por exemplo, MIL-STD-461G), ligados à proteção do sistema de medição.
- **R09** (provisorio, F8) Massa total da plataforma: Proposta preliminar; o orçamento inclui sensores, bobinas, cabos, estrutura e demais componentes.
