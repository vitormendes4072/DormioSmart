package app.dormiosmart.coleta;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Properties;

/**
 * O que a tela e o diagnostico precisam saber de uma noite (APP-02).
 *
 * <p>Gravado num arquivo {@code .properties} ao lado das epocas, para sobreviver
 * a morte do servico: e por ele que a retomada sabe que havia uma noite em
 * andamento, e em qual arquivo continuar. Java puro, testado na JVM.
 */
public final class EstadoDaNoite {

    public boolean ativa;
    public long inicioUtcMs;
    public String arquivo = "";
    public long epocasGravadas;
    public long recusadas;
    public long recusadasPorTaxa;
    public long semFeatures;
    public long semPayload;
    public long amostras;
    public long foraDeOrdem;
    /** A taxa medida pela cadeia na ultima epoca pronta, em mHz. */
    public long taxaMiliHz;
    /** Quantas vezes o sistema matou o servico e ele voltou. */
    public long retomadas;
    public long ultimaEpocaUtcMs;
    /** Temperatura do aparelho (bateria), em decimos de grau; Long.MIN_VALUE se nunca lida. */
    public long temperaturaDecimos = Long.MIN_VALUE;
    /** Deslocamento aplicado ao relogio do sensor (ver RelogioDoSensor), em ns. */
    public long deslocamentoDoRelogioNs;
    /** CAL-03: se a noite saiu calibrada, e o resumo para a tela. */
    public boolean calibrada;
    public String calibracaoResumo = "";
    /** Quantas epocas paradas desta noite viraram ponto de calibracao. */
    public long pontosDeCalibracao;

    public void salvar(File destino) throws IOException {
        final Properties p = new Properties();
        p.setProperty("ativa", Boolean.toString(ativa));
        p.setProperty("inicio_utc_ms", Long.toString(inicioUtcMs));
        p.setProperty("arquivo", arquivo);
        p.setProperty("epocas_gravadas", Long.toString(epocasGravadas));
        p.setProperty("recusadas", Long.toString(recusadas));
        p.setProperty("recusadas_por_taxa", Long.toString(recusadasPorTaxa));
        p.setProperty("sem_features", Long.toString(semFeatures));
        p.setProperty("sem_payload", Long.toString(semPayload));
        p.setProperty("amostras", Long.toString(amostras));
        p.setProperty("fora_de_ordem", Long.toString(foraDeOrdem));
        p.setProperty("taxa_mhz", Long.toString(taxaMiliHz));
        p.setProperty("retomadas", Long.toString(retomadas));
        p.setProperty("ultima_epoca_utc_ms", Long.toString(ultimaEpocaUtcMs));
        p.setProperty("temperatura_decimos", Long.toString(temperaturaDecimos));
        p.setProperty("deslocamento_relogio_ns", Long.toString(deslocamentoDoRelogioNs));
        p.setProperty("calibrada", Boolean.toString(calibrada));
        p.setProperty("calibracao_resumo", calibracaoResumo);
        p.setProperty("pontos_de_calibracao", Long.toString(pontosDeCalibracao));
        // Grava num temporario e troca: um corte no meio nao deixa estado pela metade.
        final File tmp = new File(destino.getPath() + ".tmp");
        try (OutputStream s = new FileOutputStream(tmp)) {
            p.store(s, "Dormio APP-02");
        }
        if (!tmp.renameTo(destino)) {
            if (!destino.delete() || !tmp.renameTo(destino)) {
                throw new IOException("nao trocou " + destino);
            }
        }
    }

    /** Le o estado gravado; um estado vazio (inativo) se o arquivo nao existe. */
    public static EstadoDaNoite ler(File origem) throws IOException {
        final EstadoDaNoite e = new EstadoDaNoite();
        if (!origem.exists()) return e;
        final Properties p = new Properties();
        try (InputStream s = new FileInputStream(origem)) {
            p.load(s);
        }
        e.ativa = Boolean.parseBoolean(p.getProperty("ativa", "false"));
        e.inicioUtcMs = numero(p, "inicio_utc_ms", 0);
        e.arquivo = p.getProperty("arquivo", "");
        e.epocasGravadas = numero(p, "epocas_gravadas", 0);
        e.recusadas = numero(p, "recusadas", 0);
        e.recusadasPorTaxa = numero(p, "recusadas_por_taxa", 0);
        e.semFeatures = numero(p, "sem_features", 0);
        e.semPayload = numero(p, "sem_payload", 0);
        e.amostras = numero(p, "amostras", 0);
        e.foraDeOrdem = numero(p, "fora_de_ordem", 0);
        e.taxaMiliHz = numero(p, "taxa_mhz", 0);
        e.retomadas = numero(p, "retomadas", 0);
        e.ultimaEpocaUtcMs = numero(p, "ultima_epoca_utc_ms", 0);
        e.temperaturaDecimos = numero(p, "temperatura_decimos", Long.MIN_VALUE);
        e.deslocamentoDoRelogioNs = numero(p, "deslocamento_relogio_ns", 0);
        e.calibrada = Boolean.parseBoolean(p.getProperty("calibrada", "false"));
        e.calibracaoResumo = p.getProperty("calibracao_resumo", "");
        e.pontosDeCalibracao = numero(p, "pontos_de_calibracao", 0);
        return e;
    }

    private static long numero(Properties p, String chave, long padrao) {
        try {
            return Long.parseLong(p.getProperty(chave, Long.toString(padrao)));
        } catch (NumberFormatException ex) {
            return padrao;
        }
    }
}
