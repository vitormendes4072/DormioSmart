# Limitações do trabalho — texto pronto para o TCC (`DOC-06`)

> **Como usar este arquivo.** O que está entre as linhas `── TEXTO ──` é redigido em tom
> acadêmico e pode ser colado no documento com ajustes mínimos de numeração e de referência.
> O que está fora delas são **notas para você**, não para o texto final.
>
> **Fundamentação:** todos os números vêm de `docs/ML-DATASETS-E-PLANO.md` §0, onde cada um
> está atrelado à sua fonte e à população em que foi medido. **Confira as citações contra o
> §0 antes de submeter.**
>
> ✅ **Atualizado em 2026-09-10.** Autoria, ano, veículo e DOI de todas as referências foram
> confirmados na fonte. Os marcadores `(REFERÊNCIA — …)` deste texto foram substituídos por
> citações autor-data. **Três coisas mudaram de conteúdo**, não só de forma — estão marcadas
> com 🔧 nas notas ao final e devem ser lidas antes de colar.
>
> ✅ **Atualizado em 2026-09-21 com números medidos.** As seções X.3 (lateralidade) e X.4
> (degradação entre coortes, ganho que atravessa coorte, nº de coortes) passaram a conter
> resultados **medidos neste trabalho**, não mais só limitações antecipadas. A procedência de
> cada número está em "O que entrou na medição de 2026-09-21", ao final. Diferentemente do
> restante do arquivo, esses números **não vêm da literatura**: vêm de
> `ml/experimentos/saida/*.json` e podem ser reproduzidos com os comandos ali listados.
>
> ✅ **Alinhado em 2026-09-28 com o `docs/RESULTADOS-TCC.md`.** Três mudanças, todas de
> alinhamento numérico com os JSONs, nenhuma de conteúdo:
> 1. **X.3** — o IC do Δκ de lateralidade passou de `−0,015` para **`−0,014`**. O valor no JSON
>    é −0,014499; o arredondamento anterior estava para cima. O `RESULTADOS-TCC.md` já usava
>    −0,014, e os dois documentos agora dizem o mesmo número.
> 2. **X.4** — a prevalência da base de desenvolvimento passou de "aproximadamente 0,85" para
>    **0,895**, que é o valor medido (`prevalencia_sono` em `ml03_transferencia_*.json`). A da
>    coorte externa passou de "aproximadamente 0,70" para **0,699**, idem.
> 3. **X.4** — um parágrafo novo registra que o **teto de concordância entre pontuadores** foi
>    medido na base de desenvolvimento (κ = 0,612), mas **não existe** para a coorte externa, que
>    não publica segunda pontuação. Consequência declarada: a degradação de κ e de especificidade
>    não pode ser decomposta entre perda do método e diferença de concordância da rotulagem.
>    Este é o único acréscimo de conteúdo, e ele *acrescenta* uma limitação.
>
> ⚠️ **Seção nova em 2026-10-20: X.7, "Limitações de segurança da camada de autenticação".** É a
> primeira limitação deste arquivo que **não é sobre medição** — é sobre o sistema como software
> em uso. Declara que o sistema não atende ao requisito de não-dedutibilidade de usuários válidos
> (ASVS 5.0 § 6.3.8, **Nível 3**), em quatro canais, **dos quais dois não foram medidos neste
> trabalho e dizem isso no próprio texto**. **Leia "O que entrou em 2026-10-20", ao final, antes
> de colar:** há três ressalvas de citação obrigatórias, uma delas sobre citar uma norma **por
> ausência**. Referências novas da seção **não vêm do §0** — a lista está naquela nota.
>
> **Sugestão de posição:** seção própria ao final do desenvolvimento, antes das
> Considerações Finais. Declarar limitação num lugar só, de forma organizada, é sinal de
> maturidade metodológica — espalhá-las pelo texto parece tentativa de diluí-las.

---

## Nota de enquadramento (leia antes de colar)

O texto abaixo assume a **afirmação máxima honesta** do trabalho:

> O dispositivo registra eventos de movimento durante o repouso de forma não invasiva e, a
> partir deles, estima o período de repouso e sua fragmentação, com desempenho da ordem do
> que a literatura de actigrafia reporta — reconhecidamente limitado na discriminação de
> vigília quieta, com tendência conhecida a superestimar o tempo de sono, e sem qualquer
> estadiamento de sono.

Se o texto do TCC afirmar mais que isso em qualquer outro ponto, **é o outro ponto que
precisa mudar**, não esta seção.

---

── TEXTO ────────────────────────────────────────────────────────────────────

## X. Limitações

Esta seção reúne as limitações do trabalho de forma explícita. Parte delas decorre de
escolhas de escopo; parte decorre de restrições físicas do princípio de medição adotado e,
portanto, não seria superada por refinamento de implementação. A distinção entre as duas
naturezas é feita ao longo do texto, por ser relevante para a interpretação dos resultados
e para trabalhos futuros.

### X.1 Limitações do princípio de medição

O dispositivo baseia-se em acelerometria, isto é, no registro de movimento. A inferência de
estados de repouso a partir de movimento é a premissa da **actigrafia**, método consolidado
e reconhecido na literatura de medicina do sono, mas cujos limites são bem documentados e
se aplicam integralmente a este trabalho.

**Discriminação da vigília em repouso.** A limitação central da actigrafia é a
impossibilidade de distinguir vigília quieta de sono: um indivíduo desperto, deitado e
imóvel produz o mesmo sinal de aceleração que um indivíduo adormecido. Revisão sistemática
sobre o tema registra que a actigrafia "mede apenas movimento de membro periférico, usando
atividade como *proxy* de vigília e inatividade como *proxy* de sono e, por extensão, tem
capacidade limitada de inferir os estágios do sono, pela ausência de sinais fisiológicos"
(YUAN et al., 2024, tradução nossa).

Essa limitação manifesta-se de forma assimétrica nas métricas de desempenho. A
**sensibilidade** (capacidade de identificar corretamente épocas de sono) situa-se
consistentemente alta, enquanto a **especificidade** (capacidade de identificar corretamente
épocas de vigília) apresenta variação ampla. Meta-análise de 96 estudos reporta, no
agrupamento de 49 estudos com análise época a época (n = 1 582), sensibilidade média de 83%
(DP 12,0), especificidade média de 51% (DP 19) e acurácia média de 82% (DP 7) (CONLEY et
al., 2019). Nos estudos individuais, a dispersão da especificidade é ainda mais evidente: em
validação de actígrafo de grau clínico contra polissonografia, a especificidade relatada foi
de 33,1%, com sensibilidade de 94,8% (LI; HALAKI; CHOW, 2025); em abordagem baseada
exclusivamente em aceleração bruta, com extração de características derivadas do *jerk*,
foram relatadas sensibilidade de 96,13 ± 5,61% e especificidade de 80,18 ± 12,71% (ODE et
al., 2022) — cabendo observar que o desvio-padrão da especificidade indica desempenho
substancialmente inferior em parte dos indivíduos.

