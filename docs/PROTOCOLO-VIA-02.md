# Protocolo do VIA-02 — travesseiro e celular gravando a mesma noite

**Item:** `VIA-02`. **Escrito em:** 23/11/2026, antes da coleta. O critério de análise abaixo foi
fixado antes de existir qualquer dado, e não muda depois de ver o resultado.

**A pergunta.** Numa noite real, o travesseiro capta o movimento que o celular capta? Os dois
calculam as mesmas 8 features com o mesmo núcleo em C++, então a diferença entre eles é de
**onde** o sensor está e de **quanto** ele acopla ao corpo, não de conta. O teste também produz o
limiar de movimento do celular, que o `DATA-06` espera.

**O que este teste é e não é.** Compara dois sensores. Não diz se a pessoa estava dormindo: dois
sensores concordando não provam que estão certos (isso é o `VAL-02`). Uma pessoa, várias noites
(n = 1). Nenhuma mudança no app ou no firmware: os dois aparelhos já gravam para a mesma conta.

**As mesmas noites servem à etapa 3 do `CAL-03`** (seção no fim): se a autocalibração do
celular tirou o viés da orientação. Para isso, a tela do celular alterna entre as noites (passo 5
abaixo) e você anota uma linha do app; nenhuma noite a mais.

---

## Antes de cada noite

1. **Os dois aparelhos recebendo leituras.** Em **Dispositivos**, nem o travesseiro nem o celular
   podem estar "Pausado". Se estiverem, toque em **Retomar**; senão, o que mandarem é descartado.
2. **O travesseiro** ligado, com o firmware de produto (`firmware/sketch.ino`) e Wi-Fi.
3. **O celular** com o app Smart Dormio 1.1.2 ou mais novo, carregando a noite toda.
4. **A posição do celular é a mesma em todas as noites: sobre o colchão, perto do travesseiro**, e
   no app escolha **"Sobre o colchão"**. É o uso normal do app, e é ele que se quer comparar com o
   travesseiro. Trocar de posição entre noites mistura duas perguntas.
5. **A tela alterna de uma noite para a outra:** numa noite, deitado **com a tela para cima**; na
   seguinte, **com a tela para baixo**, e assim por diante. Continua "Sobre o colchão": muda só o
   lado, e isso não mexe no rótulo de movimento que o `VIA-02` compara (o viés da posição é de
   0,02 g, e o rótulo começa em 0,12 g). É o que o `CAL-03` precisa: a calibração só acerta o eixo
   da tela vendo os dois lados dele.
6. Anote a hora em que **iniciou a noite no app** e a hora em que **encerrou**, em data, horas e
   minutos.
