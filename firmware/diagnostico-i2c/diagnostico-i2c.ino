/*
 * diagnostico-i2c.ino - o barramento esta confiavel? (CALC-02)
 *
 * INSTRUMENTO DE BANCADA. Nao usa a biblioteca da Adafruit de proposito: fala
 * direto com os registradores do MPU6050 pelo Wire. Se a biblioteca fosse a
 * suspeita, usa-la para investigar nao provaria nada.
 *
 * -- POR QUE ISTO EXISTE ------------------------------------------------
 *
 * Em 25/08/2026 a bancada apresentou DOIS defeitos diferentes seguidos:
 *
 *   1. todos os registradores zerados (temperatura em 36,53 C exatos, que e
 *      o que a formula raw/340+36,53 produz com raw = 0);
 *   2. depois, valores absurdos e INSTAVEIS - |a| = 56,5 m/s2 (5,75 g) com a
 *      placa parada, temperatura em -11,6 C, e ruido de 1,57 m/s2 contra os
 *      0,043 medidos quando o sensor estava saudavel.
 *
 * O segundo caso e o informativo. Erro de configuracao daria valor errado
 * porem ESTAVEL. Valor que pula 37x mais que o normal a cada leitura e
 * corrupcao de barramento: contato intermitente em algum dos quatro fios, ou
 * solda fria no header do modulo - defeito comum em placas baratas.
 *
 * Este sketch troca suposicao por numero.
 *
 * -- O QUE ELE MEDE -----------------------------------------------------
 *
 *   1. Varredura do barramento: quais enderecos respondem, e sempre os
 *      mesmos? Endereco que aparece e some ja e prova de contato ruim.
 *   2. WHO_AM_I mil vezes: deve devolver 0x68 SEMPRE. Uma unica divergencia
 *      condena o barramento.
 *   3. Bloco de 14 bytes (acelerometro + temperatura + giroscopio) mil vezes,
 *      com verificacao de plausibilidade: parado, |a| tem que ficar perto de
 *      9,81. Conta quantas leituras saem da faixa.
 *   4. Repete tudo em 100 kHz e em 400 kHz. Se so a velocidade baixa
 *      funciona, o problema e capacitancia/comprimento de fio.
 *
 * -- COMO LER O RESULTADO -----------------------------------------------
 *
 *   0 erros nas duas velocidades  -> barramento ok, o defeito e outro
 *   erros so em 400 kHz           -> fio comprido ou pull-up fraco
 *   erros nas duas               -> contato intermitente ou solda fria
 *   nada responde na varredura    -> alimentacao ou fio trocado
 *
 * DICA: rode e, enquanto ele mede, PRESSIONE cada fio e os pinos do header.
 * Se a contagem de erros mudar com a pressao, o defeito e mecanico.
 */

#include <Wire.h>
#include <math.h>
#include <string.h>

const uint8_t ENDERECO_A = 0x68;  // AD0 em nivel baixo (padrao)
const uint8_t ENDERECO_B = 0x69;  // AD0 em nivel alto

const uint8_t REG_SMPLRT_DIV   = 0x19;
const uint8_t REG_CONFIG       = 0x1A;
const uint8_t REG_GYRO_CONFIG  = 0x1B;
const uint8_t REG_ACCEL_CONFIG = 0x1C;
const uint8_t REG_ACCEL_XOUT_H = 0x3B;
const uint8_t REG_PWR_MGMT_1   = 0x6B;
const uint8_t REG_WHO_AM_I     = 0x75;

const float GRAVIDADE   = 9.80665;
const float ESCALA_8G   = 4096.0;   // LSB/g em +-8 g
const int   REPETICOES  = 1000;

// Parado, |a| fica perto de 9,81 em qualquer pose. Esta e a faixa que
// consideramos plausivel para uma placa em repouso sobre a mesa.
const float PLAUSIVEL_MIN = 7.0;
const float PLAUSIVEL_MAX = 13.0;