**Viés sistemático de superestimação.** Como consequência direta do exposto acima, a
actigrafia tende a superestimar o tempo total de sono, e o faz de modo desigual conforme a
população. Meta-análise que reuniu 96 estudos e 4 134 participantes relatou, em adultos com
condições crônicas, superestimação estatisticamente significativa do tempo total de sono
(+22,42 minutos; IC 95%: 11,92 a 32,91) e da eficiência do sono (+5,21%; IC 95%: 1,41 a
9,00). Em adultos saudáveis, os autores registram apenas uma **tendência não
estatisticamente significativa** de superestimação (+11,23 minutos; IC 95%: −3,98 a 26,44
para o tempo total de sono) (CONLEY et al., 2019). Em populações com insônia, síntese da
literatura reporta superestimação do tempo total de sono na faixa de 14 a 60 minutos
(PAQUET; KAWINSKA; CARRIER, 2007). Registra-se ainda que a acurácia do método declina
conforme aumenta a severidade do distúrbio de sono (LI; HALAKI; CHOW, 2025), o que configura
uma limitação de particular relevância: a precisão da medida é menor justamente na população
para a qual a medida seria mais informativa.

### X.2 Ausência de estadiamento do sono

O trabalho **não realiza estadiamento do sono** — isto é, não classifica os estágios N1, N2,
N3 e REM. Trata-se de uma limitação de natureza física, e não algorítmica, razão pela qual
não seria superada por modelos mais sofisticados aplicados ao mesmo sinal.

Os estágios do sono não invasivo definem-se por fenômenos que a acelerometria não capta. Os
estágios N1, N2 e N3 distinguem-se por padrões de **atividade cortical** — fusos do sono,
complexos K e ondas delta —, mensuráveis por eletroencefalografia na ordem de microvolts. O
estágio REM caracteriza-se pela combinação de **movimentos oculares rápidos**, registrados
por eletro-oculografia, com **atonia da musculatura esquelética**, registrada por
eletromiografia. Nenhum desses fenômenos possui assinatura mecânica detectável por um
acelerômetro acoplado ao travesseiro. Cabe destacar, adicionalmente, que os estágios REM e
N3 correspondem ambos a estados de baixa atividade motora, sendo portanto indistinguíveis
entre si por esse princípio de medição.

A literatura sustenta que a discriminação entre REM e NREM em dispositivos vestíveis se
apoia predominantemente em marcadores do **sistema nervoso autônomo**, notadamente a
variabilidade da frequência cardíaca. WALCH et al. (2019), ao avaliarem a contribuição de
diferentes modalidades de sensor, obtiveram acurácia de aproximadamente 72% na classificação
entre vigília, NREM e REM utilizando conjuntamente movimento, frequência cardíaca obtida por
fotopletismografia e um marcador do ritmo circadiano. O dispositivo desenvolvido neste
trabalho não dispõe de medição de frequência cardíaca, pela razão discutida na seção X.5.

### X.3 Limitações decorrentes da posição do sensor

O sensor é acoplado ao travesseiro, sem contato com o corpo do usuário. Essa escolha atende
ao requisito de não invasividade que orienta o trabalho, mas implica limitações que devem
ser declaradas.

**Acoplamento mecânico.** O travesseiro constitui meio complacente e amortecedor, e registra
sobretudo o movimento que efetivamente o solicita — predominantemente movimentos de cabeça e
mudanças de posição que a envolvam. Movimentos corporais que não desloquem a cabeça tendem a
ser subcaptados. A magnitude dessa subcaptação constitui questão empírica em aberto,
endereçada pelo protocolo de bancada descrito na seção (REFERÊNCIA INTERNA — item VIA-01).

**Comparação com a posição de pulso.** A literatura de posicionamento de acelerômetros
indica que o punho apresenta acurácia superior a posições próximas ao centro de massa para a
tarefa de discriminação sono/vigília, tendo sido relatada acurácia majoritariamente superior
a 80% no punho contra valores geralmente inferiores a 80% em cintura, coxa e região lombar
(MEREDITH-JONES et al., 2024; ressalve-se que a população desse estudo é pediátrica, com 137
participantes de 8 a 16 anos). No mesmo estudo, a **sensibilidade** mostrou-se em geral
maior nas posições próximas ao centro de massa, ao passo que a **especificidade** foi
consideravelmente melhor no punho — resultado coerente com o mecanismo descrito na seção
X.1, visto que a discriminação da vigília depende do registro de movimento durante o período
desperto. Por esse mecanismo, é razoável antecipar que a posição adotada neste trabalho
apresente especificidade **inferior** à de dispositivos de punho, e não superior — hipótese
que o trabalho declara explicitamente e que orienta a interpretação dos resultados obtidos.

Em contrapartida, há evidência de que a incorporação de informação sobre **mudanças de
postura**, combinada à aceleração corporal, melhora a detecção de épocas de sono e vigília
em relação ao uso isolado da aceleração de punho: em comparação direta contra
polissonografia, sensor único posicionado no tórax alcançou acurácia de 85,8% na
identificação de épocas de sono e vigília, contra 79,8% da actigrafia de punho (RAZJOUYAN et
al., 2017). Essa constatação fundamentou a inclusão de características derivadas de ângulo
de inclinação no conjunto de atributos utilizado.

**Lateralidade do sensor.** A base empregada na validação externa dispõe de registros
simultâneos dos dois punhos do mesmo participante, o que permitiu isolar o efeito do lado do
corpo sobre o desempenho. A comparação foi conduzida **intraparticipante**, nos 26
participantes com registro bilateral: cada participante é seu próprio controle, uma vez que
a noite, a rotulagem polissonográfica e o modelo são os mesmos, variando apenas o lado em
que o acelerômetro foi acoplado. Sob essa formulação, a diferença entre os punhos esquerdo e
direito **não se distinguiu de zero** em nenhuma das configurações avaliadas: para a
configuração de melhor desempenho, obteve-se diferença de coeficiente kappa de +0,009
(IC 95%: −0,014 a +0,031) e de especificidade de −0,009 (IC 95%: −0,038 a +0,017); nas vinte
e quatro comparações realizadas, a maior diferença absoluta observada foi de 0,027 em kappa,
e todos os intervalos de confiança contiveram o valor nulo.

Esse resultado é interpretado como evidência favorável às decisões de representação adotadas
na seção (REFERÊNCIA INTERNA — extração de características): o conjunto de atributos foi
deliberadamente construído com grandezas invariantes a rotação — inclinação relativa à
gravidade de referência da própria gravação e norma euclidiana da componente dinâmica, em
substituição a atributos dependentes de eixo —, e a insensibilidade ao lado do corpo é uma
consequência previsível dessa invariância. Registra-se, contudo, que a ausência de efeito
detectável não equivale à demonstração de ausência de efeito: com 26 participantes, efeitos
de magnitude inferior a aproximadamente 0,03 em kappa não seriam distinguíveis do ruído
amostral pelo delineamento empregado.

### X.4 Limitações da validação

**Ausência de padrão-ouro.** A polissonografia constitui o padrão-ouro para avaliação do
sono e encontra-se fora do alcance material deste trabalho. A validação empregou, portanto,
referências alternativas viáveis, conforme descrito na seção de metodologia, e os resultados
devem ser interpretados à luz dessa substituição.

**Transferência entre domínios.** Não existe, até o momento desta pesquisa, base de dados
pública que reúna acelerometria captada em travesseiro com rotulagem de sono validada por
polissonografia. Consequentemente, a validação apoiada em bases públicas atesta a
**abordagem** de detecção movimento/repouso, e não o desempenho do sensor **naquela
posição**. A distância entre os dois domínios — posição do sensor, acoplamento mecânico e
população — é declarada como limitação e foi objeto de quantificação específica, conforme
descrito na seção (REFERÊNCIA INTERNA — experimento de transferência entre posições).

