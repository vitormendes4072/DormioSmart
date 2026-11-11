package app.dormiosmart.coleta;

/**
 * Quando o servico encerra a noite sozinho pelo calor do aparelho (APP-02, etapa 4).
 *
 * <p>O protocolo poe o celular dentro da fronha, e um aparelho velho abafado
 * esquenta. Um aviso na tela nao adianta: quem devia le-lo esta dormindo. Entao
 * o servico encerra a noite e registra o motivo.
 *
 * <p>45 C e um valor de PARTIDA, conservador, nao medido nem tirado de folha de
 * dados deste aparelho: fica abaixo da faixa em que o Android costuma desligar
 * por calor, e o protocolo manda NAO carregar dentro da fronha. A constante e o
 * lugar de ajustar com o orientador. Java puro, testado na JVM.
 */
public final class CorteDeTemperatura {

    /** 45,0 C, em decimos de grau (a unidade do {@code BatteryManager}). */
    public static final int LIMITE_DECIMOS = 450;

    private CorteDeTemperatura() {}

    /** Encerra quando a bateria chega ao limite (inclusive). */
    public static boolean deveEncerrar(int temperaturaDecimos) {
        return temperaturaDecimos >= LIMITE_DECIMOS;
    }
}