uint8_t endereco = ENDERECO_A;

// --- Acesso cru ao barramento -------------------------------------------

bool escrever(uint8_t reg, uint8_t valor) {
  Wire.beginTransmission(endereco);
  Wire.write(reg);
  Wire.write(valor);
  return Wire.endTransmission() == 0;
}

/** Le `n` bytes a partir de `reg`. Devolve false se o barramento reclamar. */
bool ler(uint8_t reg, uint8_t *destino, uint8_t n) {
  Wire.beginTransmission(endereco);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)endereco, (int)n) != n) return false;
  for (uint8_t i = 0; i < n; i++) destino[i] = Wire.read();
  return true;
}

int16_t junta(const uint8_t *b) { return (int16_t)((b[0] << 8) | b[1]); }

// --- 1. Varredura --------------------------------------------------------

void varrer() {
  Serial.println("[1] Varredura do barramento (3 passadas)");
  for (int passada = 1; passada <= 3; passada++) {
    Serial.printf("    passada %d:", passada);
    int achados = 0;
    for (uint8_t a = 1; a < 127; a++) {
      Wire.beginTransmission(a);
      if (Wire.endTransmission() == 0) {
        Serial.printf("  0x%02X", a);
        achados++;
      }
    }
    if (achados == 0) Serial.print("  NADA RESPONDEU");
    Serial.println();
  }
  Serial.println("    (o mesmo endereco tem que aparecer nas tres passadas)");
  Serial.println();
}

// --- 2. WHO_AM_I ---------------------------------------------------------

void testarIdentidade() {
  Serial.printf("[2] WHO_AM_I x%d (esperado 0x68 sempre)\n", REPETICOES);
  int falhasDeLeitura = 0, divergentes = 0;
  uint8_t primeiroErrado = 0;

  for (int i = 0; i < REPETICOES; i++) {
    uint8_t v = 0;
    if (!ler(REG_WHO_AM_I, &v, 1)) {
      falhasDeLeitura++;
    } else if (v != 0x68) {
      if (divergentes == 0) primeiroErrado = v;
      divergentes++;
    }
    delayMicroseconds(500);
  }

  Serial.printf("    falhas de barramento : %d\n", falhasDeLeitura);
  Serial.printf("    valor divergente     : %d", divergentes);
  if (divergentes) Serial.printf("  (primeiro: 0x%02X)", primeiroErrado);
  Serial.println();
  if (falhasDeLeitura == 0 && divergentes == 0) {
    Serial.println("    -> identidade estavel");
  } else {
    Serial.println("    -> BARRAMENTO NAO CONFIAVEL. Uma so divergencia ja condena:");
    Serial.println("       este registrador e constante de fabrica.");
  }
  Serial.println();
}

// --- 3. Bloco de dados ---------------------------------------------------