**Degradação do desempenho entre coortes independentes.** A validação por
*leave-one-subject-out* controla o vazamento de informação entre participantes, mas não
controla nenhuma das demais fontes de homogeneidade de uma mesma coorte: aparelho, protocolo
de aquisição, critérios de pontuação polissonográfica, laboratório e perfil da população
permanecem constantes. Para quantificar essa limitação, conduziu-se validação externa em que
o modelo foi ajustado na totalidade dos 92 participantes da base de desenvolvimento e
aplicado, **sem qualquer reajuste**, a 27 participantes de coorte independente, adquirida com
acelerômetro de outro fabricante, em outro centro e com outra equipe de pontuação. Não houve
reestimação de parâmetros de normalização no domínio de teste, recalibração de limiar de
decisão ou qualquer acesso aos rótulos da coorte externa anterior à medição.

Na melhor configuração, o coeficiente kappa de Cohen decresceu de 0,414, obtido em validação
interna, para 0,334 (IC 95%: 0,254 a 0,416) na coorte externa, e a **especificidade decresceu
de 0,802 para 0,507** (IC 95%: 0,442 a 0,576). A perda concentra-se, portanto, exatamente na
métrica que a seção X.1 identifica como crítica neste domínio: aproximadamente trinta pontos
percentuais de especificidade não sobrevivem à troca de coorte. Considera-se, por
consequência, que **o desempenho externo, e não o interno, constitui a estimativa defensável
do comportamento esperado do método em população não observada**, e é nele que devem se
apoiar quaisquer afirmações de generalização.

Registra-se que os coeficientes kappa das duas condições **não são diretamente comparáveis
entre si**, uma vez que o kappa depende da prevalência da classe majoritária, que é de
0,699 na coorte externa e de 0,895 na base de desenvolvimento.
Por essa razão, a leitura adotada não é a comparação absoluta entre os dois valores, mas a
comparação de cada um contra o classificador trivial medido **na própria coorte** — referência
que, por construção, apresenta kappa nulo. Registra-se que a referência superior correspondente
— a concordância entre dois pontuadores humanos — foi medida na base de desenvolvimento, e não
na coorte externa, que não dispõe de segunda pontuação manual (ver a seção REFERÊNCIA INTERNA —
teto de concordância entre pontuadores). Em consequência, **não é possível decompor a degradação
relatada** entre perda de desempenho do método e diferença de concordância da rotulagem de
referência entre as duas coortes. Sob esse critério, todas as configurações
avaliadas permaneceram com o intervalo de confiança de 95% integralmente acima de zero na
coorte externa, o que sustenta a afirmação de que o método generaliza, ainda que com
desempenho reduzido.

**Ganhos metodológicos que atravessam coortes e ganhos que não atravessam.** A validação
externa produziu um resultado de natureza metodológica que se julga relevante registrar,
por condicionar a interpretação de todo procedimento de seleção de modelo adotado neste
trabalho. Duas modificações foram avaliadas sobre a mesma configuração de referência: a
imposição de estrutura temporal às predições por meio de um modelo oculto de Markov de dois
estados, e a ampliação da janela de contexto de cada época de ±2 para ±11 épocas,
aproximando-se da escala temporal empregada por algoritmos clássicos de actigrafia.

Em validação interna, a primeira modificação apresentou-se nitidamente superior, com ganho de
kappa de +0,123 (IC 95%: +0,105 a +0,142), aproximadamente o dobro do ganho obtido pela
segunda. Em validação externa, contudo, essa vantagem praticamente desapareceu — o ganho
remanescente foi de +0,036 (IC 95%: +0,008 a +0,067) — e veio acompanhada de **perda
estatisticamente distinguível de especificidade** (−0,037; IC 95%: −0,058 a −0,014). A
ampliação da janela de contexto, ao contrário, preservou magnitude e direção do efeito na
coorte externa, com ganho de kappa de +0,069 (IC 95%: +0,039 a +0,102) e de especificidade de
+0,095 (IC 95%: +0,065 a +0,130).

A explicação para a assimetria é atribuível ao objeto que cada modificação aprende. A matriz
de transição do modelo de Markov é estimada sobre a estrutura temporal de sono e vigília da
coorte de desenvolvimento e, por isso, incorpora a prevalência dessa coorte; transposta para
população com prevalência substancialmente distinta, a mesma matriz passa a penalizar
indevidamente as transições para vigília. A janela de contexto ampliada, por sua vez, não
codifica prevalência alguma: apenas altera a escala temporal sobre a qual as características
são computadas, e essa escala é propriedade do fenômeno fisiológico, não da coorte.

Deriva-se daí a limitação metodológica que se declara: **procedimentos de seleção de modelo
apoiados exclusivamente em validação cruzada interna são insuficientes neste domínio**. Neste
trabalho, especificamente, a validação interna teria selecionado a modificação cujo ganho não
se reproduz fora da coorte de origem, e apenas a validação externa permitiu distinguir o
ganho atribuível ao método do ganho atribuível à coorte. Essa distinção é registrada como
recomendação para trabalhos futuros na área, e não apenas como característica deste estudo.

**Número de coortes independentes.** A validação externa apoiou-se em **uma única** coorte
independente. Estava prevista a utilização de uma segunda base, com acelerometria de punho
obtida por dispositivo de consumo e rotulagem polissonográfica, o que permitiria distinguir o
que, na degradação observada, é atribuível à troca de coorte em geral e o que é atribuível às
particularidades daquela coorte específica. Essa segunda validação **não foi realizada**, por
indisponibilidade de acesso ao repositório que hospeda a base no ambiente de execução
empregado. Registra-se explicitamente que se trata de procedimento não executado, e não de
procedimento executado com resultado desfavorável. Com uma única coorte externa, a magnitude
da degradação relatada deve ser lida como estimativa pontual, não como medida da variabilidade
esperada entre coortes.

**Amostra própria.** As captações realizadas com o protótipo constituem amostra reduzida,
insuficiente para inferência estatística sobre população. Prestam-se à demonstração de
viabilidade técnica e à calibração de parâmetros, não à validação do método.

**Limite de detecção da verificação por paridade entre implementações.** O cálculo das
características é realizado em duas implementações independentes — a de referência, em
linguagem interpretada, empregada na análise, e a embarcada, em linguagem compilada, executada
no dispositivo — e a equivalência entre ambas é verificada por confronto contra um conjunto de
casos de referência com tolerâncias declaradas. Registra-se que esse procedimento possui
**limite de detecção inerente**, e que esse limite foi quantificado em vez de presumido.

A razão é estrutural. Entre duas implementações do mesmo cálculo não existe critério de
igualdade exata, apenas critério de tolerância, e a tolerância não pode ser estabelecida abaixo
do piso de divergência legítima entre elas — sob pena de reprovar implementação correta. Em
consequência, qualquer discrepância cuja magnitude seja inferior a esse piso é, por construção,
indetectável pelo procedimento.

Verificou-se experimentalmente, por injeção deliberada de defeito, um caso em que essa condição
se realiza: a substituição do estimador da direção da gravidade da época pela média das direções
instantâneas, em lugar da direção da média. Mediu-se, em função da amplitude do movimento, a
divergência produzida pelo defeito e o piso de divergência legítima, decorrente do tratamento de
borda do filtro de fase zero:

| Amplitude do movimento | Piso de divergência legítima | Divergência produzida pelo defeito |
|---:|---:|---:|
| 0,02 g | 0,0213° | 0,0004° |
| 0,20 g | 0,1857° | 0,0400° |
| 0,40 g | 0,3683° | 0,1406° |
| 0,60 g | 0,5507° | 0,2793° |
| 1,20 g | 1,0963° | 0,8184° |

