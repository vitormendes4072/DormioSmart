# Contrato de dados — Dormio Smart

**Versão:** 1.0.0 · **Item:** DATA-01

Este documento é a fonte única de verdade sobre o dado que trafega entre
firmware, backend e banco. Firmware (`firmware/sketch.ino`), simulador
(`web-app/fake_sensor.py`) e backend (`web-app/routes.py`) devem sempre
declarar a mesma versão deste contrato. Divergência entre eles é bug.

---

## 1. Fluxo

```
ESP32 + MPU6050 ──POST /api/data──▶ Flask ──service_role──▶ Supabase (sleep_data)
                  X-Device-Token                                    │
                                                                    │ RLS
SPA (frontend) ──GET /api/sleep-history──▶ Flask ──JWT do usuário───┘
                  Authorization: Bearer
```

Dois caminhos, credenciais distintas e propositalmente diferentes:

- **Ingestão** não tem sessão de usuário, então o RLS não se aplica. O backend
  usa `service_role` e autentica o **dispositivo** por token.
- **Leitura** tem sessão. O backend repassa o JWT do usuário ao Supabase e quem
  filtra é o RLS, não código Python.

---

## 2. Payload de ingestão (device → backend)

`POST /api/data` · `Content-Type: application/json` · `X-Device-Token: <token>`

| Campo | Tipo | Unidade | Origem | Obrigatório |
|---|---|---|---|---|
| `ax` | float | m/s² | `a.acceleration.x` | sim |
| `ay` | float | m/s² | `a.acceleration.y` | sim |
| `az` | float | m/s² | `a.acceleration.z` | sim |
| `gx` | float | rad/s | `g.gyro.x` | sim |
| `gy` | float | rad/s | `g.gyro.y` | sim |
| `gz` | float | rad/s | `g.gyro.z` | sim |
| `t` | float | °C | `temp.temperature` | sim |
| `total` | float | m/s² | magnitude do vetor de aceleração | sim |
| `status` | string | — | rótulo do firmware | sim |

**Chaves curtas por decisão de projeto:** economizam bytes na transmissão do
ESP32. O backend traduz para os nomes de coluna (seção 4).

### 2.1 `total` — o que é e o que NÃO é

```
total = √(ax² + ay² + az²)
```

É a **magnitude bruta do vetor de aceleração, com a gravidade incluída**.
Em repouso vale ≈ 9,81 m/s² — **não vale zero**.

A *intensidade de movimento* exibida no dashboard é derivada disto, não
transmitida pelo device:

```
intensidade = |total − 9,81|
```

Em repouso ≈ 0; durante um evento, cresce. Essa derivação vive hoje em
`web-app/static/js/dashboard_logic.js` (`GRAVIDADE = 9.81`).

### 2.2 `status` — rótulo, não verdade científica

Valores atuais: `"Dormindo"` · `"Movimento Detectado!"`

O firmware classifica com um limiar fixo:

```cpp
status = (total > 11.0 || total < 8.0) ? "Movimento Detectado!" : "Dormindo";
```

> ⚠️ **Inconsistência conhecida (a resolver em DATA-02).** O limiar do firmware é
> **assimétrico** em relação à gravidade — a faixa 8,0–11,0 equivale a −1,81 /
> +1,19 m/s² em torno de 9,81 — enquanto o dashboard usa desvio absoluto
> **simétrico**. Firmware e visualização não usam o mesmo critério de "movimento".
>
> ⚠️ O rótulo `"Dormindo"` **excede o escopo do projeto**: o dispositivo não sabe
> se alguém dorme, apenas se houve movimento. O escopo declarado no `ROADMAP.md`
> não afirma estadiamento de sono. Renomear para `"Repouso"` / `"Movimento"`
> está previsto no DATA-02.

### 2.3 `t` — temperatura do chip, não do ambiente

O MPU6050 reporta a temperatura **do próprio circuito integrado**. Não é
temperatura ambiente, não é temperatura corporal e não deve ser apresentada
como qualquer uma das duas (ver Escopo no `ROADMAP.md`).

> ⚠️ **Inconsistência conhecida.** O `fake_sensor.py` documenta esse campo como
> "temperatura base do quarto (24 °C)", o que contradiz o contrato. Corrigir em
> DATA-02/SIM-02.

### 2.4 Timestamp

O device **não envia timestamp**. O ESP32 não tem RTC com bateria e perde a
hora a cada Deep Sleep; um relógio derivado do NTP a cada acordar gastaria
energia e falharia offline. O `created_at` é gerado pelo **banco** (`default now()`).

*Consequência assumida:* o timestamp é o do **recebimento**, não o da captação.
Com a rede saudável a diferença é de segundos. Quando o buffer local offline
existir (HW-05), o device precisará enviar um deslocamento relativo — isso
exigirá **versão 2.0.0** deste contrato.

---

## 3. Autenticação do dispositivo (SEC-02)

Header obrigatório: `X-Device-Token: <token opaco>`

- Gerado pela aplicação ao parear um dispositivo, exibido ao usuário **uma única vez**.
- O banco guarda apenas o **SHA-256** do token (`devices.token_hash`), nunca o valor.
- O backend resolve `token → device → user_id` e carimba a linha.
- Token revogado ou inexistente → `401`.

---

## 4. Mapeamento payload → coluna

| Payload | Coluna `sleep_data` | Tipo |
|---|---|---|
| `ax` | `accel_x` | double precision |
| `ay` | `accel_y` | double precision |
| `az` | `accel_z` | double precision |
| `gx` | `gyro_x` | double precision |
| `gy` | `gyro_y` | double precision |
| `gz` | `gyro_z` | double precision |
| `t` | `temp` | double precision |
| `total` | `movimento_total` | double precision |
| `status` | `status` | text |
| — | `created_at` | timestamptz (`now()`) |
| — | `user_id` | uuid (do token) |
| — | `device_id` | uuid (do token) |

---

## 5. Respostas de `POST /api/data`

| Código | Significado |
|---|---|
| `201` | Persistido e confirmado |
| `400` | Payload malformado — campo ausente, tipo errado ou fora de faixa (SEC-03) |
| `401` | `X-Device-Token` ausente, inválido ou revogado |
| `503` | Backend íntegro, mas o banco não persistiu |

`201` só é devolvido se a gravação foi **confirmada** — nunca otimista (FIX-02).

---

## 6. Leitura (backend → SPA)

`GET /api/sleep-history` · `Authorization: Bearer <JWT>`

Devolve um array (possivelmente vazio — nunca `500`, FIX-01) das leituras
**do usuário autenticado**, mais recentes primeiro:

```json
[{ "created_at": "2026-08-19T03:14:22.511Z",
   "movimento_total": 9.83, "temp": 31.2, "status": "Dormindo" }]
```

`401` sem JWT válido. O isolamento entre usuários é garantido pelo **RLS**, não
por filtro em código.

---

## 7. Versionamento

SemVer. **MAJOR** = quebra o firmware em campo (campo removido/renomeado,
unidade alterada, novo header obrigatório). **MINOR** = campo opcional novo.
**PATCH** = correção de redação.

| Versão | Data | Mudança |
|---|---|---|
| 1.0.0 | 2026-08-19 | Contrato inicial; formaliza payload existente, adiciona `X-Device-Token`, `user_id` e `device_id` (DATA-01/SEC-04) |
