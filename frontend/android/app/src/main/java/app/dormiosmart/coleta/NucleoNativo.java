package app.dormiosmart.coleta;

/**
 * O nucleo do firmware, compilado para o celular (APP-02).
 *
 * <p>Cada metodo chama {@code firmware/nucleo/coletor_celular.h} pela ponte JNI
 * ({@code src/main/cpp/ponte.cpp}). Nenhuma conta mora aqui: as amostras do
 * acelerometro entram com o instante de cada uma, e saem payloads JSON no
 * formato exato que a placa envia, com as seis features do contrato.
 *
 * <p>Nao e seguro entre threads: uma instancia por noite, chamada pela thread
 * do servico de coleta.
 */
public final class NucleoNativo implements AutoCloseable {

    static {
        System.loadLibrary("dormio_nucleo");
    }

    /** Indices de {@link #contadores()}. */
    public static final int RECEBIDAS = 0;
    public static final int FORA_DE_ORDEM = 1;
    public static final int COM_PAYLOAD = 2;
    public static final int RECUSADAS = 3;
    public static final int RECUSADAS_POR_TAXA = 4;
    public static final int SEM_FEATURES = 5;
    public static final int SEM_PAYLOAD = 6;
    public static final int TAXA_MILI_HZ = 7;

    private long ponteiro;

    public NucleoNativo() {
        ponteiro = criar();
    }

    /**
     * Comeca uma noite.
     *
     * @param primeiraAmostraUs instante monotonico da primeira amostra; a epoca 0
     *     comeca {@link #antecedenciaDaOrigemUs()} depois dele
     * @param monoRefMs um instante do mesmo relogio monotonico, em ms
     * @param paredeRefMs o UTC (epoch unix, ms) naquele mesmo instante
     */
    public void iniciar(long primeiraAmostraUs, long monoRefMs, long paredeRefMs) {
        iniciar(ponteiro, primeiraAmostraUs + antecedenciaDaOrigemUs(), monoRefMs, paredeRefMs);
    }

    /** {@code n} amostras: {@code tUs[i]} e {@code xyz[3i..3i+2]} em m/s^2. */
    public void amostrar(long[] tUs, float[] xyz, int n) {
        amostrar(ponteiro, tUs, xyz, n);
    }

    public void definirTemperatura(float grausC) {
        definirTemperatura(ponteiro, grausC);
    }

    /** O proximo payload pronto, ou {@code null}. Chamar ate devolver null. */
    public String proximoPayload() {
        return proximoPayload(ponteiro);
    }

    public long[] contadores() {
        return contadores(ponteiro);
    }

    /** A calibracao desta noite (CAL-03). Chamar antes das amostras. */
    public void definirCalibracao(Calibracao c) {
        definirCalibracao(ponteiro, c.parametros());
    }

    /** {x, y, z, temp} da ultima epoca, se ela foi parada; senao {@code null}. */
    public double[] pontoParado() {
        return pontoParado(ponteiro);
    }

    /** Estima a calibracao a partir dos pontos guardados ({@link PontosDeCalibracao}). */
    public static Calibracao estimar(java.util.List<double[]> pontos) {
        final double[][] v = PontosDeCalibracao.paraEstimar(pontos);
        return Calibracao.doResultado(estimar(v[0], v[1], pontos.size()));
    }

    /** Quantas epocas paradas a estimativa exige ({@code PONTOS_MINIMOS_CALIBRACAO}). */
    public static native int pontosMinimos();

    @Override
    public void close() {
        if (ponteiro != 0) {
            destruir(ponteiro);
            ponteiro = 0;
        }
    }

    public static native long antecedenciaDaOrigemUs();

    private static native long criar();

    private static native void destruir(long p);

    private static native void iniciar(long p, long origemUs, long monoRefMs, long paredeRefMs);

    private static native void amostrar(long p, long[] tUs, float[] xyz, int n);

    private static native void definirTemperatura(long p, float grausC);

    private static native String proximoPayload(long p);

    private static native long[] contadores(long p);

    private static native void definirCalibracao(long p, double[] parametros);

    private static native double[] pontoParado(long p);

    private static native double[] estimar(double[] xyz, double[] temps, int n);
}