Em toda a faixa avaliada o piso legítimo é de aproximadamente **o dobro** da divergência
produzida pelo defeito, e ambos crescem conjuntamente, por serem governados pela mesma grandeza
física — a variação do módulo do vetor gravidade filtrado ao longo da época. Registra-se, em
particular, que **a ampliação do conjunto de casos de referência não corrige a limitação**:
casos de movimento de maior amplitude elevariam o piso legítimo acima da tolerância, reprovando
implementação correta. Trata-se, portanto, de limitação do método de verificação, e não de
insuficiência do conjunto de casos empregado.

Declara-se, por conseguinte, que a equivalência entre as duas implementações está estabelecida
**acima do piso medido**, e não de forma absoluta, e que a mitigação adotada consiste na
inspeção do código e na manutenção do confronto por igualdade exata do lado da implementação de
referência, onde ele é possível. Registra-se igualmente que toda a verificação descrita foi
conduzida em ambiente de desenvolvimento, não no dispositivo físico, conforme a seção X.4,
parágrafo "Amostra própria".

**Sobre o instante de cada amostra no dispositivo.** ✏️ *(30/10, `FW-07`.)* Na arquitetura
adotada, o sensor armazena as leituras em memória interna sem marca de tempo, a uma taxa
governada por oscilador próprio cuja tolerância declarada é de −15 % a +10 % na faixa de
temperatura de operação. O dispositivo estima, por regressão linear entre o número acumulado de
amostras e o instante de cada leitura da memória, a taxa efetiva e o instante de cada amostra.
Em simulação com 50 sementes e quatro taxas entre 42,5 e 55 Hz, o erro dessa estimativa atingiu
cerca de 5 ms no centro da época; com o instante verdadeiro, a cadeia de reamostragem
embarcada reproduz a do pipeline de análise em 1,5 × 10⁻⁶ g. A divergência residual entre as
características calculadas no dispositivo e as do pipeline é, portanto, atribuível ao relógio, e
foi quantificada: até 2,2 × 10⁻³ g no máximo do ENMO, até 8 cruzamentos de 959 na taxa de
cruzamentos e até 1,1 % na magnitude dinâmica média. Registra-se, adicionalmente, que a
estimativa toma como exato o relógio do próprio microcontrolador, que durante o sono leve opera
a partir de oscilador interno de menor estabilidade; o erro desse relógio não foi medido e
depende do dispositivo físico.

**Sobre a guarda das épocas na ausência de conexão.** ✏️ *(31/10, `FW-08`.)* As épocas
calculadas no dispositivo são gravadas em memória flash não volátil antes do envio, e só são
liberadas após confirmação do servidor. Com a tabela de partições adotada, a capacidade
garantida é de 32 704 épocas de 30 s, o que corresponde a 272,5 h sem conexão; esgotada essa
capacidade, as épocas novas são recusadas e contabilizadas, e nenhuma época pendente é
sobrescrita. Duas perdas são declaradas. Primeiro, o instante de cada época é registrado com
resolução de um segundo. Segundo, quando o dispositivo é reiniciado antes de sincronizar o
relógio com a rede, as épocas gravadas naquela sessão conservam a medição, mas não o instante
absoluto, e passam a ser datadas pelo instante de recebimento. A integridade dos registros após
interrupção de energia foi verificada em simulação da memória, com interrupção em cada byte de
uma gravação, e não no dispositivo físico.

**Sobre a métrica de acurácia.** Registra-se, por rigor metodológico, que a acurácia global
não constitui métrica informativa neste domínio. Dado que a proporção de épocas de sono em
um registro noturno é elevada, um classificador trivial que atribuísse a totalidade das
épocas à classe "sono" alcançaria acurácia próxima àquela reportada por métodos
estabelecidos. Por essa razão, os resultados deste trabalho são apresentados acompanhados de
sensibilidade, especificidade, coeficiente kappa de Cohen e da comparação explícita com
classificadores de referência, conforme a seção de metodologia.

### X.5 Limitações de escopo deliberadas

As limitações a seguir decorrem de decisões de projeto, tomadas e registradas ao longo do
desenvolvimento.

**Não incorporação de fotopletismografia.** A medição de frequência cardíaca aumentaria
substancialmente a capacidade de discriminação do sistema, conforme a seção X.2. A
fotopletismografia, contudo, requer contato óptico com tecido perfundido, condição
incompatível com um dispositivo alojado no interior de um travesseiro. Avaliou-se
alternativa mecânica, pela captação de balistocardiografia; verificou-se, entretanto, que os
sinais de balistocardiografia e sismocardiografia possuem energia concentrada abaixo de
30 Hz e amplitude da ordem de 10 mg pico a pico, e que acelerômetros
microeletromecânicos comerciais, com densidade de ruído acima de 98 µg/√Hz, resultam em
resolução de aquisição de aproximadamente 0,54 mg — cerca de cinco bits — o que, conforme os
autores, compromete fortemente a análise do sinal; o sistema de alta resolução desenvolvido
naquele trabalho emprega acelerômetro com densidade de ruído inferior a 6,5 µg/√Hz (LEITÃO
et al., 2018). O componente adotado neste trabalho apresenta densidade de ruído de
400 µg/√Hz, medida a 10 Hz, em fundo de escala de ±2 g e taxa de amostragem de 1 kHz (TDK
INVENSENSE, 2013) — valor aproximadamente quatro vezes superior ao dos acelerômetros
comerciais mencionados e cerca de sessenta vezes superior ao do sensor dedicado. Registra-se
ainda que os trabalhos revisados que obtêm sinal cardiorrespiratório
em ambiente de cama empregam sensores piezoelétricos posicionados sob o colchão, e não
acelerômetros alojados no travesseiro. A incorporação dessa modalidade exigiria,
simultaneamente, substituição do transdutor, alteração da posição de instalação e
desenvolvimento de cadeia de processamento de sinal cardíaco, o que extrapola o escopo
delimitado.

**Não incorporação de captação de áudio.** A análise de sinal acústico permitiria abordar
fenômenos como ronco e padrão respiratório. Optou-se por não incorporá-la, por três razões:
alteraria o escopo declarado do trabalho, que se define como acelerométrico; elevaria
substancialmente a sensibilidade do dado tratado, com implicações relevantes sob a Lei Geral
de Proteção de Dados; e demandaria fundamentação adicional quanto à sua pertinência a um
trabalho fundamentado em actigrafia.

**Não medição de temperatura ambiente.** O sensor empregado disponibiliza leitura de
temperatura referente ao próprio circuito integrado, e não ao ambiente. Tal grandeza não é
apresentada ao usuário como temperatura ambiente, sendo esta uma distinção explicitamente
mantida na interface do sistema.

### X.6 Limitações de aplicação

O sistema **não constitui dispositivo médico** e não se destina a diagnóstico, triagem ou
acompanhamento clínico de distúrbios do sono. Não foi submetido a validação clínica, e as
informações que apresenta ao usuário limitam-se ao registro de movimento e a métricas dele
derivadas. O sistema não substitui polissonografia nem avaliação por profissional de saúde.

### X.7 Limitações de segurança da camada de autenticação

A autenticação do sistema é delegada a um serviço gerenciado de identidade (Supabase Auth),
decisão registrada no desenvolvimento e motivada por não reimplementar armazenamento de
credenciais, emissão de token e gestão de sessão em um trabalho cujo objeto é a medição do
repouso. Dessa delegação decorre a limitação descrita nesta seção, que se declara por ser
verificável por terceiros e por ter sido parcialmente medida durante o desenvolvimento.

