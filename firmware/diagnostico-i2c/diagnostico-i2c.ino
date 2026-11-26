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
 *   2. WHO_AM_I mil vezes: o MPU6050 original devolve 0x68 SEMPRE (com AD0
 *      alto ou baixo). Tres casos (HW-12, 26/11/2026):
 *        - 0x68 em todas, sem falha       -> MPU6050 original;
 *        - o MESMO valor diferente de 0x68 em todas, sem falha de barramento
 *                                         -> CHIP NAO ORIGINAL, barramento ok;
 *        - falhas, ou valores que variam  -> barramento nao confiavel.
 *      Ate 26/11 o segundo caso caia no terceiro: um clone com 0x70 constante
 *      e zero falhas era anunciado como "barramento nao confiavel".
 *   3. Bloco de 14 bytes (acelerometro + temperatura + giroscopio) mil vezes,
 *      com verificacao de plausibilidade: parado, |a| tem que ficar perto de
 *      9,81. Conta quantas leituras saem da faixa.
 *   4. Capacidade da FIFO (HW-12): enche a FIFO so com o acelerometro e mede
 *      a contagem em que ela transborda. O MPU6050 tem 1024 B; os clones com
 *      WHO_AM_I 0x70 medidos em 26/11 transbordaram em 512 B. O firmware do
 *      Dormio esvazia a FIFO a cada ~1,7 s contando com 1024 B: com 512 B,
 *      toda drenagem e descartada por transbordo.
 *   5. Repete tudo em 100 kHz e em 400 kHz. Se so a velocidade baixa
 *      funciona, o problema e capacitancia/comprimento de fio.
 *
 * -- COMO LER O RESULTADO -----------------------------------------------
 *
 *   0 erros nas duas velocidades  -> barramento ok, o defeito e outro
 *   erros so em 400 kHz           -> fio comprido ou pull-up fraco
 *   erros nas duas               -> contato intermitente ou solda fria
 *   nada responde na varredura    -> alimentacao ou fio trocado
 *   WHO_AM_I constante != 0x68    -> chip nao original: a marcacao "MPU-6050"
 *                                    no chip nao prova nada (HW-12)
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
const uint8_t REG_FIFO_EN      = 0x23;
const uint8_t REG_INT_STATUS   = 0x3A;
const uint8_t REG_ACCEL_XOUT_H = 0x3B;
const uint8_t REG_USER_CTRL    = 0x6A;
const uint8_t REG_PWR_MGMT_1   = 0x6B;
const uint8_t REG_FIFO_COUNT_H = 0x72;
const uint8_t REG_WHO_AM_I     = 0x75;

const uint8_t WHO_AM_I_MPU6050  = 0x68;
const uint16_t FIFO_MPU6050_B   = 1024;   // o que o firmware do Dormio espera
// A contagem lida no instante do transbordo oscila alguns bytes (510 ou 512 B
// no clone de 26/11; 1024 nao e multiplo de 6). O corte fica no meio do
// caminho entre 512 e 1024, e nao em 1024 exato.
const uint16_t FIFO_CORTE_B     = 768;

// ANTES de qualquer funcao: a IDE gera os prototipos de todas as funcoes
// logo antes da primeira delas, e eles ja usam o tipo. O `make sintaxe`
// compila com g++ puro e nao pega isso; so o arduino-cli pega.
enum Identidade { ID_ORIGINAL, ID_NAO_ORIGINAL, ID_BARRAMENTO_RUIM };

bool fifoComoMpu6050(uint16_t n) { return n >= FIFO_CORTE_B; }

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

// HW-12: o valor constante sem falha nenhuma e a identidade do chip, nao
// ruido. Barramento ruim muda o valor de uma leitura para outra (ou falha).
Identidade classificarIdentidade(int falhas, int lidos, int iguaisAoPrimeiro,
                                 uint8_t primeiro) {
  if (falhas > 0 || lidos == 0 || iguaisAoPrimeiro != lidos) return ID_BARRAMENTO_RUIM;
  return primeiro == WHO_AM_I_MPU6050 ? ID_ORIGINAL : ID_NAO_ORIGINAL;
}

const char *nomeDaIdentidade(uint8_t v) {
  switch (v) {
    case 0x68: return "MPU6050";
    case 0x70: return "MPU6500 (ou clone com a identidade dele)";
    case 0x71: return "MPU9250";
    case 0x73: return "MPU9255";
    default:   return "desconhecida (clone)";
  }
}

