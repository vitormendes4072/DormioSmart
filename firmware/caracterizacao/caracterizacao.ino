/*
 * caracterizacao.ino - calibracao de 6 posicoes do MPU6050 (CALC-02)
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
 * O `sketch.ino` de producao NAO chama setFilterBandwidth, entao roda no
 * padrao (260 Hz), que e barulhento. Medir aqui num filtro e usar outro no
 * produto invalidaria a transferencia do resultado.
 *
 * 21 Hz e a escolha certa para os dois: movimento de corpo em cama e um
 * fenomeno lento, na casa de poucos Hz. Tudo acima disso e vibracao do
 * movel, passo no comodo e ruido do proprio MEMS - largura de banda maior so
 * deixa entrar o que nao interessa. Alinhar o firmware e o item FW-06.
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

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <math.h>

Adafruit_MPU6050 mpu;

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
  sensors_event_t a, g, t;

  for (int i = 0; i < AMOSTRAS; i++) {
    mpu.getEvent(&a, &g, &t);
    float x = a.acceleration.x, y = a.acceleration.y, z = a.acceleration.z;
    soma[0] += x;
    soma[1] += y;
    soma[2] += z;

    double m = sqrt((double)x * x + (double)y * y + (double)z * z);
    somaMag  += m;
    somaMag2 += m * m;
    somaTemp += t.temperature;
    delay(INTERVALO_MS);
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
  if (!mpu.begin()) {
    Serial.println("ERRO: MPU6050 nao encontrado. Confira 3V3, GND, SDA=21, SCL=22.");
    while (1) delay(100);
  }

  // Iguais ao sketch.ino de producao, para o resultado transferir.
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  // Ver a nota sobre largura de banda no cabecalho (FW-06).
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  Serial.println();
  Serial.println("=====================================================");
  Serial.println(" CARACTERIZACAO DE 6 POSICOES - MPU6050 (CALC-02)");
  Serial.println("=====================================================");
  Serial.println(" Faixa: +-8 g | Giro: +-500 deg/s | Filtro: 21 Hz");
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
