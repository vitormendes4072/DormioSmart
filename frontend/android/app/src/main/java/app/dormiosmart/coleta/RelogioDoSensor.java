package app.dormiosmart.coleta;

/**
 * Converte o carimbo do sensor para o relogio monotonico do sistema, em us (APP-02).
 *
 * <p>O {@code SensorEvent.timestamp} e "o instante em nanossegundos em que o
 * evento aconteceu", e na maioria dos aparelhos esta na base do
 * {@code SystemClock.elapsedRealtimeNanos()}. Na maioria, nao em todos: ha
 * aparelhos que usam o {@code uptimeMillis} (que para no sono) ou outra base.
 * A cadeia so precisa de intervalos certos, mas o servico amarra a hora real
 * (UTC) ao {@code elapsedRealtime}; com outra base, o {@code ts} de cada epoca
 * sairia deslocado.
 *
 * <p>Na primeira amostra, se o carimbo estiver a mais de {@link #LIMIAR_DE_BASE_NS}
 * do {@code elapsedRealtimeNanos}, a diferenca vira um deslocamento fixo. O erro
 * desse deslocamento e o atraso de entrega do lote (ate ~1 s), igual em todas as
 * amostras: os intervalos ficam exatos, e o {@code ts} erra no maximo isso.
 */
public final class RelogioDoSensor {

    /** Mais que o atraso de um lote do sensor (1 s) com folga. */
    public static final long LIMIAR_DE_BASE_NS = 10_000_000_000L;

    private boolean calibrado;
    private long deslocamentoNs;

    /**
     * @param carimboNs {@code SensorEvent.timestamp}
     * @param agoraNs {@code SystemClock.elapsedRealtimeNanos()} na entrega
     * @return o instante da amostra na base do {@code elapsedRealtime}, em us
     */
    public long paraMonotonicoUs(long carimboNs, long agoraNs) {
        if (!calibrado) {
            final long diferenca = agoraNs - carimboNs;
            deslocamentoNs = Math.abs(diferenca) > LIMIAR_DE_BASE_NS ? diferenca : 0L;
            calibrado = true;
        }
        return (carimboNs + deslocamentoNs) / 1000L;
    }

    /** O deslocamento aplicado, em ns; 0 quando o sensor ja usa a base certa. */
    public long deslocamentoNs() {
        return deslocamentoNs;
    }
}
