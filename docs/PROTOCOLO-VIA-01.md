# Protocolo do VIA-01 — viabilidade de bancada do travesseiro

**Item:** `VIA-01`. **Escrito em:** 16/11/2026, antes da coleta. O critério de análise abaixo foi
fixado antes de existir qualquer dado, e não muda depois de ver o resultado.

**A pergunta.** Um MPU6050 dentro do travesseiro distingue três situações: a pessoa **parada**,
**mexendo a cabeça** e **virando o corpo**? A terceira é a dúvida real. O travesseiro acopla bem a
cabeça, mas pode não perceber o corpo rolando com a cabeça quase parada (`docs/HARDWARE.md`,
"Limitação antecipada"). Se não perceber, aciona-se a contingência de um segundo sensor sob o
colchão (`HW-07`).

**O que este teste é e não é.** É uma sonda de viabilidade, com uma pessoa e uma sessão (n = 1).
Mostra se o sinal existe; não valida o dispositivo, que é o `VAL-01` e o `VAL-02`.

---

## Antes de começar

1. **O travesseiro precisa estar recebendo leituras.** Em **Dispositivos**, o Smart Dormio não pode
   estar "Pausado". Se estiver, toque em **Retomar**; senão, tudo o que a placa mandar é descartado.
2. A placa no travesseiro, ligada, com o firmware de produto (`firmware/sketch.ino`) e Wi-Fi.
3. Espere a primeira época chegar. Ela aparece no painel ou no monitor serial como
   `[epoca N] ... com f`. Sem "com f", a época não tem features, e o teste não serve.
4. Um relógio à vista para anotar a **hora de início de cada bloco**, em horas, minutos e segundos.
   O relógio do celular serve.

## Os blocos (deitado, com a cabeça no travesseiro)

| Bloco | Duração | O que fazer |
|---|---|---|
| **A, parado** | 5 min | Não se mexer. |
| **B, cabeça** | 5 min | Virar a cabeça de um lado para o outro de vez em quando, sem mexer o corpo. |
| **C, corpo** | 5 min | Virar o corpo de lado e voltar de vez em quando, tentando manter a cabeça no lugar. |

**Recomendado:** repetir A, B e C mais uma vez, num total de 30 min. A repetição mostra se a
separação se repete, e dobra as épocas de cada bloco.

**Por que 5 min, e não os 2 min da linha original do backlog.** A placa entrega uma época a cada
30 s. Em 2 min seriam 4 épocas por bloco, e menos ainda depois de descartar as bordas. Com 5 min,
ficam 9.

## Depois do último bloco

1. Espere o último lote chegar ao servidor. ✏️ *16/11: a placa envia **a cada 10 minutos**, não logo depois de cada época. Com a placa no USB, o monitor serial mostra `[lote] HTTP 200` depois do último bloco; sem ele, espere 10 minutos depois do fim.*
2. No computador, com o site da produção aberto e logado, abra o console do navegador (F12, aba
   Console). Cole o trecho abaixo **trocando os horários** pelos que você anotou e tecle Enter.
3. O navegador baixa um arquivo `via01-AAAA-MM-DD.json`. Ele contém as épocas, as features e o
   rótulo do painel da janela do teste. **O token da sessão não vai no arquivo.**
4. Guarde o arquivo em `dados-locais/`, fora do repositório, e avise o Claude.

