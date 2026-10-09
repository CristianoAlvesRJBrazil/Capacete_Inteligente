# Base de dados dos materiais — cobertura

Gerado automaticamente a partir de `materiais/` por `python -m capacete.materiais --relatorio`. Não editar à mão.

- Materiais: 24
- Registros: 165 (165 ainda sem conferência por uma segunda pessoa)
- Fontes: 11

## Propriedades essenciais por material

Valor na menor frequência disponível (escolha conservadora). — indica lacuna.

| Material | Classe | Permeabilidade relativa inicial (campo baixo) (-) | Permeabilidade relativa máxima (-) | Indução (ou polarização) de saturação (T) | Densidade (g/cm3) | Espessura da fita ou lâmina (um) |
|---|---|---|---|---|---|---|
| Aço silício 3% orientado (comparativo Hitachi) | aco_silicio | 2700 | — | 1.9 | — | 230 |
| Co amorfo de alta permeabilidade (comparativo Hitachi) | co_amorfo | 115000 | — | 0.55 | — | 18 |
| Co amorfo de alta quadratura (comparativo Hitachi) | co_amorfo | 30000 | — | 0.6 | 7.7 | 18 |
| Fita Co amorfa CA (Liang et al. 2026) | co_amorfo | 247800 | 913000 | 0.39 | — | 25 |
| Fita Co amorfa MS-RMF (Qian et al. 2026) | co_amorfo | — | 400000 | — | — | — |
| Metglas 2705M | co_amorfo | — | 290000 | 0.77 | 7.8 | 22 |
| VITROVAC 6025 | co_amorfo | — | — | 0.53–0.59 | — | — |
| Fe amorfo (comparativo Hitachi) | fe_amorfo | 5000 | — | 1.56 | — | 25 |
| FINEMET FT-3H | fe_nanocristalino | 30000 | — | 1.23 | 7.3 | 18 |
| FINEMET FT-3L | fe_nanocristalino | 23000 | — | 1.23 | 7.3 | 18 |
| FINEMET FT-3M | fe_nanocristalino | 70000 | — | 1.23 | 7.3 | 18 |
| FINEMET FT-3S | fe_nanocristalino | 100000 | — | 1.23 | 7.3 | 18 |
| Fita Fe nanocristalina (Shen et al. 2026) | fe_nanocristalino | — | — | 1.2 | — | 20 |
| Fita Fe nanocristalina FN (Liang et al. 2026) | fe_nanocristalino | 38400 | 54400 | 1.25 | — | 25 |
| VITROPERM 500 F | fe_nanocristalino | 15000–150000 | — | 1.2 | — | 20 |
| Ferrita Mn0.6Zn0.4Fe2O4 (Liu et al. 2025) | ferrita_mnzn | 1536 | — | — | — | — |
| Ferrita MnZn MN80 (Ceramic Magnetics) | ferrita_mnzn | 2030 | — | — | — | — |
| Ferrita MnZn N87 (TDK) | ferrita_mnzn | 2200 | — | 0.49 | 4.85 | — |
| Ferrita MnZn de alta permeabilidade (comparativo Hitachi) | ferrita_mnzn | 10000 | — | 0.39 | — | — |
| Ferrita MnZn de baixa perda (comparativo Hitachi) | ferrita_mnzn | 2500 | — | 0.52 | — | — |
| MUMETALL | permalloy | 60000 | 150000 | 0.8 | 8.7 | 200 |
| Permalloy 80% Ni de alta permeabilidade (comparativo Hitachi) | permalloy | 50000 | — | 0.74 | — | 25 |
| ULTRAPERM 10 | permalloy | 150000 | 300000 | 0.74 | 8.7 | 100 |
| VACOPERM 100 | permalloy | 100000 | 250000 | 0.74 | 8.7 | 100 |

## Lacunas das propriedades essenciais