void testarDados() {
  Serial.printf("[3] Bloco de 14 bytes x%d, com verificacao de plausibilidade\n",
                REPETICOES);

  int falhasDeLeitura = 0, implausiveis = 0;
  float somaMag = 0, minMag = 1e9, maxMag = -1e9;
  uint8_t exemploRuim[14];
  bool guardouExemplo = false;
  int amostrasBoas = 0;

  for (int i = 0; i < REPETICOES; i++) {
    uint8_t b[14];
    if (!ler(REG_ACCEL_XOUT_H, b, 14)) {
      falhasDeLeitura++;
      continue;
    }
    float ax = junta(b + 0) / ESCALA_8G * GRAVIDADE;
    float ay = junta(b + 2) / ESCALA_8G * GRAVIDADE;
    float az = junta(b + 4) / ESCALA_8G * GRAVIDADE;
    float mag = sqrt(ax * ax + ay * ay + az * az);

    if (mag < PLAUSIVEL_MIN || mag > PLAUSIVEL_MAX) {
      implausiveis++;
      if (!guardouExemplo) {
        memcpy(exemploRuim, b, 14);
        guardouExemplo = true;
      }
    } else {
      amostrasBoas++;
      somaMag += mag;
      if (mag < minMag) minMag = mag;
      if (mag > maxMag) maxMag = mag;
    }
    delayMicroseconds(500);
  }

  Serial.printf("    falhas de barramento : %d\n", falhasDeLeitura);
  Serial.printf("    fora do plausivel    : %d de %d  (%.1f%%)\n",
                implausiveis, REPETICOES, 100.0 * implausiveis / REPETICOES);
  if (amostrasBoas > 0) {
    Serial.printf("    |a| nas boas         : media %.3f  faixa %.3f a %.3f\n",
                  somaMag / amostrasBoas, minMag, maxMag);
  } else {
    Serial.println("    |a| nas boas         : NENHUMA leitura plausivel");
  }
  if (guardouExemplo) {
    Serial.print("    exemplo de bloco ruim: ");
    for (int i = 0; i < 14; i++) Serial.printf("%02X ", exemploRuim[i]);
    Serial.println();
  }
  Serial.println();
}

// --- Bateria completa numa velocidade -----------------------------------

void bateria(uint32_t hz) {
  Serial.println("=====================================================");
  Serial.printf(" I2C a %lu kHz\n", hz / 1000);
  Serial.println("=====================================================");
  Wire.setClock(hz);
  delay(50);

  varrer();

  // Acorda o sensor e configura a faixa, cru. Se isto falhar, o resto nao
  // tem sentido.
  bool ok = escrever(REG_PWR_MGMT_1, 0x01);      // clock do giro X, sem sleep
  ok &= escrever(REG_SMPLRT_DIV, 0x00);
  ok &= escrever(REG_CONFIG, 0x04);              // DLPF ~21 Hz
  ok &= escrever(REG_GYRO_CONFIG, 0x08);         // +-500 deg/s
  ok &= escrever(REG_ACCEL_CONFIG, 0x10);        // +-8 g
  delay(100);
  Serial.printf("    configuracao escrita : %s\n\n", ok ? "ok" : "FALHOU");

  testarIdentidade();
  testarDados();
}

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  delay(500);

  Serial.println();
  Serial.println("#####################################################");
  Serial.println(" DIAGNOSTICO DE I2C - MPU6050");
  Serial.println(" Fala direto com os registradores, sem a biblioteca.");
  Serial.println("#####################################################");
  Serial.println();
  Serial.println(" DICA: enquanto ele mede, PRESSIONE cada fio e os pinos");
  Serial.println(" do header do modulo. Se a contagem de erros mudar com a");
  Serial.println(" pressao, o defeito e mecanico.");
  Serial.println();

  Wire.begin(21, 22);

  // Descobre em qual endereco o sensor esta antes de comecar.
  const uint8_t candidatos[2] = {ENDERECO_A, ENDERECO_B};
  for (int i = 0; i < 2; i++) {
    Wire.beginTransmission(candidatos[i]);
    if (Wire.endTransmission() == 0) {
      endereco = candidatos[i];
      Serial.printf("Sensor encontrado em 0x%02X

", endereco);
      break;
    }
  }
  }

  bateria(100000);
  bateria(400000);

  Serial.println("#####################################################");
  Serial.println(" COMO LER");
  Serial.println("#####################################################");
  Serial.println(" 0 erros nas duas velocidades -> barramento ok, defeito e outro");
  Serial.println(" erros so em 400 kHz          -> fio comprido ou pull-up fraco");
  Serial.println(" erros nas duas               -> contato intermitente / solda fria");
  Serial.println(" nada respondeu na varredura  -> alimentacao ou fio trocado");
  Serial.println();
  Serial.println(" Copie tudo desde o inicio e mande para analise.");
}

void loop() {
  delay(1000);
}
