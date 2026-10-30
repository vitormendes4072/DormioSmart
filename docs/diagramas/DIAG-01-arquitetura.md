# DIAG-01 — Arquitetura do sistema, ponta a ponta

> **Item do backlog:** `DIAG-01` (escopo ampliado — o backlog pedia "diagrama de blocos
> da arquitetura"; aqui ele cobre sensor → firmware → API → banco → painel).
> **Onde entra no TCC:** capítulo de Desenvolvimento, primeira figura — é o mapa que
> todas as seções seguintes referenciam.
> **Estado do código:** verificado em `2026-09-29`, na branch `chore/GIT-01-normalizar-fim-de-linha`.
> ✏️ **Reconferido em `2026-10-28`** (`DIAG-01`): as 55 afirmações de arquivo, rota, função,
> tabela com RLS, pino e constante batem com o código. Entraram o que surgiu depois de 29/09 —
> as features em C++ (`filtro.h`, `caracteristicas.h`, **não exercitadas**), a rota
> `/api/me/perfil` (`PERFIL-01`) e o `/health` — e o `ML-04` da seta futura virou `ML-09`.

## Convenções de leitura (valem para os quatro diagramas)

Nada aqui depende de cor. A informação é carregada por **forma**, **traço** e **texto**:

| Aparência | Significado |
|---|---|
| Caixa de traço **contínuo** | Existe no código de hoje e roda. |
| Caixa de traço **tracejado**, rótulo começando por `(FUTURO)` | Projetado, **não implementado**. O item do backlog está no rótulo. |
| Caixa de traço **contínuo** com rótulo `(NÃO EXERCITADO)` | O código existe, mas nunca rodou no cenário que o justifica. |
| Seta cheia `-->` | Chamada ou fluxo de dado que acontece hoje. |
| Seta tracejada `-.->` | Fluxo projetado, ou fluxo que só ocorre em caminho de exceção. |

---

## O diagrama

```mermaid
flowchart TB
    subgraph DISP["DISPOSITIVO — ESP32 DevKit V1"]
        direction TB
        MPU["MPU6050 / GY-521<br/>I2C 0x68 · SDA=21 · SCL=22<br/>+/-8 g · filtro 21 Hz"]
        NUC["firmware/nucleo/ (C++ puro)<br/>cadencia.h · epoca.h · buffer.h<br/>reconexao.h · payload.h · relogio.h<br/>341 verificacoes no host"]
        FEAT["(NAO EXERCITADO) filtro.h · caracteristicas.h<br/>6 features por epoca em C++<br/>paridade com o dourado: 157 verificacoes<br/>o envio-continuo.ino NAO as chama — ARQ-01"]
        ENV["firmware/envio-continuo/<br/>envio-continuo.ino<br/>INSTRUMENTO DE BANCADA<br/>buffer de 1024 epocas = 8,53 h"]
        SKT["(FUTURO) firmware/sketch.ino<br/>reescrita FW-07: Deep Sleep +<br/>buffer em RTC_DATA_ATTR (128 epocas)<br/>hoje: 1 amostra por boot"]
        MPU -->|"ax, ay, az, gx, gy, gz, temp"| NUC
        NUC --> ENV
        FEAT -.->|"(FUTURO) vetor f no payload — DATA-07b"| ENV
        NUC -.-> SKT
    end

    subgraph CEL["SEGUNDA FONTE — navegador"]
        direction TB
        DM["DeviceMotion do navegador"]
        ACEL["frontend/src/lib/acelerometro.ts<br/>epoca de 30 s · pico-da-magnitude"]
        COL["frontend/src/pages/Coletar.tsx<br/>lib/coleta.ts"]
        DM --> ACEL --> COL
    end

    subgraph API["BACKEND — Flask em Vercel (dormio-smart.vercel.app)"]
        direction TB
        RT["web-app/routes.py<br/>POST /api/data · POST /api/data/lote · GET /api/sleep-history<br/>/api/devices · /api/me/perfil · DELETE /api/me<br/>GET /health"]
        ING["ingestao.py — qual caminho de credencial<br/>device_auth.py — hash SHA-256 do token<br/>auth.py — Bearer JWT"]
        VAL["validacao.py — SEC-03<br/>faixa fisica, coerencia ax/ay/az x total,<br/>epoca_s <= 3600 exige metodo"]
        DB["database.py<br/>cliente_de_ingestao() / cliente_do_usuario()"]
        RT --> ING --> VAL --> DB
    end

    subgraph SUP["BANCO — Supabase / PostgreSQL"]
        direction TB
        FN["Funcoes security definer<br/>registrar_leitura(token_hash, jsonb)<br/>registrar_leitura_da_sessao(uuid, jsonb)<br/>resolver_dispositivo · parear_dispositivo<br/>apagar_minha_conta · sanidade"]
        TB["Tabelas com RLS<br/>auth.users · profiles · devices<br/>device_tokens · sleep_data"]
        FN --> TB
    end

    subgraph WEB["PAINEL — React + Vite (PWA)"]
        direction TB
        HIST["hooks/useHistorico.ts<br/>lib/api.ts -> GET /api/sleep-history"]
        MET["lib/metricas.ts · lib/cobertura.ts<br/>sessoes, lacunas, fracao em movimento"]
        DASH["pages/Dashboard.tsx<br/>components/TracadoDeMovimento.tsx<br/>lib/exportar.ts (CSV)"]
        HIST --> MET --> DASH
    end

    ENV -->|"POST /api/data<br/>X-Device-Token"| RT
    SKT -.->|"POST /api/data/lote — rota pronta (API-03, 30/10); o firmware passa a usá-la no FW-07"| RT
    COL -->|"POST /api/data<br/>Authorization: Bearer"| RT
    DB -->|"papel dormio_ingestao (token)<br/>ou JWT do usuario (sessao)"| FN
    DB -->|"GET: JWT do usuario, filtro pelo RLS"| TB
    TB --> HIST

    subgraph OFF["PESQUISA — fora do produto, offline (ml/)"]
        direction TB
        DS["Wearanize+ OA (100 suj.)<br/>Newcastle 2015 (55 reg.)"]
        PIPE["ml/src/ — carregar, sinal, epocas,<br/>features (8), modelos, avaliar"]
        RES["ml/experimentos/saida/*.json"]
        DS --> PIPE --> RES
    end

    RES -.->|"(FUTURO) modelo embarcado ou servido — ML-INF"| RT
    TB -.->|"(FUTURO) noite propria como coorte — VAL-02 / ML-09"| PIPE

    classDef futuro stroke-dasharray: 6 4;
    class SKT futuro;
```

## Notas que o diagrama sustenta, e que precisam ser ditas no texto

1. **O classificador de ML não está no produto.** O bloco `ml/` é pesquisa offline. O
   rótulo `status` que chega ao banco é produzido por limiar no firmware
   (`firmware/nucleo/payload.h`: `|total − 9,81| > 1,2 m/s²` → `movimento`), não por
   modelo. As duas setas tracejadas entre `ml/` e o produto são projeto (`ML-INF`,
   `VAL-02`), não realidade.
2. **Há dois sketches, e o de produto não é o que roda.** `envio-continuo.ino` está
   declarado no próprio cabeçalho como *instrumento de bancada*; `sketch.ino` tira uma
   amostra por boot e não registraria uma noite. A reescrita é o `FW-07`.
3. **O backend não escolhe o dono da linha.** `routes.py` monta o payload sem `user_id`
   e sem `device_id`; quem carimba é a função no banco, a partir do hash do token ou de
   `auth.uid()`. Ver `DIAG-04`.
4. **O ESP32 e o navegador são duas fontes com credenciais deliberadamente diferentes** —
   `X-Device-Token` para quem não tem sessão, `Authorization: Bearer` para quem tem.
   Ver `web-app/ingestao.py`.
5. **Nenhuma noite real foi captada ainda.** Os 8 pinos do MPU6050 não estão soldados
   (Etapa 0 do backlog). O caminho `MPU6050 → painel` está fechado e testado em bancada,
   não validado em uso noturno.
