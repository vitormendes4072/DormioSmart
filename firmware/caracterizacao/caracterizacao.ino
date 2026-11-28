/*
 * caracterizacao.ino - calibracao de 6 posicoes do MPU6050 ou do MPU6500
 * (CALC-02, CAL-01; FW-23)
 *
 * -- FW-23 (27/11): SEM A BIBLIOTECA DA ADAFRUIT ------------------------
 *
 * Ate 27/11 este sketch usava a Adafruit_MPU6050, cujo `begin()` recusa
 * qualquer chip cujo WHO_AM_I nao seja 0x68 (Adafruit_MPU6050.cpp, linha 94:
 * `if (chip_id.read() != MPU6050_DEVICE_ID)`). Os GY-521 vendidos hoje
 * chegam com um MPU6500 (0x70, FW-21), e com eles o sketch parava em
 * "MPU6050 nao encontrado". A biblioteca tambem grava o filtro so no CONFIG
 * (0x1A), que no MPU6500 nao filtra o acelerometro.
 *
 * Agora o sketch fala com o chip pelos registradores, como o sketch.ino de
 * producao: reconhece o chip pelo WHO_AM_I, acorda o sensor ANTES de gravar a
 * configuracao (no MPU6050 a primeira versao gravava com o chip dormindo, logo
 * apos o reset, e a conferencia acusou), grava o filtro de 21 Hz no 0x1A e,
 * no MPU6500, tambem no ACCEL_CONFIG 2 (0x1D), e converte a temperatura com a
 * formula de cada chip. A inicializacao e a conversao repetem as da
 * biblioteca (reset, SMPLRT_DIV 0, giroscopio em +-500 deg/s, PLL do eixo X;
 * m/s2 = bruto / 4096 * 9,80665), para que uma calibracao do MPU6050 feita
 * com a versao antiga continue comparavel.
 *
 * INSTRUMENTO DE BANCADA, NAO FIRMWARE DE PRODUTO.
 * Ele nao conecta Wi-Fi, nao envia nada e nao dorme.
 *
 * Vive em PASTA PROPRIA, e nao ao lado do sketch.ino, porque a IDE do Arduino
 * concatena todos os .ino de uma mesma pasta: dois setup() e dois loop() no
 * mesmo build nao compilam. A separacao tambem garante o que se quer aqui -
 * nao da para gravar isto no dispositivo por engano.
 *
 * -- POR QUE ISTO EXISTE -------------------------------------------------
 *
 * Uma medicao real de bancada (2026-08-24) mostrou o sensor parado marcando
 * |a| = 9,20 m/s2, e nao 9,81. Sao 0,61 m/s2 de erro com o aparelho IMOVEL.
 *
 * O criterio do projeto e |total - 9,81| > 1,2 (DATA-02). Com esse desvio, o
 * repouso ja nasce com intensidade 0,61 - metade do orcamento do limiar
 * gasta sem ninguem se mexer. Pior: sobra 1,81 de folga para cima e apenas
 * 0,59 para baixo. Uma assimetria de 3,1x, que e exatamente a classe de
 * defeito que o contrato v1.1.0 corrigiu no codigo. Agora ela vem do
 * hardware.
 *
 * Aquela medicao tinha UMA orientacao, e uma so nao distingue as duas causas
 * possiveis:
 *
 *   - ERRO DE ESCALA  -> as 6 magnitudes saem parecidas e baixas. Corrige-se
 *                        com um fator unico.
 *   - VIES POR EIXO   -> as 6 variam entre si. Cada eixo precisa do seu
 *                        proprio offset.
 *
 * Este sketch mede as seis e calcula as duas coisas.
 *
 * -- O METODO ------------------------------------------------------------
 *
 * Calibracao classica de 6 posicoes. Com o eixo i apontado para cima le-se
 * +g; apontado para baixo, -g. Dai:
 *
 *     vies_i   = (leitura_cima + leitura_baixo) / 2
 *     escala_i = (leitura_cima - leitura_baixo) / (2 * 9,81)
 *
 * O vies e o quanto o zero esta deslocado; a escala, o quanto o ganho difere
 * de 1. A correcao final e  a_corrigido = (a_lido - vies) / escala.
 *
 * -- POR QUE A LARGURA DE BANDA ESTA EM 21 Hz ----------------------------
 *
 * Ate o FW-06 o `sketch.ino` de producao NAO chamava setFilterBandwidth, e
 * rodava no padrao (260 Hz), que e barulhento. Medir aqui num filtro e usar
 * outro no produto invalidaria a transferencia do resultado - por isso os
 * dois sketches agora medem na mesma banda.
 *
 * 21 Hz e a escolha certa para os dois: movimento de corpo em cama e um
 * fenomeno lento, na casa de poucos Hz. Tudo acima disso e vibracao do
 * movel, passo no comodo e ruido do proprio MEMS - largura de banda maior so
 * deixa entrar o que nao interessa.
 *
 * -- COMO USAR -----------------------------------------------------------
 *
 * 1. Grave e abra o Monitor Serial em 115200, com "Nova linha" habilitado.
 * 2. Siga as seis poses. Apoie a placa numa superficie firme e SOLTE A MAO:
 *    dedo encostado transmite tremor e estraga a medida.
 * 3. Ao final, copie o bloco entre as linhas de ===== e mande para analise.
 *
 * A precisao do resultado depende de quao bem cada face fica na horizontal.
 * Uma caixinha ou um livro de capa dura ajuda mais do que a mao.
 */