7. **Logo depois de iniciar a noite**, abra **Detalhes técnicos** no cartão da noite e anote a
   linha **"Calibração do sensor"** (por exemplo "Calibrado: …", "Calibrando: 12 de 40 épocas
   paradas" ou "Calibração recusada: …"). Ela só aparece ali, e diz com que calibração a noite foi
   gravada.

## De manhã

1. No app, **Encerrar a noite** e esperar o envio terminar ("registros enviados"). Sem o envio, o
   servidor não tem a noite do celular.
2. Espere o último lote do travesseiro. A placa envia **a cada 10 minutos**: espere 10 minutos
   depois de levantar, ou o `[lote] HTTP 200` no monitor serial.
3. No computador, com o site da produção aberto e logado, abra o console do navegador (F12, aba
   Console). Cole o trecho abaixo **trocando o início e o fim** pelos que você anotou e tecle Enter.
4. O navegador baixa um arquivo `via02-AAAA-MM-DD.json`, com as épocas, as features, o rótulo do
   painel e, quando a janela basta, a saída do modelo dos dois aparelhos. **O token da sessão não
   vai no arquivo.**
5. Guarde o arquivo em `dados-locais/`, fora do repositório, e avise o Claude.

```js
// Início e fim da noite, no fuso do seu computador, como "AAAA-MM-DD HH:MM".
const INICIO = "2026-11-24 23:30";
const FIM = "2026-11-25 07:00";
const POSICAO_DO_CELULAR = "colchao";
// CAL-03: "cima" ou "baixo", e a linha "Calibração do sensor" anotada ao iniciar.
const ORIENTACAO_DO_CELULAR = "cima";
const LINHA_DE_CALIBRACAO = "";

const quando = (texto) => { const [d, hm] = texto.split(" "); const [a, me, di] = d.split("-").map(Number); const [h, mi] = hm.split(":").map(Number); return new Date(a, me - 1, di, h, mi, 0, 0); };
const desde = new Date(quando(INICIO).getTime() - 10 * 60000).toISOString();
const ate = new Date(quando(FIM).getTime() + 15 * 60000).toISOString();

const k = Object.keys(localStorage).find(k => k.endsWith('-auth-token'));
const h = { Authorization: 'Bearer ' + JSON.parse(localStorage[k]).access_token };
const pegar = async (url) => { const r = await fetch(url, { headers: h }); return { status: r.status, corpo: await r.json().catch(() => null) }; };
const aparelhos = (await pegar('/api/devices')).corpo.filter(d => !d.revoked_at);
const baixar = async (tipo) => {
  const d = aparelhos.find(x => x.tipo === tipo);
  if (!d) { console.log(tipo, 'não encontrado'); return null; }
  const q = new URLSearchParams({ device: d.id, desde, ate });
  const features = await pegar('/api/features?' + q);
  const historico = await pegar('/api/sleep-history?' + new URLSearchParams({ device: d.id, desde, ate, limite: 2000 }));
  const inferencia = await pegar('/api/inferencia?' + q);
  console.log(tipo, ': features', features.status, (features.corpo?.epocas || []).length, 'épocas; histórico', historico.status, (historico.corpo || []).length, '; inferência', inferencia.status);
  return { features: features.corpo, historico: historico.corpo, inferencia: inferencia.status === 200 ? inferencia.corpo : null };
};
const travesseiro = await baixar('travesseiro');
const celular = await baixar('celular');

const arquivo = { protocolo: 'VIA-02', gerado_em: new Date().toISOString(), janela: { inicio: quando(INICIO).toISOString(), fim: quando(FIM).toISOString() }, posicao_do_celular: POSICAO_DO_CELULAR, orientacao_do_celular: ORIENTACAO_DO_CELULAR, linha_de_calibracao: LINHA_DE_CALIBRACAO, travesseiro, celular };
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([JSON.stringify(arquivo, null, 1)], { type: 'application/json' }));
a.download = `via02-${INICIO.slice(0, 10)}.json`;
a.click();
```

O console imprime uma linha por aparelho. As duas devem dizer `features 200` e perto de 2 épocas
por minuto de noite (umas 900 numa noite de 7 h 30). Com 0 épocas num deles, ele não enviou na
janela: confira a pausa, o Wi-Fi e, no celular, se o envio terminou. O histórico não passa de
2 000 registros por pedido, o que cobre 16 h. `inferência 422` é normal em janela curta.

---

## O critério (fixado em 23/11, antes dos dados)

O script `scripts/analisar_via02.py` faz a conta; o critério está escrito também no cabeçalho dele.

1. **Pareamento.** O instante de cada época é o **fim** dela, e ela cobre os 30 s anteriores. Cada
   aparelho ancora a própria grade quando liga, então as grades ficam defasadas de 0 a 30 s. Cada
   época do travesseiro casa com a do celular que mais se sobrepõe a ela, com **ao menos 15 s** em
   comum; no empate exato, a do celular que termina depois. Época sem par fica de fora: trecho sem
   registro não é discordância.
2. **Atraso entre os relógios.** O celular é deslocado de −2 a +2 registros, e fica o deslocamento
   de maior correlação de Pearson da intensidade entre os pares. O escolhido é aplicado e relatado.
3. **Por noite:** dos registros com movimento no celular, quantos o travesseiro **também viu**, e o
   contrário; o κ de Cohen entre os rótulos; a correlação da intensidade (Pearson e Spearman); a
   fração com movimento em cada um; a cobertura de cada aparelho. Noite com **menos de 120 pares**
   (uma hora) não entra no veredito.
4. **O veredito**, sobre as noites que entram, **com ao menos 5 noites**: o travesseiro **capta** o
   que o celular capta se viu **ao menos 80%** dos registros com movimento no celular, e se o
   **limite inferior do intervalo de 95% passa de 70%**. O intervalo vem de um bootstrap por blocos
   de 20 pares seguidos (10 min), porque registros vizinhos não são independentes; 2 000
   reamostras, semente fixa.
5. **Também se relata**, sem entrar no veredito: o limiar do celular que faria a fração com
   movimento dele igualar a do travesseiro (o candidato para o `DATA-06`) e, quando veio, se o
   modelo chega à mesma classe nos dois.

**Por que a direção "o travesseiro viu do celular".** A dúvida é se o travesseiro perde o
movimento que o celular sobre o colchão vê. A direção contrária é relatada, e não decide: o
travesseiro ver mais que o celular não é defeito.

**Conferência do critério com dados sintéticos** (`web-app/tests/test_analisar_via02.py`, no CI):
- a mesma série nos dois, com as grades defasadas de 0, 5, 15 e 29 s, concorda inteira;
- séries independentes não concordam (|κ| < 0,15) e não "captam";
- um atraso de relógio de 1 e de 2 registros é medido e corrigido;
- um buraco no travesseiro ou no celular não vira discordância nem pareia com registro distante;
- perder 5% do movimento capta; perder 50% não;
- com pouco movimento, 80% vistos não bastam: o intervalo segura o veredito;
- menos de 5 noites não dão veredito, e uma noite curta fica de fora;
- o "viu" é medido na direção certa, e o limiar candidato iguala as frações.

Controle positivo: 8 regras sabotadas (sem corrigir o atraso, o empate do pareamento invertido, a
sobreposição mínima ignorada, o intervalo fora do veredito, sem o mínimo de noites, a noite curta
entrando, o "viu" invertido e o limiar errado), e cada uma derruba ao menos um teste.

## Rodar a análise

```bash
python scripts/analisar_via02.py dados-locais/via02-*.json --json dados-locais/via02-resultado.json
```

O resultado vai para o diário. Os dados brutos ficam fora do repositório, que é público.

## Depois

As noites ficam na conta do autor e aparecem no painel como duas sessões, uma por aparelho. Não há
nada a apagar: são noites reais.

---

## Junto: a etapa 3 do `CAL-03` (critério fixado em 23/11, antes dos dados)

**A pergunta.** Na noite de 10/11, sem calibração, o celular parado com a tela para baixo lia a
gravidade 2 % maior, e o piso da medida de movimento subia de menos de 1 mg para 23 mg sem
movimento nenhum. Desde a etapa 2, o app junta as épocas paradas entre noites e calibra cada
noite nova. Com noites reais, o piso passa a ser o mesmo nas duas posições?

**Os dados.** Os mesmos arquivos, só a parte do celular. É preciso a exportação do contrato
**2.12.0** ou mais novo, em que cada época traz a direção da gravidade, a norma, a marca de
calibração e a temperatura; o script recusa o arquivo de antes. As noites gravadas antes do
release continuam no banco e saem completas quando baixadas depois dele.

**O critério** (o script `scripts/analisar_cal03.py` faz a conta e o repete no cabeçalho):
1. **Época parada:** a magnitude dinâmica abaixo de 10 mg, a mesma régua com que o app escolhe os
   pontos de calibração.
2. **Orientação** pela gravidade: tela para cima ou para baixo com o eixo da tela a menos de 30°
   da vertical; em pé, de lado ou inclinado não entra.
3. **Por noite e por orientação**, com a época calibrada separada da que não é: o piso (a mediana
   da medida de movimento das épocas paradas), a mediana da norma e a da temperatura. Grupo com
   menos de 30 épocas paradas (15 min) não entra.
4. **O veredito, só com as épocas calibradas, com ao menos 2 noites em cada orientação:** a
   calibração **tirou o viés** se a diferença entre os pisos das duas orientações fica em **até
   3 mg** (eram 22,1 mg sem calibração e 7,9 mg com a calibração de mesa) e se a norma de cada
   orientação fica a **até 0,5 % de 1 g**. Com menos noites, "inconclusivo".
5. **Também se relata**, sem decidir: o mesmo para as épocas sem calibração (o controle: o viés
   tem de aparecer ali), a noite calibrada só em parte, a orientação declarada contra a medida e
   a linha anotada do app.

**O que esta etapa não decide.** Os limiares do app (os 10 mg de época parada e os 2 °C de faixa
de temperatura para estimar o termo de temperatura) seguem provisórios: a análise os descreve.
Validá-los pediria uma referência que não existe aqui. A temperatura aparece ao lado de cada
piso, porque também muda o erro do sensor.

**Conferência do critério com dados sintéticos** (`web-app/tests/test_analisar_cal03.py`, no CI),
com o erro do Moto E7 medido em 10/11: sem calibração, o controle acha o viés; calibrada nas duas
posições, tira; calibrada sem corrigir, com o viés invertido ou com a norma fora de 1 g, não tira;
época em movimento ou de lado não entra no piso; a calibrada não se mistura com a que não é; poucas
épocas ou uma noite por orientação dão "inconclusivo"; a exportação antiga é recusada. Controle
positivo: 10 regras do script sabotadas, e cada uma derruba ao menos um teste.

```bash
python scripts/analisar_cal03.py dados-locais/via02-*.json --json dados-locais/cal03-resultado.json
```
