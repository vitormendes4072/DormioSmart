/*
 * secrets.example.h — modelo de credenciais do firmware (FW-05)
 *
 * COPIE este arquivo para `secrets.h` e preencha com os valores reais.
 *
 *   secrets.h          -> ignorado pelo git. NUNCA versionar.
 *   secrets.example.h  -> versionado, apenas com placeholders.
 *
 * O `sketch.ino` inclui `secrets.h`. Se o arquivo não existir, o build falha
 * de propósito: é melhor não compilar do que compilar com credencial escrita
 * no código, que é como segredo acaba no histórico do git.
 */
#ifndef SECRETS_H
#define SECRETS_H

// --- Wi-Fi ---
// Fase 1 (Wokwi): a rede do simulador é "Wokwi-GUEST", sem senha.
// Fase 2 (placa real): troque pela sua rede.
#define WIFI_SSID      "Wokwi-GUEST"
#define WIFI_PASSWORD  ""

// --- Token do dispositivo (SEC-02) ---
// Gerado ao parear o dispositivo na aplicação e exibido UMA ÚNICA VEZ.
// Sem ele, POST /api/data responde 401 e nada é gravado.
#define DEVICE_TOKEN   "cole-aqui-o-token-do-dispositivo"

#endif  // SECRETS_H