#include <Wire.h>
#include <math.h>

// --- O chip, pelos registradores (FW-23) ----------------------------------

const uint8_t MPU_ENDERECO = 0x68;
const uint8_t REG_SMPLRT_DIV = 0x19;
const uint8_t REG_CONFIG = 0x1A;         // DLPF: no MPU6050, acelerometro e giro
const uint8_t REG_GYRO_CONFIG = 0x1B;
const uint8_t REG_ACCEL_CONFIG = 0x1C;
const uint8_t REG_ACCEL_CONFIG2 = 0x1D;  // so no MPU6500: o filtro do acelerometro
const uint8_t REG_ACCEL_XOUT_H = 0x3B;   // 0x3B-0x40 aceleracao, 0x41-0x42 temperatura
const uint8_t REG_SIGNAL_PATH_RESET = 0x68;
const uint8_t REG_PWR_MGMT_1 = 0x6B;
const uint8_t REG_WHO_AM_I = 0x75;

const uint8_t WHO_AM_I_MPU6050 = 0x68;
const uint8_t WHO_AM_I_MPU6500 = 0x70;

// Os mesmos valores do sketch.ino (C2_ACCEL_CONFIG, C2_DLPF_CFG, C2_A_DLPF_CFG).
const uint8_t ACCEL_8G = 2u << 3;     // AFS_SEL = 2: +-8 g, 4 096 LSB/g
const uint8_t GYRO_500DPS = 1u << 3;  // FS_SEL = 1: +-500 deg/s
const uint8_t DLPF_21HZ = 4;

const float LSB_POR_G = 4096.0;
const float G_PADRAO = 9.80665;  // o SENSORS_GRAVITY_STANDARD da Adafruit

struct Chip {
  const char *nome;
  bool filtro_em_accel_config2;
  float temp_lsb_por_grau;  // T = bruto / temp_lsb_por_grau + temp_com_bruto_zero
  float temp_com_bruto_zero;
};

// As conversoes de temperatura sao as do perfil_do_sensor.h (FW-21; driver
// `inv_mpu6050` do Linux). Chip desconhecido: sem 0x1D, temperatura do MPU6050.
const Chip CHIP_MPU6050 = {"MPU6050", false, 340.0, 36.53};
const Chip CHIP_MPU6500 = {"MPU6500", true, 333.87, 21.0};
const Chip CHIP_DESCONHECIDO = {"desconhecido", false, 340.0, 36.53};

const Chip *chip = &CHIP_DESCONHECIDO;
uint8_t who_am_i = 0;

// --- Parametros da medicao ----------------------------------------------

// Referencia teorica. NAO e o que o sensor le - e o que ele DEVERIA ler, e a
// diferenca entre as duas coisas e justamente o que este sketch mede.
const float GRAVIDADE = 9.81;

const int   AMOSTRAS       = 500;   // ~2 s a 4 ms
const int   INTERVALO_MS   = 4;
const int   ASSENTAMENTO_MS = 1500; // tempo para a mao sair e a placa parar

// Acima disso a pose foi medida com a placa tremendo. O valor vem da medicao
// real de 2026-08-24, que deu 0,043 m/s2 de desvio-padrao com o sensor
// imovel; 0,15 e folga generosa que ainda pega mao encostada.
const float RUIDO_MAXIMO = 0.15;

