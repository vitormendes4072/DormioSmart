# DormioSmart — Levantamento de datasets públicos (DEC-01)

> Fonte da verdade do item **DEC-01**. Resultado da pesquisa feita em 2026-05-31.
> Complementa `docs/METODOLOGIA.md` (validade científica) e o `ROADMAP.md`.
> O orientador endossou usar dataset público para demonstrar **viabilidade científica real**,
> não apenas hipótese. Este documento define COMO fazer isso com rigor.

---

## Conclusão direta

**Não existe um dataset público que corresponda exatamente ao cenário do DormioSmart**
(um acelerômetro embutido no travesseiro, captando movimento durante o sono, com rótulos).
Há um motivo estrutural: esse dado exigiria rodar **polissonografia (ou outra referência)
simultânea a um sensor no travesseiro** em várias pessoas — estudo clínico-de-engenharia
caro e raro.

**Isso NÃO indica inviabilidade** (ver `METODOLOGIA.md` → "Viabilidade do sensoriamento no
travesseiro"). A ausência de dataset é uma questão de *publicação de dados*, não de *física do
sensor*. Em engenharia aplicada, a prova de viabilidade é o **protótipo medindo + dado próprio**,
não um dataset pré-existente.

> Ressalva: não é possível provar uma negativa universal. Pode haver dataset solto em
> GitHub/Kaggle não indexado. Mas, após busca ampla (vários termos + Kaggle, Zenodo,
> IEEE DataPort, Mendeley, Figshare, PhysioNet, NSRR, GitHub), nada exato apareceu.

---

## Panorama: o que existe se divide em três eixos (e nada combina os três)

| Eixo | Mais próximo encontrado | Por que não serve de cara | Disponível? |
|---|---|---|---|
| **Mesmo sensor** (MPU6050/IMU) | `Human-Posture-Dataset` (GitHub): MPU-6050 no peito+coxa, 6 posturas incl. "dormindo", 44.800 amostras CSV. Paper c/ GY-521 no abdômen (KNN ~93%) | Postura corporal **vestida**, não uma noite de sono; "dormindo" é pose estática | ✅ (GitHub) |
| **Mesma posição** (não-contato na cama) | Smart-bed com **8 acelerômetros triaxiais sob o colchão** (MDPI Sensors 2025, 25 voluntários, 6 posturas, >90%); under-mattress cardiorrespiratório (MDPI Sensors 2023) | São **papers** (dado bruto aparentemente não liberado); tarefa = postura/respiração; é *array* sob o colchão, não 1 sensor no travesseiro | ❌ (papers) |
| **Mesma tarefa** (sono rotulado, noite) | **Walch 2019 (sleep-accel)**: accel bruto (g) + HR, 31 sujeitos, rótulo PSG; **CAPTURE-24**: pulso, 151 pessoas, 2562 h anotadas; MESA/UK Biobank (DUA); paper de **estágios por acelerômetro na cabeça** | Sensor **vestido** (pulso/cabeça), não travesseiro | ✅ Walch/CAPTURE-24 |
| **Vindo aí** | **OxWEARS**: estudo em andamento que inclui **sensor sob o colchão**; coleta termina em 2026, liberação pública prometida depois | Ainda não existe; não dá para contar com ele agora | ⏳ |

---

## Recomendação para o DEC-01

O caminho realista **não** é "achar o dataset perfeito" (não existe), e sim combinar três fontes
com papéis distintos:

1. **Validar a *abordagem* (movimento → repouso/atividade) — Walch 2019 (sleep-accel).**
   Acelerometria humana real com rótulo PSG (padrão-ouro). Permite demonstrar que a lógica de
   detecção funciona sobre dado real e comparar contra um baseline trivial. É o que atende o
   pedido do orientador ("viabilidade real, não só hipótese").
2. **Fundamentar o não-contato (ponte de construto) — papers de colchão/cabeça (MDPI; head-accel).**
   Citação na fundamentação (FUND-01), não treino. Sustenta que acelerometria não-contato na cama
   é viável.
3. **Gerar dado próprio na Fase 2 — protótipo no travesseiro (mesmo n=1).**
   É a única fonte no construto real do projeto e vira **contribuição original** do TCC
   (preenche a lacuna identificada aqui; potencialmente publicável).

### Validade de construto — o limite a declarar
Todos os datasets bons são de **pulso/corpo**; o sensor do projeto é **não-contato no travesseiro**.
Logo, o dataset valida a **abordagem/algoritmo**, NÃO o sensor naquela posição. Formulação honesta
para o texto:

> "Validamos a abordagem de detecção de movimento→repouso sobre acelerometria de pulso com
> referência PSG (Walch et al., 2019). A transferência para um sensor não-contato no travesseiro
> é uma limitação declarada, endereçada pelas capturas próprias (n=1) do protótipo na Fase 2."

### Rigor obrigatório (de `METODOLOGIA.md`)
Seed fixa · split **por sujeito** (não embaralhar noites/pessoas entre treino e teste) ·
baseline trivial honesto · métricas além de acurácia (F1, matriz de confusão; sono/vigília é
desbalanceado) · versionamento de dados e ambiente pinado.

---

## Candidatos — detalhe e acesso

- **Walch et al., 2019 — "Motion and heart rate from a wrist-worn wearable and labeled sleep
  from polysomnography" (sleep-accel).** PhysioNet (aberto — confirmar licença na página) e NSRR.
  31 sujeitos, accel triaxial bruto (g) + HR, rótulo PSG (AASM). **Candidato principal.**
- **BIDSLEEP.** PhysioNet. Apple Watch multi-noite + rótulo EEG (Dreem 2). Bom para robustez.
- **CAPTURE-24.** Pulso (Axivity AX3, 100 Hz, ±8g), 151 participantes, 2562 h anotadas + diário
  de sono. Free-living (não é sono em laboratório).
- **NSRR — MESA / MrOS.** Actigrafia de pulso + PSG, milhares de sujeitos. Exige cadastro/DUA
  (burocracia — não cabe em prazo curto).
- **Não-contato (citação, não treino):** smart-bed com array sob colchão (MDPI Sensors 2025);
  under-mattress cardiorrespiratório (MDPI Sensors 2023); estágios por acelerômetro na cabeça.
- **MPU6050 vestido (referência de método):** Human-Posture-Dataset (GitHub).

---

## Fontes

- Walch 2019 — sleep-accel (PhysioNet): https://physionet.org/content/sleep-accel/1.0.0/
- NSRR — sleepaccel: https://www.sleepdata.org/datasets/sleepaccel
- Walch et al., SLEEP 2019 (PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC6930135/
- BIDSLEEP (PhysioNet): https://physionet.org/content/bidsleep-dataset/1.0.0/
- CAPTURE-24 (arXiv): https://arxiv.org/pdf/2402.19229
- DPSleep — análise de sono por acelerômetro (PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC8529474/
- Smart-bed: array de acelerômetros sob colchão (MDPI Sensors 2025): https://www.mdpi.com/1424-8220/25/12/3609
- Under-mattress cardiorrespiratório (MDPI Sensors 2023): https://pmc.ncbi.nlm.nih.gov/articles/PMC10256009/
- Estágios de sono por acelerômetro na cabeça (PMC): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7867075/
- Human-Posture-Dataset (GitHub, MPU-6050): https://github.com/pkmandke/Human-Posture-Dataset
- OxWEARS (protocolo, PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC12747664/

---

## Status

- [ ] **DEC-01** pendente de validação final com o orientador (direção já endossada: dataset
      público como **validação/calibração**, não replicação nem estadiamento).
- Decisão registrada aqui é a recomendação técnica; a palavra final é do orientador.