**A limitação, enunciada.** Os fluxos de autenticação do sistema permitem a um visitante não
autenticado determinar se um endereço de correio eletrônico possui conta cadastrada. A falha é
conhecida na literatura de segurança de aplicações como *enumeração de usuários* (OWASP, 2025a)
e consiste na existência de um oráculo: um ponto de acesso que responde de forma distinguível
conforme a conta exista ou não. Seu impacto direto é a divulgação de informação, e não o acesso
indevido; sua relevância decorre do que ela viabiliza, a saber, a conversão de uma lista
arbitrária de endereços em uma lista de usuários efetivos do serviço, insumo de ataques de
reutilização de credenciais e de mensagens fraudulentas direcionadas.

**Os quatro canais identificados.** Foram levantados quatro pontos distinguíveis, classificados
abaixo quanto à natureza da evidência que os sustenta, por ser essa distinção condição para
avaliar a extensão da limitação.

1. **Cadastro de endereço já existente — verificado por execução.** Na configuração adotada, a
   tentativa de cadastro com endereço já registrado resulta em resposta de erro
   (`422 user_already_exists`), enquanto um endereço novo resulta em resposta de sucesso com
   sessão autenticada. A divergência é observável em cinco atributos simultâneos — código de
   estado, corpo da resposta, existência de sessão, navegação subsequente e estado da interface.
   Este canal foi **reproduzido no sistema em execução**, não inferido da leitura do código.
2. **Cadastro sob confirmação de endereço habilitada — não verificado neste trabalho.** O serviço
   oferece, como mecanismo declarado de mitigação, a habilitação da confirmação de endereço, sob
   a qual a tentativa de cadastro com endereço existente passa a retornar sucesso aparente. A
   documentação do serviço descreve esse comportamento de forma qualificada, afirmando que a
   resposta *"tenta ocultar"* a informação (SUPABASE, 2026a). Relatos técnicos reproduzíveis
   indicam que a ocultação é incompleta: o objeto de usuário retornado apresenta a coleção de
   identidades **vazia** quando o endereço já pertence a conta confirmada, e populada quando o
   endereço é novo, o que restabelece o oráculo no interior de uma resposta de sucesso. Este
   canal **não foi medido neste trabalho** e é declarado com base em documentação do fornecedor e
   em relato de terceiros.
3. **Alteração de endereço de correio eletrônico — verificado por leitura de código, com fonte
   externa.** A funcionalidade de correção de dados cadastrais, implementada em atendimento ao
   art. 18, III da Lei n.º 13.709/2018, solicita ao serviço de identidade a alteração do endereço
   de acesso. Quando o endereço solicitado pertence a outra conta, o serviço responde
   `422 email_exists`, comportamento registrado como pendência em aberto no repositório público
   do fornecedor (SUPABASE, 2026b). Em consequência, a interface do sistema apresenta desfechos
   distintos para endereço disponível e endereço já utilizado. Registra-se que este canal exige
   sessão autenticada, o que **não constitui controle efetivo**: uma única conta é suficiente para
   consultar um número arbitrário de endereços.
4. **Recuperação de senha — não verificado neste trabalho.** O fluxo de recuperação foi
   deliberadamente projetado para responder de modo idêntico na interface, independentemente da
   existência da conta, conforme recomendação específica para esse fluxo (OWASP, 2025b). Relato
   em aberto no repositório do fornecedor indica, contudo, que o serviço retorna erro de validação
   para endereços existentes e sucesso para endereços inexistentes em determinadas condições,
   porque a validação do domínio é executada após a consulta ao banco de dados (SUPABASE, 2026c).
   O relato foi reproduzido pelo autor daquele registro com domínio reservado para documentação,
   e **não se verificou se o comportamento se mantém para domínios de uso corrente**. Observa-se
   adicionalmente que a recomendação referida exige uniformidade também no **tempo de resposta**,
   requisito que não é atendido nem verificável no âmbito deste trabalho, por depender da
   implementação interna do serviço delegado.

**Enquadramento normativo da limitação.** A qualificação da severidade requer situar a exigência
violada no corpo normativo pertinente, e esse exercício produz três constatações.

Primeiro, a exigência de que usuários válidos não possam ser deduzidos a partir de mensagens de
erro, códigos de estado ou tempos de resposta, **com menção explícita aos fluxos de cadastro e de
recuperação de senha**, consta do Application Security Verification Standard em seu requisito
6.3.8, classificado como **Nível 3** (OWASP, 2025c). O Nível 3 é o mais alto da norma, destinado
a aplicações que demandem o maior rigor de verificação; nenhum requisito dos Níveis 1 e 2 exige
uniformidade de resposta entre os desfechos. A limitação aqui declarada configura, portanto,
não-atendimento de requisito de nível máximo, e não de requisito de linha de base.

Segundo, o NIST Special Publication 800-63B-4, referência normativa para autenticação e gestão
de ciclo de vida de autenticadores, **não estabelece requisito de não-enumeração**: a busca pelo
termo no capítulo que define as obrigações do verificador não retorna ocorrências, e os controles
que a publicação impõe para o mesmo espaço de ameaça são a limitação de taxa de tentativas e a
notificação do titular em eventos de conta (NIST, 2025). A ausência é informativa: ela indica que
a não-enumeração não integra o conjunto mínimo de obrigações de um verificador segundo aquela
norma, o que é coerente com o fato de o fornecedor do serviço delegado declarar a enumeração como
matéria fora do escopo de seu programa de divulgação de vulnerabilidades.

Terceiro, e com consequência para a classificação da limitação, **o acoplamento entre a proteção
contra enumeração e o fluxo de confirmação de endereço é escolha de implementação do serviço
adotado, e não necessidade técnica**. Serviço concorrente do mesmo segmento oferece a resposta
genérica no cadastro como opção de configuração independente, habilitada por padrão em instâncias
novas, sem vinculá-la a qualquer fluxo de confirmação (AUTH0, 2026); outro serviço oferece a
supressão apenas no fluxo de autenticação, mantendo-a ausente no cadastro (AMAZON, 2020).
Conclui-se que a limitação decorre da escolha do serviço de identidade — decisão de projeto
revisável — e não de uma impossibilidade do modelo de cadastro com endereço como identificador.

**Mitigação adotada e o que ela não alcança.** Adotou-se proteção contra automação (*captcha*) nos
pontos de acesso de cadastro, autenticação e recuperação. Essa medida reduz a **taxa** de
exploração, tornando economicamente desinteressante a varredura em massa, e **não elimina o
oráculo**: a consulta sobre um endereço determinado permanece possível ao custo de um desafio, e
é precisamente essa consulta individual que sustenta os usos de maior gravidade da enumeração. A
própria referência adotada classifica o *captcha* como medida de defesa em profundidade, e não
como controle preventivo (OWASP, 2025a). Registra-se, pelo mesmo motivo, que as mensagens
apresentadas na interface foram redigidas de forma condicional, não nomeando a existência da
conta, o que fecha o canal diretamente visível ao usuário sem fechar os canais descritos nos itens
1 a 4, que residem nas respostas do serviço e não na interface.