// Parado na Terra, |a| vale ~9,81 em QUALQUER pose. Bem abaixo disso nao e
// pose ruim: e ausencia de medida.
//
// O caso classico e alimentacao mal encaixada. Sem VCC firme, o MPU6050
// sobrevive do vazamento dos resistores de pull-up do I2C: energia bastante
// para responder no barramento - entao `mpu.begin()` PASSA - e insuficiente
// para os sensores funcionarem. Todos os registradores voltam zero.
//
// O sintoma delator e a temperatura: com o registrador zerado, a conversao
// devolve exatamente a constante do chip -- 36,53 C no MPU6050, 21,0 C no
// MPU6500. Se aparecer isso com |a| = 0, o problema e fiacao, nao pose.
//
// Foi um furo desta versao: os dois avisos anteriores nao disparavam com
// zero (`0 > 0,15` e falso, e `0 < 0,90*0` tambem), entao o sketch aceitava
// leitura vazia calado e seguia para a pose seguinte.
const float MAGNITUDE_MINIMA_PLAUSIVEL = 3.0;
const float MAGNITUDE_MAXIMA_PLAUSIVEL = 20.0;

// --- Poses ---------------------------------------------------------------

const int N_POSES = 6;

struct Pose {
  const char *nome;
  const char *instrucao;
  int   eixo;    // 0=X, 1=Y, 2=Z
  float sinal;   // +1 se o eixo aponta para CIMA
};

const Pose POSES[N_POSES] = {
  {"Z+", "componentes para CIMA, placa deitada e nivelada", 2, +1},
  {"Z-", "componentes para BAIXO, placa deitada de cabeca para baixo", 2, -1},
  {"X+", "borda do eixo X apontando para CIMA", 0, +1},
  {"X-", "borda do eixo X apontando para BAIXO", 0, -1},
  {"Y+", "borda do eixo Y apontando para CIMA", 1, +1},
  {"Y-", "borda do eixo Y apontando para BAIXO", 1, -1},
};

struct Medida {
  float eixo[3];   // media de ax, ay, az
  float mag;       // media das magnitudes instantaneas
  float ruido;     // desvio-padrao das magnitudes
  float temp;
};

Medida medidas[N_POSES];

// A IDE do Arduino gera prototipos sozinha; declarar aqui evita depender
// disso caso o arquivo seja compilado por outra toolchain.
void esperarEnter();
Medida medirPose();
void relatorio();
bool escrever(uint8_t reg, uint8_t valor);
bool ler(uint8_t reg, uint8_t *dest, uint8_t n);
bool configurarSensor();
bool lerAmostra(float *x, float *y, float *z, float *temp);

// --- O chip --------------------------------------------------------------

bool escrever(uint8_t reg, uint8_t valor) {
  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(reg);
  Wire.write(valor);
  return Wire.endTransmission() == 0;
}

bool ler(uint8_t reg, uint8_t *dest, uint8_t n) {
  Wire.beginTransmission(MPU_ENDERECO);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(MPU_ENDERECO, n) != n) return false;
  for (uint8_t i = 0; i < n; i++) dest[i] = Wire.read();
  return true;
}

// A sequencia do `Adafruit_MPU6050::_init` (reset, caminhos de sinal,
// divisor 0, giroscopio +-500 deg/s, PLL do eixo X), com a faixa e o filtro
// do produto, e o 0x1D quando o chip e um MPU6500.
const char *passo_que_falhou = "";