```js
// Horários de início de cada bloco, no fuso do seu computador, na ordem em que você fez.
// Com a repetição, são seis linhas: A, B, C, A, B, C.
const BLOCOS = [
  ["A", "22:00:00"],
  ["B", "22:05:00"],
  ["C", "22:10:00"],
];
const DURACAO_MIN = 5;

const hoje = new Date();
const quando = (hms) => { const [h, m, s] = hms.split(":").map(Number); const d = new Date(hoje); d.setHours(h, m, s || 0, 0); return d; };
const blocos = BLOCOS.map(([rotulo, hms]) => { const i = quando(hms); return { rotulo, inicio: i.toISOString(), fim: new Date(i.getTime() + DURACAO_MIN * 60000).toISOString() }; });
const desde = new Date(new Date(blocos[0].inicio).getTime() - 2 * 60000).toISOString();
const ate = new Date(new Date(blocos.at(-1).fim).getTime() + 5 * 60000).toISOString();

const k = Object.keys(localStorage).find(k => k.endsWith('-auth-token'));
const h = { Authorization: 'Bearer ' + JSON.parse(localStorage[k]).access_token };
const pegar = async (url) => { const r = await fetch(url, { headers: h }); return { status: r.status, corpo: await r.json().catch(() => null) }; };
const travesseiro = (await pegar('/api/devices')).corpo.find(d => d.tipo === 'travesseiro' && !d.revoked_at);
const q = new URLSearchParams({ device: travesseiro.id, desde, ate });
const features = await pegar('/api/features?' + q);
const historico = await pegar('/api/sleep-history?' + new URLSearchParams({ device: travesseiro.id, desde, ate, limite: 500 }));
const inferencia = await pegar('/api/inferencia?' + q);
console.log('features', features.status, (features.corpo?.epocas || []).length, 'épocas; histórico', historico.status, '; inferência', inferencia.status);

const arquivo = { protocolo: 'VIA-01', gerado_em: new Date().toISOString(), blocos, features: features.corpo, historico: historico.corpo, inferencia: inferencia.status === 200 ? inferencia.corpo : null };
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([JSON.stringify(arquivo, null, 1)], { type: 'application/json' }));
a.download = `via01-${hoje.toISOString().slice(0, 10)}.json`;
a.click();
```

A linha impressa no console deve dizer `features 200` e um número de épocas próximo de 2 por
minuto de teste. Com `features 200` e 0 épocas, a placa não enviou na janela: confira a pausa e o
Wi-Fi. `inferência 422` é normal em janelas curtas: o modelo pede um mínimo de épocas, e a
inferência é só informação extra.

---

## O critério (fixado em 16/11, antes dos dados)

O script `scripts/analisar_via01.py` faz a conta; o critério está escrito também no cabeçalho dele.

1. **Épocas de cada bloco:** as que estão a pelo menos 30 s de cada borda. As transições ficam de
   fora. Blocos com a mesma letra (a repetição) são somados.
2. **Para cada par** (A×B, A×C, B×C) e cada uma das 8 features, o **delta de Cliff**: a
   probabilidade de uma época de um bloco ter valor maior que uma do outro, menos o contrário. Vai
   de −1 a 1, e 0 é sobreposição total.
3. **Um par separa** se ao menos uma feature tiver |δ| ≥ 0,8, e se esse máximo passar num teste de
   permutação (2 000 embaralhamentos, semente fixa) com p < 0,05. A permutação existe porque
   escolher a melhor de 8 features infla o resultado.
4. **O veredito é o par A×C.** Se separa, o travesseiro percebe o corpo virando, e o projeto fica
   na v1. Se não separa, aciona-se o `HW-07`.
5. **Também se relata**, sem entrar no veredito: quantas leituras de cada bloco o painel rotulou
   "Movimento" (o rótulo usa a amostra de maior módulo da época, ver o `CALC-03`), e a saída do
   modelo, quando a janela basta.

**Conferência do critério com dados sintéticos** (`web-app/tests/test_analisar_via01.py`, no CI):
- blocos iguais em 30 sementes deram 3 pares "separados" em 90 (3,3 %), dentro dos 5 %;
- blocos diferentes separam;
- só a cabeça diferente aciona o `HW-07`;
- uma separação completa com 3 épocas por bloco não basta;
- uma diferença real, mas pequena, não basta;
- as épocas de borda não decidem nada.

## Rodar a análise

```bash
python scripts/analisar_via01.py dados-locais/via01-AAAA-MM-DD.json --json dados-locais/via01-resultado.json
```

O resultado vai para o diário. Os dados brutos ficam fora do repositório, que é público.

## Depois

As épocas do teste ficam na conta do autor e aparecem no painel como uma sessão curta. Se o autor
quiser apagá-las, a janela exata está no arquivo baixado (`blocos`), e o Claude escreve a consulta.
