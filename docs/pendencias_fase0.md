# Pendências da Fase 0

Informações necessárias para fechar os requisitos v1. Ao obter cada uma,
atualizar `requisitos/requisitos.yaml`, regenerar `docs/requisitos_v1.md`
(`python -m capacete.requisitos --markdown docs/requisitos_v1.md`) e marcar
o item aqui.

## Fabricante do OPM (ficha técnica do QZFM Gen-3)

- [ ] **P-F1** Dimensões do sensor e posição/dimensões da célula de vapor
      (R14, R16; volume sensível em `requisitos/convencoes.md`)
- [ ] **P-F2** Campo ambiente máximo de operação, para confirmar os 50 nT (R04)
- [ ] **P-F3** Faixa dinâmica após o zeramento, em malha aberta e fechada (R05)
- [ ] **P-F4** Largura de banda e ruído intrínseco em fT/sqrt(Hz) (R06, R08)
- [ ] **P-F5** Potência dissipada e temperatura de superfície do sensor
      (R12, R13)

## Decisões da equipe

- [ ] **P-E1** Número e posições dos OPMs (R14)
- [ ] **P-E2** Aplicação neurofisiológica que justifica a banda de 4–100 Hz
      (R06)
- [ ] **P-E3** Gradiente máximo admissível nos locais dos OPMs (R07)
- [ ] **P-E4** Ruído máximo introduzido por materiais e bobinas (R08)
- [ ] **P-E5** Temperatura máxima de contato e potência máxima (R12, R13)
- [ ] **P-E6** Requisitos de uso das aberturas facial e cervical: visão,
      respiração, equipamentos (R10)
- [ ] **P-E7** Faixa de frequências, níveis e norma de referência para
      RF/EMI (R11)
- [ ] **P-E8** Confirmação do orçamento de massa de 2,5 kg (R09)
- [ ] **P-E9** Dimensão anteroposterior do envelope, a partir de dados
      antropométricos (R15)

## Ambiente de aplicação

- [ ] **P-A1** Plano de medição do campo estático e das variações no ambiente-
      alvo, para substituir os 90 uT provisórios (R01)

## Ambiente computacional

- [x] Repositório com estrutura de pastas, requisitos e convenções
- [x] Dependências fixadas (`requirements.txt`) e instaláveis em ambiente
      limpo
- [x] Testes automáticos: validação dos requisitos e verificação da casca
      esférica (erro < 1%)
- [ ] Ambiente recriado em uma segunda máquina por outro membro da equipe