bool configurarSensor() {
  passo_que_falhou = "ler o WHO_AM_I";
  if (!ler(REG_WHO_AM_I, &who_am_i, 1)) return false;
  if (who_am_i == WHO_AM_I_MPU6050) {
    chip = &CHIP_MPU6050;
  } else if (who_am_i == WHO_AM_I_MPU6500) {
    chip = &CHIP_MPU6500;
  } else {
    chip = &CHIP_DESCONHECIDO;
  }

  passo_que_falhou = "pedir o reset";
  if (!escrever(REG_PWR_MGMT_1, 0x80)) return false;  // DEVICE_RESET
  // Logo depois do reset o chip pode nao responder no I2C: uma leitura que
  // falha conta como "ainda em reset", e nao como erro.
  uint8_t pwr = 0x80;
  for (int i = 0; i < 200 && (pwr & 0x80); i++) {
    delay(1);
    if (!ler(REG_PWR_MGMT_1, &pwr, 1)) pwr = 0x80;
  }
  passo_que_falhou = "esperar o fim do reset";
  if (pwr & 0x80) return false;
  delay(100);
  passo_que_falhou = "resetar os caminhos de sinal";
  bool ok = escrever(REG_SIGNAL_PATH_RESET, 0x07);
  delay(100);
  // Acorda ANTES de configurar: o reset deixa o chip dormindo (SLEEP = 1).
  passo_que_falhou = "acordar o sensor";
  ok = ok && escrever(REG_PWR_MGMT_1, 0x01);  // acordado, PLL do giro X
  delay(100);
  if (!ok) return false;
  passo_que_falhou = "gravar a configuracao";
  ok = ok && escrever(REG_SMPLRT_DIV, 0);
  ok = ok && escrever(REG_CONFIG, DLPF_21HZ);
  if (chip->filtro_em_accel_config2) ok = ok && escrever(REG_ACCEL_CONFIG2, DLPF_21HZ);
  ok = ok && escrever(REG_GYRO_CONFIG, GYRO_500DPS);
  ok = ok && escrever(REG_ACCEL_CONFIG, ACCEL_8G);
  delay(50);
  if (!ok) return false;

  // Confere o que ficou gravado: um registrador que nao pegou estragaria a
  // calibracao inteira sem aviso.
  passo_que_falhou = "conferir a configuracao gravada";
  uint8_t cfg = 0, acc = 0, acc2 = 0;
  ok = ok && ler(REG_CONFIG, &cfg, 1) && ler(REG_ACCEL_CONFIG, &acc, 1);
  if (chip->filtro_em_accel_config2) ok = ok && ler(REG_ACCEL_CONFIG2, &acc2, 1);
  ok = ok && (cfg & 0x07) == DLPF_21HZ && (acc & 0x18) == ACCEL_8G;
  if (chip->filtro_em_accel_config2) ok = ok && (acc2 & 0x0F) == DLPF_21HZ;
  if (!ok) {
    Serial.printf("   lido: CONFIG 0x%02X, ACCEL_CONFIG 0x%02X, ACCEL_CONFIG 2 0x%02X\n", cfg, acc,
                  acc2);
  }
  return ok;
}

bool lerAmostra(float *x, float *y, float *z, float *temp) {
  uint8_t b[8];
  if (!ler(REG_ACCEL_XOUT_H, b, 8)) return false;
  const int16_t rx = (int16_t)((b[0] << 8) | b[1]);
  const int16_t ry = (int16_t)((b[2] << 8) | b[3]);
  const int16_t rz = (int16_t)((b[4] << 8) | b[5]);
  const int16_t rt = (int16_t)((b[6] << 8) | b[7]);
  *x = rx / LSB_POR_G * G_PADRAO;
  *y = ry / LSB_POR_G * G_PADRAO;
  *z = rz / LSB_POR_G * G_PADRAO;
  *temp = rt / chip->temp_lsb_por_grau + chip->temp_com_bruto_zero;
  return true;
}

// --- Utilitarios ---------------------------------------------------------

void esperarEnter() {
  while (Serial.available()) Serial.read();
  Serial.println("   >> Posicione, solte a mao e tecle ENTER.");
  while (Serial.available() == 0) delay(10);
  while (Serial.available()) Serial.read();
}

Medida medirPose() {
  Serial.print("   assentando");
  for (int i = 0; i < ASSENTAMENTO_MS / 250; i++) {
    Serial.print(".");
    delay(250);
  }
  Serial.println();

  double soma[3] = {0, 0, 0};
  double somaMag = 0, somaMag2 = 0, somaTemp = 0;
  int falhas = 0;

  for (int i = 0; i < AMOSTRAS; i++) {
    float x = 0, y = 0, z = 0, temperatura = 0;
    // Uma falha de I2C vira amostra zerada, que a checagem de magnitude da
    // pose acusa; a contagem sai no log.
    if (!lerAmostra(&x, &y, &z, &temperatura)) falhas++;
    soma[0] += x;
    soma[1] += y;
    soma[2] += z;

    double m = sqrt((double)x * x + (double)y * y + (double)z * z);
    somaMag  += m;
    somaMag2 += m * m;
    somaTemp += temperatura;
    delay(INTERVALO_MS);
  }
  if (falhas > 0) {
    Serial.printf("   AVISO: %d de %d leituras falharam no I2C.\n", falhas, AMOSTRAS);
  }

  Medida md;
  for (int e = 0; e < 3; e++) md.eixo[e] = soma[e] / AMOSTRAS;
  md.mag   = somaMag / AMOSTRAS;
  double var = (somaMag2 / AMOSTRAS) - (md.mag * md.mag);
  md.ruido = var > 0 ? sqrt(var) : 0.0;
  md.temp  = somaTemp / AMOSTRAS;
  return md;
}

