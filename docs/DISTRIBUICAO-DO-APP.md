# Distribuir o app Android para testadores (`APP-12`)

> **Escrito em 10/11/2026.** O app é o do `APP-02`: registra a noite com a tela apagada e envia de
> manhã para a conta de quem o usa.
>
> ⚠️ **Antes de mandar o app a qualquer pessoa, falta uma decisão que não é técnica.** Dados de sono de
> outra pessoa, usados no TCC, são pesquisa com seres humanos. São necessárias três coisas: o aval do
> orientador sobre o comitê de ética (`LGPD-03`), a política de privacidade descrevendo o app nativo
> (achado AUD-04 da auditoria de 10/11) e o consentimento de cada testador. Este documento prepara o
> APK e o guia; **não autoriza o envio.**

## Parte 1 — para o autor: gerar a chave e o APK

### 1.1 A chave de assinatura (uma vez só)

O APK que vai para os testadores é assinado com uma chave **sua**, e não com a de depuração do
Android Studio. A chave fica **fora do repositório**, que é público. O `.gitignore` do Android
recusa `*.jks`, `*.keystore`, `*.p12` e `assinatura.properties` como segunda defesa.

1. Crie a pasta `.dormio` dentro da sua pasta de usuário. No Windows ela fica dentro de
   `C:\Users\<seu-usuario>`.
2. Num terminal, gere a chave dentro dela:

   ```bash
   keytool -genkeypair -v -keystore dormio-release.jks -alias dormio -keyalg RSA -keysize 4096 -validity 10000
   ```

   No **PowerShell**, com o caminho completo do Android Studio, o comando precisa do `&` na frente
   (sem ele, dá "Token '-genkeypair' inesperado"; medido em 11/11):

   ```powershell
   & "C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe" -genkeypair -v -keystore dormio-release.jks -alias dormio -keyalg RSA -keysize 4096 -validity 10000
   ```

   O `keytool` vem com o Android Studio, em `jbr/bin` dentro da pasta de instalação. Ele pede uma
   senha e alguns dados de identificação: nome e cidade bastam.
3. Na mesma pasta, crie o arquivo `assinatura.properties` com quatro linhas:

   ```properties
   arquivo=<caminho completo do dormio-release.jks, com barras normais />
   senha=<a senha do keystore>
   apelido=dormio
   senhaDaChave=<a senha da chave; a mesma, se você não escolheu outra>
   ```

4. **Guarde uma cópia da pasta `.dormio` fora do computador**, num pendrive ou num gerenciador de
   senhas. **Sem a chave não há como atualizar o app já instalado:** o testador teria de
   desinstalar e instalar de novo, e perderia as noites que ainda não enviou.

O `app/build.gradle` procura esse arquivo em `~/.dormio/assinatura.properties`, ou no caminho da
variável `DORMIO_ASSINATURA`. **Sem o arquivo, o APK de release sai sem assinatura e não instala.** Isso
é de propósito: nunca cai para a chave de depuração.

### 1.2 O APK

```bash
cd frontend
npm run build:app
cd android
./gradlew assembleRelease
```

O resultado é `frontend/android/app/build/outputs/apk/release/app-release.apk`. Os `.apk` são
ignorados pelo git.

**O que muda em relação ao de depuração:**
- o APK de release **não é depurável**;
- a depuração do WebView fica desligada (o padrão do Capacitor no release);
- o gatilho de teste (`--es roteiro`) não funciona, porque só vale com `BuildConfig.DEBUG`.

Medido em 10/11: o `aapt2 dump badging` mostra `application-debuggable` no de depuração e não no de
release, e o `apksigner verify` aceita o de release (esquema v2), assinado com uma chave descartável
de teste.

**Versão:** `versionName` 1.0.0 e `versionCode` 1, em `app/build.gradle`. A cada APK novo enviado,
aumente o `versionCode`: o Android recusa instalar por cima uma versão de número igual ou menor.