Identidade testarIdentidade() {
  Serial.printf("[2] WHO_AM_I x%d (o MPU6050 original devolve 0x68 sempre)\n",
                REPETICOES);
  int falhasDeLeitura = 0, divergentes = 0, lidos = 0, iguaisAoPrimeiro = 0;
  uint8_t primeiro = 0, primeiroErrado = 0;

  for (int i = 0; i < REPETICOES; i++) {
    uint8_t v = 0;
    if (!ler(REG_WHO_AM_I, &v, 1)) {
      falhasDeLeitura++;
    } else {
      if (lidos == 0) primeiro = v;
      lidos++;
      if (v == primeiro) iguaisAoPrimeiro++;
      if (v != WHO_AM_I_MPU6050) {
        if (divergentes == 0) primeiroErrado = v;
        divergentes++;
      }
    }
    delayMicroseconds(500);
  }

  Serial.printf("    falhas de barramento : %d\n", falhasDeLeitura);
  Serial.printf("    valor divergente     : %d", divergentes);
  if (divergentes) Serial.printf("  (primeiro: 0x%02X)", primeiroErrado);
  Serial.println();
  Serial.printf("    iguais ao primeiro   : %d de %d lidos\n", iguaisAoPrimeiro, lidos);

  Identidade id = classificarIdentidade(falhasDeLeitura, lidos, iguaisAoPrimeiro, primeiro);
  if (id == ID_ORIGINAL) {
    Serial.println("    -> identidade estavel: MPU6050 original (0x68)");
  } else if (id == ID_NAO_ORIGINAL) {
    Serial.printf("    -> CHIP NAO E MPU6050 ORIGINAL: 0x%02X em todas as leituras,\n", primeiro);
    Serial.printf("       sem falha de barramento. Identidade: %s.\n", nomeDaIdentidade(primeiro));
    Serial.println("       O barramento esta ok; a marcacao \"MPU-6050\" no chip nao");
    Serial.println("       prova nada. Ver a capacidade da FIFO no passo [4].");
  } else {
    Serial.println("    -> BARRAMENTO NAO CONFIAVEL: falhas de leitura ou valores que");
    Serial.println("       variam. O registrador e constante de fabrica.");
  }
  Serial.println();
  return id;
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

// --- 4. Capacidade da FIFO (HW-12) ---------------------------------------

/** Enche a FIFO so com o acelerometro (6 B por amostra, 1 kHz) e devolve a
 *  contagem no transbordo; 0 se nao conseguiu medir. */
uint16_t medirFifo() {
  Serial.println("[4] Capacidade da FIFO (so acelerometro, 1 kHz)");
  bool ok = escrever(REG_FIFO_EN, 0x00);
  ok &= escrever(REG_USER_CTRL, 0x04);           // FIFO_RESET
  delay(5);
  uint8_t st;
  ok &= ler(REG_INT_STATUS, &st, 1);             // ler limpa o bit de transbordo
  ok &= escrever(REG_USER_CTRL, 0x40);           // FIFO_EN
  ok &= escrever(REG_FIFO_EN, 0x08);             // ACCEL_FIFO_EN
  uint16_t maior = 0, noTransbordo = 0;
  // 1 kHz x 6 B: 1024 B enchem em ~0,17 s. 500 consultas de 1 ms sobram.
  for (int i = 0; ok && i < 500; i++) {
    uint8_t c[2];
    if (!ler(REG_FIFO_COUNT_H, c, 2) || !ler(REG_INT_STATUS, &st, 1)) { ok = false; break; }
    uint16_t n = (uint16_t)((c[0] << 8) | c[1]);
    if (n > maior) maior = n;
    if (st & 0x10) { noTransbordo = n; break; }
    delay(1);
  }
  escrever(REG_FIFO_EN, 0x00);
  escrever(REG_USER_CTRL, 0x04);

  if (!ok) {
    Serial.println("    falha de barramento durante a medida -> sem resultado");
  } else if (noTransbordo == 0) {
    Serial.printf("    nao transbordou em 0,5 s (maior contagem %u B) -> sem resultado\n", maior);
  } else {
    Serial.printf("    transbordou com %u B (maior contagem %u B)\n", noTransbordo, maior);
    if (fifoComoMpu6050(noTransbordo)) {
      Serial.println("    -> ~1024 B, como o MPU6050: serve ao firmware do Dormio");
    } else {
      Serial.printf("    -> MENOR QUE OS %u B DO MPU6050: o firmware do Dormio descarta\n", FIFO_MPU6050_B);
      Serial.println("       toda drenagem por transbordo com este sensor");
    }
  }
  Serial.println();
  return ok ? noTransbordo : 0;
}

// --- Bateria completa numa velocidade -----------------------------------

Identidade ultimaIdentidade = ID_BARRAMENTO_RUIM;
uint16_t ultimaFifo = 0;

void bateria(uint32_t hz) {
  Serial.println("=====================================================");
  // `%u`, nao `%lu`: no ESP32 uint32_t e `unsigned int`. Com `%lu` o printf
  // le 8 bytes de um argumento de 4 e imprime lixo. Achado pelo
  // `make sintaxe` em 16/10, na primeira vez que este sketch foi compilado.
  Serial.printf(" I2C a %u kHz\n", hz / 1000);
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

  ultimaIdentidade = testarIdentidade();
  testarDados();
  ultimaFifo = medirFifo();
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
      Serial.printf("Sensor encontrado em 0x%02X\n\n", endereco);
      break;
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
  Serial.println(" WHO_AM_I constante != 0x68   -> chip nao original, barramento ok");
  Serial.println();
  // HW-12: o veredito do chip, separado do veredito do barramento (o da
  // ultima velocidade medida, 400 kHz).
  Serial.println(" CHIP:");
  if (ultimaIdentidade == ID_ORIGINAL && fifoComoMpu6050(ultimaFifo)) {
    Serial.println("   MPU6050 original (0x68, FIFO de 1024 B)");
  } else if (ultimaIdentidade == ID_NAO_ORIGINAL ||
             (ultimaFifo > 0 && !fifoComoMpu6050(ultimaFifo))) {
    Serial.printf("   NAO E MPU6050 ORIGINAL (FIFO medida: %u B). O firmware do\n", ultimaFifo);
    Serial.println("   Dormio nao capta com ele. Trocar o sensor antes de soldar.");
  } else {
    Serial.println("   sem veredito: o barramento nao deixou medir");
  }
  Serial.println();
  Serial.println(" Copie tudo desde o inicio e mande para analise.");
}

void loop() {
  delay(1000);
}