// --- Setup ---------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  delay(500);

  Wire.begin(21, 22);
  // Iguais ao sketch.ino de producao, para o resultado transferir: +-8 g e o
  // filtro de 21 Hz (FW-06), no registrador certo de cada chip (FW-23).
  if (!configurarSensor()) {
    Serial.printf("ERRO: falhou ao %s (WHO_AM_I lido: 0x%02X). Confira 3V3, GND, SDA=21, "
                  "SCL=22.\n", passo_que_falhou, who_am_i);
    while (1) delay(100);
  }

  Serial.println();
  Serial.println("=====================================================");
  Serial.printf(" CARACTERIZACAO DE 6 POSICOES - %s (WHO_AM_I 0x%02X)\n", chip->nome, who_am_i);
  Serial.println("=====================================================");
  Serial.printf(" Faixa: +-8 g | Giro: +-500 deg/s | Filtro: 21 Hz%s\n",
                chip->filtro_em_accel_config2 ? " (CONFIG e ACCEL_CONFIG 2)" : "");
  if (chip == &CHIP_DESCONHECIDO) {
    Serial.println(" AVISO: chip desconhecido. O filtro do acelerometro pode nao estar");
    Serial.println(" ligado, e a temperatura usa a conversao do MPU6050.");
  }
  Serial.print  (" Amostras por pose: ");
  Serial.println(AMOSTRAS);
  Serial.println();
  Serial.println(" Apoie a placa numa superficie firme e SOLTE A MAO.");
  Serial.println(" Dedo encostado transmite tremor e estraga a medida.");
  Serial.println();

  for (int p = 0; p < N_POSES; p++) {
    Serial.printf("[%d/%d] Pose %s - %s\n", p + 1, N_POSES, POSES[p].nome, POSES[p].instrucao);
    esperarEnter();
    medidas[p] = medirPose();

    const Medida &m = medidas[p];
    Serial.printf("   ax=%7.3f  ay=%7.3f  az=%7.3f  |a|=%6.3f  ruido=%.4f  %.1f C\n",
                  m.eixo[0], m.eixo[1], m.eixo[2], m.mag, m.ruido, m.temp);

    if (m.mag < MAGNITUDE_MINIMA_PLAUSIVEL || m.mag > MAGNITUDE_MAXIMA_PLAUSIVEL) {
      Serial.println();
      Serial.println("   ====================================================");
      Serial.printf("   PARADO: |a| = %.3f e fisicamente impossivel.\n", m.mag);
      Serial.println("   Em repouso, em qualquer pose, tem que dar ~9,81.");
      Serial.println();
      if (m.mag < 0.01) {
        Serial.printf("   A temperatura marcou %.1f C. Se for %.1f, e o valor que a\n",
                      m.temp, chip->temp_com_bruto_zero);
        Serial.printf("   conversao do %s produz com o registrador ZERADO.\n", chip->nome);
        Serial.println("   Sensor respondendo no I2C mas sem medir = alimentacao solta.");
        Serial.println();
        Serial.println("   CONFIRA, nesta ordem:");
        Serial.println("     1. 3V3 do ESP32 -> VCC do MPU6050  (o suspeito numero um)");
        Serial.println("     2. GND -> GND");
        Serial.println("     3. GPIO21 -> SDA   e   GPIO22 -> SCL");
        Serial.println("   Reencaixe os jumpers e grave de novo.");
      }
      Serial.println("   ====================================================");
      while (1) delay(1000);
    }

    if (m.ruido > RUIDO_MAXIMO) {
      Serial.printf("   AVISO: ruido %.4f acima de %.2f - a placa tremeu. "
                    "Vale repetir esta pose.\n", m.ruido, RUIDO_MAXIMO);
    }
    // A componente do eixo da pose deveria dominar; se nao domina, a face
    // apoiada nao e a que o usuario pensa que e.
    float principal = fabs(m.eixo[POSES[p].eixo]);
    if (principal < 0.90 * m.mag) {
      Serial.printf("   AVISO: o eixo %s nao domina a leitura (%.2f de %.2f). "
                    "A pose pode estar torta ou trocada.\n",
                    POSES[p].nome, principal, m.mag);
    }
    Serial.println();
  }

  relatorio();
}

