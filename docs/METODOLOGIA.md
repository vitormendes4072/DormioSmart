# DormioSmart — Metodologia científica

Referência para tudo que envolve validade científica do TCC. Ler antes de qualquer tarefa de ML, validação ou definição de escopo de pesquisa. Complementa o `CLAUDE.md` (operacional) e o `docs/HARDWARE.md`.

---

## Pergunta de pesquisa e hipótese

O `ROADMAP.md` **abre com a pergunta de pesquisa (RQ) e a hipótese** do TCC, fixadas no topo. Elas são a régua: todo item do roadmap deve poder ser justificado como serviço à RQ. Se um item não serve à pergunta, ou é cortado, ou a RQ é revista (com o orientador).

**A RQ já existe no documento atual** (em essência: como desenvolver um dispositivo embarcado de baixo consumo, instalado no travesseiro, capaz de registrar eventos de movimento ligados ao repouso de forma não invasiva, com viabilidade de evoluir de MVP simulado para protótipo físico). A tarefa não é inventá-la do zero, e sim **transcrevê-la para o topo do ROADMAP, confirmar/refinar com o orientador** e garantir que ela continua sendo a régua. Uma RQ boa é específica e verificável — fugir de formulações vagas ("monitorar o sono").

---

## Dataset público + ML — DECISÃO EM ABERTO

A ideia de usar uma base pública de sono e/ou ML **foi endossada pelo orientador** como forma de demonstrar viabilidade científica real (dado real, não só hipótese) — mas o COMO ainda precisa de validação metodológica final. Direção definida: dataset público para **validação/calibração** da detecção de movimento, **não** para replicar dados nem classificar estágios. O levantamento completo (candidatos, acesso, recomendação) está em **`docs/DATASET.md`**. Conclusão-chave: **não existe dataset exato** para o cenário travesseiro — o caminho é validar a *abordagem* em acelerometria de pulso (Walch 2019) + fundamentar o não-contato na literatura + gerar dado próprio na Fase 2.

Antes de implementar qualquer ML, precisam estar definidos e documentados aqui/em `docs/`:
- A pergunta científica que o modelo responde.
- O dataset escolhido (origem, licença, o que contém).
- A estratégia de validação.

**Riscos metodológicos a encarar:**
- O modelo pode só "decorar" o dataset (overfitting / falta de generalização).
- **Validade de construto:** os dados públicos correspondem ao que o MPU6050 mede de fato (movimento)? Se o dataset é de polissonografia ou de outro sensor, a ponte com acelerometria precisa ser justificada.
- O problema do **n=1** se os dados reais de validação vierem só do próprio autor.

**Reconciliar com a Fase 2:** o dispositivo real pode coletar dados próprios (ainda que n=1). Definir, no planejamento, o papel de cada fonte — dataset público para escala/treino vs. dados reais do protótipo para validação.

---

## Reprodutibilidade de ML — requisito, não sugestão

Quando o ML entrar (e só depois de RQ + dataset + validação definidos), ele nasce reprodutível. Resultado de ML que não roda igual de novo **não tem validade científica** e não defende um TCC. Obrigatório:

- **Seed fixa** em tudo que tem aleatoriedade (split, init, shuffle).
- **Split disciplinado treino/validação/teste**, decidido antes de olhar resultado. Cuidado com **vazamento**: se os dados têm estrutura temporal ou por sujeito, o split respeita isso — não embaralhar leituras da mesma noite/pessoa entre treino e teste.
- **Versionamento de dados:** registrar origem do dataset, versão e todo pré-processamento. O dado bruto não é editado no lugar.
- **Log de métricas e experimentos:** cada treino registra hiperparâmetros, métricas e data. Métrica apropriada ao problema — acurácia sozinha engana em classes desbalanceadas, e sono/vigília costuma ser desbalanceado (usar F1, matriz de confusão, etc.).
- **Ambiente pinado:** versões de bibliotecas fixadas para reproduzir noutra máquina.
- **Baseline honesto:** comparar contra um baseline trivial. Se um classificador burro acerta quase tanto, o modelo não está fazendo nada — melhor descobrir antes da banca.

---

## Validação científica — contra o quê você compara

Funcionar não é validar. "O dado aparece na tela" é teste funcional; **validação** é mostrar que a medição corresponde à realidade. Definir e documentar com o orientador:

- **Padrão de referência:** o gold standard de sono é a **polissonografia**, fora do alcance de um TCC. Reconhecer essa limitação e escolher referência viável — comparar contra wearable/app comercial, contra diário de sono autorreportado, ou validar apenas a tarefa mais modesta que o hardware sustenta (detecção movimento/repouso) em vez de prometer estadiamento (REM, sono profundo).
- **Escopo honesto da afirmação:** alinhar o que o projeto diz medir com o que o MPU6050 consegue. Subprometer e cumprir vale mais na banca que superprometer e furar.
- **Limitações no texto:** n=1 (se usar dados próprios), ausência de gold standard e generalização limitada entram como limitações declaradas — declarar fraqueza metodológica é sinal de maturidade, não de fracasso.

---

## Rastreabilidade científica

- Toda decisão técnica não óbvia deve ser registrável no texto do TCC. Ao concluir um item relevante, anotar o "porquê", não só o "o quê" (aqui, no `ROADMAP.md` ou em `docs/`).
- Manter em `docs/` a lista de referências/artigos usados de fato, separando os que **embasam** decisões dos que são apenas contexto.
- Não afirmar que um artigo sustenta uma escolha sem que ele tenha sido lido e citado corretamente. Sugestão de busca ≠ citação.

---

## Viabilidade do sensoriamento no travesseiro — o que a literatura sustenta

Pergunta de engenharia (não se responde com dataset): um acelerômetro no travesseiro consegue medir os eventos de movimento que o projeto se propõe a registrar? Avaliação honesta das fontes (detalhe e links em `docs/DATASET.md`):

**Comprovado (os blocos constituintes):**
- Acelerômetro mede movimento humano (TDK — é a função do componente).
- Movimento é proxy validado de repouso/atividade (actigrafia; SMITH et al., 2018 / AASM).
- Acelerometria **não-contato sob o colchão** capta postura e até sinais cardiorrespiratórios (MDPI Sensors, 2023/2025) — mais sutil do que o projeto exige.
- Um único MPU6050/GY-521 acoplado ao corpo classifica postura de sono (~93%).
- Movimento da cabeça carrega informação de sono (acelerômetro na cabeça).

**NÃO comprovado (o caso exato do projeto):**
- "Um acelerômetro **dentro do travesseiro** capta de forma confiável os eventos de movimento do sono" — não há estudo rigoroso. O único trabalho na configuração exata (SAI SURAJ et al., 2023, smart pillow + MPU6050) é de venue de baixa credibilidade e com poucos resultados quantitativos → **não é prova**.
- **Nuance física:** a evidência mais forte (sob colchão) tem acoplamento mecânico melhor — o corpo inteiro pesa sobre o colchão. O travesseiro tem só a cabeça → capta bem movimento da cabeça / mudança de posição que a envolve; **corpo rolando sem mexer a cabeça é a incógnita real**, a ser testada em bancada (item VIA-01 do `ROADMAP.md`).

**Como escrever no TCC:** *"abordagem fundamentada na literatura, a ser validada empiricamente pelo protótipo"* — **nunca "comprovado"** para o caso travesseiro. Subprometer e validar com dado próprio (Fase 2) é mais defensável na banca, e a ausência de dataset/estudo exato vira justificativa de contribuição original.