**O que seria necessário para eliminar a limitação.** A correção, distinta das mitigações, exige
três propriedades simultâneas: resposta idêntica em conteúdo, código de estado e tempo nos dois
desfechos; cadastro que não autentique o usuário no mesmo ato, respondendo invariavelmente com o
envio de mensagem de ativação; e tratamento do caso de endereço já cadastrado **pelo canal de
correio eletrônico**, informando ao titular legítimo a tentativa e orientando-o à autenticação ou
à recuperação de senha. Essa é a conduta recomendada para o fluxo de criação de conta, que
classifica como incorretas tanto a mensagem que informa a existência da conta quanto a que
confirma o cadastro bem-sucedido, e como correta apenas a que informa o envio de mensagem de
ativação (OWASP, 2025a). Verificou-se que nenhuma configuração do serviço adotado implementa esse
conjunto, e que interpor um serviço próprio entre o cliente e o serviço de identidade não seria
suficiente, dado que o ponto de acesso original permanece publicamente alcançável com a chave
pública que, por projeto, acompanha a aplicação cliente. A eliminação da limitação demandaria
desabilitar o cadastro público no serviço de identidade e implementar a criação de contas em
camada própria — alteração de arquitetura que extrapola o escopo delimitado e que foi, por essa
razão, declarada e não executada.

**Limitação correlata, registrada por decorrência.** Avaliou-se a habilitação da confirmação de
endereço como possível mitigação e verificou-se que ela introduz exposição de natureza distinta e
mais grave que a enumeração. Sob confirmação habilitada, uma nova tentativa de cadastro em
endereço com registro pendente de confirmação não substitui a credencial originalmente
estabelecida; em consequência, quem registre endereço de terceiro e não o confirme pode conservar
a credencial de acesso à conta que o titular legítimo venha a confirmar e utilizar posteriormente.
Trata-se da classe de ataque denominada *pré-sequestro de conta*, cuja causa raiz é descrita como
a permissão de uso da conta antes da verificação de que o usuário controla o identificador
fornecido, documentada empiricamente em 56 ocorrências sobre 35 de 75 serviços examinados
(SUDHODANAN; PAVERD, 2022); a documentação do serviço adotado emprega o mesmo termo ao descrever
as proteções do fluxo de vinculação de identidades (SUPABASE, 2026d). Registra-se que **a
exposição não se verifica na configuração adotada**, na qual a conta é confirmada no ato do
cadastro e, portanto, não existe estado pendente a ser ocupado. Ela é declarada por constituir
condição a ser satisfeita previamente a qualquer adoção futura da confirmação de endereço, sob
pena de substituir uma divulgação de informação por uma via de acesso indevido.

**Síntese.** O sistema não atende ao requisito de não-dedutibilidade de usuários válidos.
O não-atendimento é de requisito de nível máximo de verificação, decorre da escolha do serviço de
identidade delegado e não do princípio de medição do trabalho, e permanece em quatro pontos
identificados, dos quais um foi reproduzido em execução, um por leitura de código com fonte
externa e dois declarados a partir de registros públicos do fornecedor não reproduzidos neste
trabalho. O impacto é de divulgação de informação, sobre base de usuários de dimensão
experimental, sem finalidade comercial. Não se afirma, em nenhuma hipótese, ausência de
enumeração.

── FIM DO TEXTO ─────────────────────────────────────────────────────────────

---

## Checklist antes de colar no documento

- [x] ~~Substituir os marcadores `(REFERÊNCIA — ...)` pelas citações~~ — **feito em
      2026-09-10.** O texto usa agora citações autor-data. Resta apenas conferir se esse é o
      padrão adotado no TCC (se for numérico, converter) e montar a lista de referências
      final a partir de `docs/ML-DATASETS-E-PLANO.md` → "Fontes", onde cada entrada já traz
      autores, ano, título, periódico, volume, páginas e DOI.
- [x] ~~Montar as referências a partir dos artigos~~ — **autoria, ano, veículo, volume,
      páginas e DOI de todas as referências deste texto foram conferidos na fonte** em
      2026-09-10 (PubMed / Europe PMC / texto completo). A ressalva anterior de que "o único
      com autoria verificada é WALCH et al. (2019)" **não vale mais**.
- [ ] Substituir os marcadores `(REFERÊNCIA INTERNA — ...)` pelos números de seção
      corretos do próprio TCC.
- [ ] Ajustar `X` para o número da seção.
- [ ] **Ler os artigos citados antes de citá-los.** Isto **continua obrigatório**: ter a
      referência conferida não é o mesmo que ter lido o trabalho. `METODOLOGIA.md` é
      explícito: *sugestão de busca ≠ citação*. Todos os DOIs estão no §0.
- [ ] 🔧 **Ler as três notas de alteração de conteúdo** na seção "O que mudou na verificação
      de 2026-09-10", logo abaixo. Duas frases que estavam neste texto foram **removidas por
      não terem sido localizadas nas fontes**.
- [ ] Conferir se nenhum outro trecho do TCC afirma mais do que a seção X.2 permite —
      especialmente resumo, introdução e considerações finais.
- [ ] Verificar a coerência com o `README.md` público e com a nota de escopo exibida
      permanentemente na interface (`WEB-03`).
- [ ] 🔧 **X.7 — ler as três ressalvas de citação** em "O que entrou em 2026-10-20". Em especial:
      **delimitar ou reconferir a citação do NIST, que é feita por ausência**, e **ler o artigo de
      Sudhodanan & Paverd antes de citá-lo** — é a única fonte acadêmica da seção.