### 1.3 Como mandar

| Opção | Como | Prós | Contras |
|---|---|---|---|
| **Link do Google Drive** (para começar) | Suba o `app-release.apk` e mande o link | Grátis e imediato | O testador libera "instalar apps desconhecidos"; o Play Protect pode avisar; cada atualização é um APK novo, mandado de novo |
| **Google Play, teste interno** | Até 100 testadores por e-mail | Instala e atualiza pela Play Store, sem aviso | Conta de desenvolvedor (taxa única de US$ 25), revisão do Google, e o formulário de dados de saúde da Play |

## Parte 2 — para quem vai testar

> Este texto pode ser mandado como está, depois de o autor completar o item do termo.

### Antes de instalar

- **O que o app faz:** registra o movimento do celular durante a noite e envia para a sua conta. Não
  grava som, imagem nem localização.
- **Para que servem os dados:** *(a completar pelo autor: o uso no TCC e o termo de consentimento,
  conforme o orientador)*.
- **Celular:** Android 7 ou mais novo, com acelerômetro (praticamente todos têm). Testado até agora
  num Moto E7 (Android 10). Em outras marcas, o sistema pode encerrar o app de madrugada; o app
  registra quando isso acontece.

### Instalar

1. Abra o link do arquivo no celular e baixe o `app-release.apk`.
2. Ao abrir o arquivo, o Android pede para **permitir instalar apps desta fonte**. Permita, só para
   o app que abriu o arquivo (o Drive ou o navegador).
3. Se o **Play Protect** avisar que o app é desconhecido, toque em **Mais detalhes → Instalar mesmo
   assim**. O aviso aparece porque o app não está na Play Store.

### Criar a conta

1. Abra o **Dormio** e, na tela de entrada, toque em **Cadastre-se**.
2. Use um e-mail seu e uma senha que você **anote**. ⚠️ **Por enquanto, a recuperação de senha por
   e-mail não chega**; quem esquecer a senha perde o acesso à conta.
3. É preciso ter **18 anos ou mais**.

### Liberar a bateria (importante)

Sem isso, o Android pode parar o registro no meio da noite.

1. Na tela da noite, toque em **Permitir que o Dormio funcione com a economia de bateria** e
   confirme.
2. Em alguns celulares é preciso mais um passo:
   - **Xiaomi, Redmi e POCO:** Configurações → Apps → Dormio → Economia de bateria → **Sem
     restrições**. Ative também o **Início automático**.
   - **Samsung:** Configurações → Bateria → Limites de uso em segundo plano: tire o Dormio de **Apps
     em suspensão** e **Apps em suspensão profunda**.
   - **Motorola e Android puro:** o passo 1 basta.
3. Aceite a **notificação** quando o app pedir: ela fica fixa durante a noite e mostra que o registro
   está funcionando.

### Registrar uma noite

1. Antes de dormir, escolha **onde o celular vai ficar** (sobre o colchão é o mais simples) e toque
   em **Iniciar a noite**. Pode bloquear a tela.
2. **Deixe o celular com a tela para cima**, e de preferência num lugar onde ele não vire.
   **Não deixe carregando dentro da fronha**: esquenta.
3. Se acordar e pegar o celular, tudo bem: o app continua registrando.
4. De manhã, toque em **Encerrar** e preencha as **anotações**: a hora em que deitou, quando acha que
   pegou no sono, as vezes em que acordou e a hora em que levantou. Aproximado está bom.
5. **Deixe o app aberto até o envio terminar.** A tela mostra quantas épocas já foram.
6. **Não faça gravações de teste:** tudo o que o app grava vai para a sua conta como uma noite.

### Sair do teste

- **Apagar a conta:** Configurações → **Excluir minha conta**. Apaga as leituras, os dispositivos e o perfil.
- **Desinstalar:** como qualquer app. As noites que ainda não foram enviadas se perdem.