- **Aço silício 3% orientado (comparativo Hitachi)**: permeabilidade relativa máxima, densidade
- **Co amorfo de alta permeabilidade (comparativo Hitachi)**: permeabilidade relativa máxima, densidade
- **Co amorfo de alta quadratura (comparativo Hitachi)**: permeabilidade relativa máxima
- **FINEMET FT-3H**: permeabilidade relativa máxima
- **FINEMET FT-3L**: permeabilidade relativa máxima
- **FINEMET FT-3M**: permeabilidade relativa máxima
- **FINEMET FT-3S**: permeabilidade relativa máxima
- **Fe amorfo (comparativo Hitachi)**: permeabilidade relativa máxima, densidade
- **Ferrita Mn0.6Zn0.4Fe2O4 (Liu et al. 2025)**: permeabilidade relativa máxima, indução (ou polarização) de saturação, densidade, espessura da fita ou lâmina
- **Ferrita MnZn MN80 (Ceramic Magnetics)**: permeabilidade relativa máxima, indução (ou polarização) de saturação, densidade, espessura da fita ou lâmina
- **Ferrita MnZn N87 (TDK)**: permeabilidade relativa máxima, espessura da fita ou lâmina
- **Ferrita MnZn de alta permeabilidade (comparativo Hitachi)**: permeabilidade relativa máxima, densidade, espessura da fita ou lâmina
- **Ferrita MnZn de baixa perda (comparativo Hitachi)**: permeabilidade relativa máxima, densidade, espessura da fita ou lâmina
- **Fita Co amorfa CA (Liang et al. 2026)**: densidade
- **Fita Co amorfa MS-RMF (Qian et al. 2026)**: permeabilidade relativa inicial (campo baixo), indução (ou polarização) de saturação, densidade, espessura da fita ou lâmina
- **Fita Fe nanocristalina (Shen et al. 2026)**: densidade
- **Fita Fe nanocristalina FN (Liang et al. 2026)**: densidade
- **Metglas 2705M**: permeabilidade relativa inicial (campo baixo)
- **Permalloy 80% Ni de alta permeabilidade (comparativo Hitachi)**: permeabilidade relativa máxima, densidade
- **VITROPERM 500 F**: permeabilidade relativa máxima, densidade
- **VITROVAC 6025**: permeabilidade relativa inicial (campo baixo), permeabilidade relativa máxima, densidade, espessura da fita ou lâmina

## Fontes

- `hitachi_finemet_2010`: HITACHI METALS. Nanocrystalline soft magnetic material FINEMET. Catálogo HL-FM9-E, jul. 2010.
- `metglas_2705m_2014`: METGLAS INC. Magnetic Alloy 2705M (cobalt-based): Technical Bulletin, ref. 2705M08202014, 2014.
- `vac_pht001_2002`: VACUUMSCHMELZE. Soft Magnetic Materials and Semi-finished Products, PHT-001, ed. 2002.
- `vac_vitroperm_emc_2016`: VACUUMSCHMELZE. Nanocrystalline VITROPERM: EMC Products, 2016.
- `tdk_n87_2025`: TDK ELECTRONICS. Ferrites and accessories: SIFERRIT material N87. Data sheet, jun. 2025.
- `shen2026`: SHEN, P. et al. Fe-based nanocrystalline magnetic shielding cylinder with subfemtotesla-level magnetic noise. Advanced Science, v. 13, n. 17, art. e22435, 2026. DOI: 10.1002/advs.202522435.
- `qian2026`: QIAN, Y. et al. Exceptional magnetic shielding via ultra-low-remanence Co-based amorphous alloys engineered by atomic ordering. Materials Research Letters, v. 14, n. 7, p. 792-801, 2026. DOI: 10.1080/21663831.2026.2660809.
- `liuX2025`: LIU, X. et al. Fe2O3 composition optimization for MnZn ferrite and its magnetic noise evaluation for low-frequency magnetic shielding applications. Journal of Alloys and Compounds, v. 1035, art. 181418, 2025. DOI: 10.1016/j.jallcom.2025.181418.
- `metglas_site_2026`: METGLAS INC. Magnetic Materials (especificações das ligas). Página do fabricante.
- `liang2026`: LIANG, Y. et al. Multi-layer magnetic shields based on Fe-based nanocrystalline and Co-based amorphous ribbons. Materials, v. 19, n. 10, art. 1986, 2026. DOI: 10.3390/ma19101986.
- `kornack2007`: KORNACK, T. W.; SMULLIN, S. J.; LEE, S.-K.; ROMALIS, M. V. A low-noise ferrite magnetic shield. Applied Physics Letters, v. 90, n. 22, art. 223501, 2007. DOI: 10.1063/1.2737357.