- [ ] **X.7 — reconferir as duas *issues* em aberto (#35844 e #2702) na semana da entrega** e
      registrar a data de consulta. Se tiverem sido corrigidas, a seção passa a afirmar falha
      inexistente, que é o defeito do `DOC-11` ao contrário.
- [ ] **X.7 — conferir que nenhum outro trecho do TCC afirma segurança que esta seção nega.**
      Mesma varredura que o `DOC-11` fez por "ainda não existe": procurar afirmações de
      conformidade, de "dados protegidos" e de anti-enumeração no resumo, na introdução, no
      capítulo de desenvolvimento e na política de privacidade.

## O que entrou em 2026-10-20

Nota para você, não para o texto. **Uma seção nova inteira: X.7, "Limitações de segurança da
camada de autenticação."** É a primeira limitação deste arquivo que **não é sobre medição** — não
é sobre o modelo, nem sobre o dado, nem sobre o instrumento de verificação. É sobre o sistema
como software em uso, e entrou porque o `SEC-08` foi decidido como saída **(B′)**: declarar em vez
de fechar, por fechar não ser alcançável. Raciocínio completo no diário de **2026-10-20 (ii)**.

**⚠️ Leia isto antes de colar.** Três coisas desta seção precisam de atenção, e duas são
diferentes de tudo o mais no arquivo:

1. **Dois dos quatro canais NÃO foram medidos neste trabalho**, e o texto diz isso em cada um,
   com a palavra "não verificado" no próprio título do item. **Não apague essas marcas para
   enxugar o texto.** A diferença entre "medimos" e "consta de registro público do fornecedor" é
   a única coisa que separa esta seção de uma alegação; e o arquivo inteiro existe para não
   fazer alegação. Se a banca perguntar "vocês testaram?", a resposta está escrita: o canal 1
   sim, o 3 por leitura de código com fonte, o 2 e o 4 não.
2. **A seção declara uma falha de segurança do próprio sistema, em texto que vai ao documento
   final.** Isso é deliberado e é o ponto forte: a alternativa — ligar uma chave e afirmar que
   fechou — seria afirmação falsa, porque a chave não fecha (ver canal 2). Declarar
   não-atendimento de requisito **de Nível 3**, com o custo de fechá-lo precificado, é postura
   defensável; afirmar conformidade que não existe não é.
3. **Se o captcha (`SEC-11`) for ligado, NADA nesta seção muda** além de já estar escrito no
   parágrafo "Mitigação adotada". O texto afirma que a medida reduz taxa e não elimina o oráculo.
   Trocar "limitação declarada" por "mitigado" depois de ligar a chave seria o §1 das lições.

**Referências novas desta seção, a montar na lista final.** Nenhuma delas estava no arquivo antes,
e **nenhuma vem de `ML-DATASETS-E-PLANO.md` §0** — a procedência delas é esta lista, e não aquele
§0, porque não são fontes de actigrafia. Todas foram lidas na fonte em 20/10:

| Marcador no texto | Fonte | Natureza |
|---|---|---|
| (OWASP, 2025a) | *Authentication Cheat Sheet*, OWASP Cheat Sheet Series — §*Authentication and Error Messages*, com a subseção *Account creation* | normativo-orientativa; é a que lista *"Welcome! You have signed up successfully."* como resposta **incorreta** |
| (OWASP, 2025b) | *Forgot Password Cheat Sheet*, OWASP Cheat Sheet Series | idem; é a que exige uniformidade de **tempo** |
| (OWASP, 2025c) | *Application Security Verification Standard* 5.0, V6 *Authentication*, requisito **6.3.8 (Nível 3)** | **normativa** — é a exigência violada, e o nível é o argumento |
| (NIST, 2025) | *NIST SP 800-63B-4, Digital Identity Guidelines: Authentication and Lifecycle Management* | **normativa, citada por ausência** — ver a ressalva abaixo |
| (SUDHODANAN; PAVERD, 2022) | *Pre-hijacked accounts: An Empirical Study of Security Failures in User Account Creation on the Web*, arXiv:2205.10174 | **acadêmica, e a única desta seção que é** — 56 vulnerabilidades em 35 de 75 serviços |
| (SUPABASE, 2026a) | Documentação de referência de `auth.signUp` | documentação de fornecedor |
| (SUPABASE, 2026b) | `supabase/supabase`, *issue* #35844 — `email_exists` na troca de e-mail | registro público, **em aberto** |
| (SUPABASE, 2026c) | `supabase/auth`, *issue* #2702 — `/recover` distinguível | registro público, **em aberto**, com PR proposto |
| (SUPABASE, 2026d) | Guia *Identity Linking* — usa o termo *pre-account takeover* | documentação de fornecedor |
| (AUTH0, 2026) | Configuração de *tenant* para resposta genérica no cadastro público | documentação/comunidade de fornecedor concorrente |
| (AMAZON, 2020) | *Prevent user existence errors*, Amazon Cognito — e `UsernameExistsException` no `SignUp` | idem |

**🔧 Três ressalvas de citação, e as três são obrigatórias.**

- **(NIST, 2025) é citada por AUSÊNCIA, e citar ausência exige cuidado redobrado.** A afirmação do
  texto é que a busca pelo termo *enumeration* no **capítulo de autenticadores** — o que contém as
  obrigações `SHALL` do verificador — não retorna ocorrências. Isso foi conferido em 20/10 sobre
  aquele capítulo, **e não sobre as quatro partes da publicação inteira** (63, 63A, 63B, 63C).
  Antes de submeter: ou reconferir nas quatro partes, ou estreitar a frase do texto para dizer
  exatamente onde se procurou. **Afirmação de ausência mal delimitada é o pior tipo de citação**,
  porque não há como o leitor a verificar sem repetir a busca.
- **O artigo de SUDHODANAN & PAVERD foi citado pela referência conferida, NÃO por leitura
  integral.** Vale aqui o item do checklist que já está neste arquivo, e com mais força, porque é a
  única fonte acadêmica da seção: **ler antes de citar.** O texto atribui a eles a causa raiz e os
  números (56/35/75); confira as duas coisas no artigo. A **variante exata** de pré-sequestro
  aplicável ao caso foi deliberadamente **não nomeada** no texto — o artigo cataloga cinco, e
  atribuir a errada seria pior que descrever o mecanismo em prosa, que é o que o texto faz.
- **As fontes de fornecedor são registros em aberto e podem fechar.** Os canais 3 e 4 dependem de
  *issues* não resolvidas; se forem corrigidas antes da submissão, **a seção fica desatualizada
  afirmando falha que não existe mais** — o que é o espelho exato do defeito que o `DOC-11`
  descreve. Reconferir #35844 e #2702 na semana da entrega, e registrar a data da consulta no
  texto final, como se faz com fonte eletrônica.

**O que esta seção NÃO diz, de propósito:** não quantifica risco, não estima número de contas
expostas e não compara com outros sistemas. Base de dimensão experimental e sem valor comercial
está dito; qualquer número além disso seria inventado.

## O que entrou em 2026-10-17

Nota para você, não para o texto. **Um parágrafo novo em X.4: "Limite de detecção da
verificação por paridade entre implementações."**

É a primeira limitação deste arquivo que **não é sobre o modelo nem sobre o dado** — é sobre o
*instrumento de verificação*. Entrou porque é material de defesa de um tipo que a banca
pergunta: *"como vocês sabem que o firmware calcula a mesma coisa que a análise?"*. A resposta
honesta é "até um piso medido, e aqui está o piso".

- **Procedência:** `docs/DIARIO-DE-ENGENHARIA.md`, entrada de 2026-10-17 (`DATA-07b`), seção
  "Dois pontos cegos do lado C++"; `firmware/nucleo/testes/verificar_paridade_por_mutacao.sh`.
- **Reconferir:** `cd firmware/nucleo && make mutacao` (15 casos; 11 sabotadores detectados,
  3 pontos cegos declarados confirmados cegos).
- **A tabela de amplitudes é medição**, não estimativa, e os dois números de cada linha vêm da
  mesma execução.
- **Não é pendência** e não deve ser lida como tal — está marcada ⛔ em
  `docs/BACKLOG-COMPLETO.md` (`PARID-C2`), fora da contagem de itens abertos, justamente para
  não ser retomada como tarefa.
- ⚠️ **O parágrafo remete a X.4 "Amostra própria"** ao dizer que a verificação rodou em
  desenvolvimento e não no dispositivo. Se a numeração das seções mudar, conferir a remissão.

## O que entrou na medição de 2026-09-21

Notas para você, não para o texto. Todos os números abaixo saem dos JSONs versionados em
`ml/experimentos/saida/` e podem ser reconferidos sem rodar nada pesado:

```bash
cd ml
python -m experimentos.ml03b_otimizacoes --item resumo        # validação interna, N=92
python -m experimentos.ml04_validacao_externa --comparar      # validação externa, n=27
python -m experimentos.ml04_validacao_externa --lados         # efeito do lado, n=26
python -m experimentos.ml05_teto_interavaliador --resumo      # teto humano, n=96 e n=90
```

**1. O que é medido e o que é antecipado.** Até esta atualização, X.3 e X.4 diziam o que se
*esperava* que acontecesse. Agora há medição, e em dois pontos ela é mais dura que a
expectativa. Convém não amaciar na hora de colar: a queda de especificidade de 0,802 para
0,507 é o número honesto do trabalho, e declará-lo antes que a banca o extraia é a diferença
entre rigor e defesa.

**2. Procedência dos números de X.4.** Validação interna: *leave-one-subject-out* sobre 92
participantes da base de desenvolvimento. Validação externa: modelo ajustado nos 92 de uma
vez e aplicado a 27 participantes do Newcastle 2015, sem reajuste. Braço citado no texto:
treino com acelerometria de punho, teste no punho esquerdo. Os intervalos de confiança de
comparações entre configurações são de **bootstrap pareado da diferença** sobre os mesmos
participantes, e não da sobreposição de intervalos individuais — os dois critérios estão
implementados lado a lado, e o texto reporta o pareado.

**3. Procedência dos números de X.3 (lateralidade).** A diferença entre punhos é medida
**dentro de cada participante**, nos 26 com registro bilateral. Um participante (`ncl010`)
não possui registro do punho direito e, por isso, o pareamento fecha 26 e não 27. As 53
gravações **não** foram empilhadas como observações independentes: os dois punhos de um mesmo
participante são a mesma noite e a mesma pontuação, e empilhá-los estreitaria o intervalo de
confiança em cerca de 30% sem que nenhuma evidência nova tivesse entrado. O número incorreto
está calculado no JSON, sob a chave `d_INCORRETO_empilhado`, apenas para documentar o tamanho
do viés — **não use esse valor em tabela**.

**4. O achado metodológico é o parágrafo mais forte da seção.** A distinção entre ganho que
atravessa coorte e ganho que não atravessa não é uma limitação no sentido usual: é um
resultado. Se o texto do TCC tiver seção de contribuições, vale referenciá-lo de lá, porque
um trabalho de graduação que demonstra, com número, por que validação interna não basta está
fazendo afirmação metodológica defensável — e essa afirmação é independente do desempenho
absoluto do protótipo.

**5. O que continua pendente.** A segunda coorte externa (Walch et al., 2019 — acelerometria
de punho por dispositivo de consumo, PhysioNet) não foi baixada nem processada: o repositório
não é alcançável do ambiente de execução. Falta o dado **e** o carregador
(`ml/src/carregar/walch.py` não existe). O parágrafo "Número de coortes independentes" declara
isso como não executado, de propósito — se a situação mudar, é esse parágrafo que muda.

---

## O que mudou na verificação de 2026-09-10

Três alterações são **de conteúdo**, não de forma. Leia antes de colar.

> ⚠️ **Por que estas notas não reproduzem o texto removido.** Duas citações foram retiradas
> por não existirem nas fontes. Um aviso que repete a frase errada entre aspas **vira ele
> próprio a origem do erro** — basta alguém copiá-la do aviso. Por isso as notas abaixo
> descrevem *o que* estava errado e *onde*, sem reproduzir o texto. A versão anterior das
> frases está no histórico do git, se algum dia for preciso auditar.

🔧 **1. A citação da revisão sistemática de estadiamento foi substituída (seção X.1).** O
texto trazia uma frase **entre aspas**, atribuída à revisão sistemática sobre estadiamento
por actigrafia, afirmando em substância que o método confunde vigília quieta com sono e por
isso superestima o sono. **Essa frase não foi localizada no artigo publicado**
(YUAN et al., 2024, *Journal of Sleep Research* 33(4) e14143) — o documento anterior citava
o **preprint** de medRxiv, e a redação não corresponde à do texto revisado por pares. A
citação atual foi conferida palavra por palavra no texto completo da versão publicada.
**Use a que está lá; não reintroduza nenhuma outra formulação entre aspas sem abrir o
artigo.**

🔧 **2. Uma afirmação sobre a conclusão dos autores do estudo pediátrico foi removida
(seção X.3).** O texto atribuía aos autores, **entre aspas**, uma conclusão que **inverte a
métrica**: dava ao punho a vantagem pela métrica errada. **A afirmação não foi localizada no
artigo**, e o que ele de fato relata é o oposto naquele ponto — no estudo, é nas posições
próximas ao centro de massa que a **sensibilidade** é maior; a vantagem do punho está na
**especificidade**. A seção X.3 foi reescrita para dizer apenas o que está publicado, e o
argumento ficou **mais forte**, porque a especificidade é exatamente a métrica em jogo para
este trabalho.

🔧 **3. O número de ruído de 6,5 µg/√Hz foi reenquadrado.** O texto o apresentava como um
requisito de sistemas de balistocardiografia. **O artigo não enuncia esse requisito**: os
6,5 µg/√Hz são a especificação do acelerômetro que os próprios autores desenvolveram. A
seção X.5 foi reescrita com o que o artigo de fato sustenta — a comparação com os
acelerômetros comerciais de 98 µg/√Hz e a resolução de ~5 bits que eles produzem. O
argumento sobrevive intacto e agora é defensável linha a linha.

Além disso, a atribuição do estudo do MotionWatch8 a *"Rocha et al., 2025"*, feita por
inferência numa sessão anterior, **era falsa**. A autoria correta é LI; HALAKI; CHOW (2025).

## O que NÃO está neste texto, e por quê

- **A faixa de 14 a 60 min de superestimação em insônia** — ✅ **entrou.** Foi rastreada até
  PAQUET; KAWINSKA; CARRIER (2007), *Sleep* 30(10):1362–1369, onde aparece textualmente. É
  **síntese secundária** de seis estudos primários (listados no §0.3 do
  `ML-DATASETS-E-PLANO.md`), e está citada como tal — nenhum estudo primário isolado reporta
  a faixa. Se quiser um número único e primário, escolha um dos seis e cite o valor dele.
- **Números de dispositivos comerciais** (Fitbit, Jawbone). A faixa que circula em revisões
  não foi rastreada até o estudo original nesta pesquisa; citá-la seria atribuir número sem
  fonte.
- **Limitações de hardware ainda não medidas** — autonomia, aquecimento, estabilidade
  mecânica. Dependem da validação em protótipo físico e devem ser escritas depois, com os
  números reais em mãos.

## A leitura positiva, para as Considerações Finais

Uma seção de limitações honesta não enfraquece o trabalho — mas convém que o texto explicite
o enquadramento que a acompanha, preferencialmente nas Considerações Finais:

> O trabalho não se propõe a superar a actigrafia de punho em desempenho. Propõe-se a
> investigar **quanto se perde** ao substituir um sensor vestido por um sensor que o usuário
> não percebe. Trata-se de questão de engenharia específica, mensurável e ainda não
> respondida na literatura — não há base pública que reúna acelerometria em travesseiro com
> rotulagem validada —, e é precisamente a questão de pesquisa aqui formulada. O resultado é
> informativo em qualquer direção: perda pequena valida o conceito; perda expressiva
> quantifica um limite até então não quantificado e fundamenta as alternativas de
> arquitetura discutidas.

E há um segundo enquadramento, de natureza metodológica, que a validação externa tornou
disponível e que convém não deixar enterrado na seção de limitações:

> A avaliação conduzida em coorte independente permitiu separar, entre as melhorias
> investigadas, aquelas cujo ganho se reproduz fora da base de desenvolvimento daquelas cujo
> ganho não se reproduz. A modificação que apresentava o maior ganho sob validação cruzada
> interna mostrou-se, em coorte independente, praticamente sem efeito e acompanhada de perda
> de especificidade; a modificação de ganho interno mais modesto preservou magnitude e
> direção. Conclui-se que, neste domínio, a seleção de modelo apoiada exclusivamente em
> validação interna é insuficiente, e que a distinção entre ganho atribuível ao método e
> ganho atribuível à coorte requer avaliação externa explícita.

Essa é uma afirmação **independente do desempenho absoluto do protótipo**: vale mesmo que os
números do dispositivo sejam modestos, e é o tipo de contribuição que uma banca reconhece
como maturidade metodológica.