// --- Relatorio -----------------------------------------------------------

void relatorio() {
  // Indices das poses por eixo: {cima, baixo}
  const int PAR[3][2] = {{2, 3}, {4, 5}, {0, 1}};  // X, Y, Z
  const char *NOME_EIXO[3] = {"X", "Y", "Z"};

  float vies[3], escala[3];
  for (int e = 0; e < 3; e++) {
    float cima  = medidas[PAR[e][0]].eixo[e];
    float baixo = medidas[PAR[e][1]].eixo[e];
    vies[e]   = (cima + baixo) / 2.0;
    escala[e] = (cima - baixo) / (2.0 * GRAVIDADE);
  }

  float somaMag = 0, minMag = 1e9, maxMag = -1e9;
  for (int p = 0; p < N_POSES; p++) {
    somaMag += medidas[p].mag;
    if (medidas[p].mag < minMag) minMag = medidas[p].mag;
    if (medidas[p].mag > maxMag) maxMag = medidas[p].mag;
  }
  float mediaMag = somaMag / N_POSES;

  Serial.println();
  Serial.println("=====================================================");
  Serial.println("COPIE DAQUI PARA BAIXO");
  Serial.println("=====================================================");
  Serial.printf("chip,%s,0x%02X\n", chip->nome, who_am_i);

  Serial.println("pose,ax,ay,az,mag,ruido,temp");
  for (int p = 0; p < N_POSES; p++) {
    const Medida &m = medidas[p];
    Serial.printf("%s,%.4f,%.4f,%.4f,%.4f,%.4f,%.1f\n",
                  POSES[p].nome, m.eixo[0], m.eixo[1], m.eixo[2],
                  m.mag, m.ruido, m.temp);
  }

  Serial.println();
  Serial.println("eixo,vies,escala");
  for (int e = 0; e < 3; e++) {
    Serial.printf("%s,%.4f,%.5f\n", NOME_EIXO[e], vies[e], escala[e]);
  }

  Serial.println();
  Serial.printf("magnitude_media_bruta,%.4f\n", mediaMag);
  Serial.printf("magnitude_min,%.4f\n", minMag);
  Serial.printf("magnitude_max,%.4f\n", maxMag);
  Serial.printf("dispersao_entre_poses,%.4f\n", maxMag - minMag);
  Serial.printf("fator_de_escala_unico,%.5f\n", GRAVIDADE / mediaMag);

  // Verificacao: aplica a correcao e mostra o que sobra. Se a calibracao
  // presta, as seis magnitudes corrigidas caem perto de 9,81.
  Serial.println();
  Serial.println("pose,mag_corrigida,erro_residual");
  float piorErro = 0;
  for (int p = 0; p < N_POSES; p++) {
    float c[3];
    for (int e = 0; e < 3; e++) {
      c[e] = (medidas[p].eixo[e] - vies[e]) / (escala[e] != 0 ? escala[e] : 1.0);
    }
    float mag = sqrt(c[0] * c[0] + c[1] * c[1] + c[2] * c[2]);
    float erro = fabs(mag - GRAVIDADE);
    if (erro > piorErro) piorErro = erro;
    Serial.printf("%s,%.4f,%.4f\n", POSES[p].nome, mag, erro);
  }
  Serial.printf("pior_erro_residual,%.4f\n", piorErro);

  Serial.println();
  Serial.println("=====================================================");
  Serial.println("FIM - copie ate aqui");
  Serial.println("=====================================================");
  Serial.println();

  // Leitura em portugues do que os numeros querem dizer.
  Serial.println("Interpretacao rapida:");
  if (maxMag - minMag < 0.10) {
    Serial.printf("  As 6 magnitudes ficaram juntas (dispersao %.3f). Isso aponta\n",
                  maxMag - minMag);
    Serial.printf("  ERRO DE ESCALA: um fator unico de %.4f resolveria.\n",
                  GRAVIDADE / mediaMag);
  } else {
    Serial.printf("  As 6 magnitudes variam %.3f entre si. Isso aponta VIES POR\n",
                  maxMag - minMag);
    Serial.println("  EIXO: cada eixo precisa do proprio offset, e um fator unico");
    Serial.println("  nao daria conta.");
  }
  Serial.printf("  Depois de corrigir, o pior erro residual e %.4f m/s2.\n", piorErro);
  Serial.printf("  Para comparar: o limiar de movimento vale 1,2 m/s2.\n");
}

void loop() {
  delay(1000);
}
