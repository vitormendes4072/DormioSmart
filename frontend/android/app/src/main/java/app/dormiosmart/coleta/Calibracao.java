package app.dormiosmart.coleta;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Locale;
import java.util.Properties;

/**
 * A calibracao do acelerometro de uma noite (CAL-03, etapa 2).
 *
 * <p>Quem estima e o nucleo ({@code firmware/nucleo/calibracao.h}, pela ponte
 * {@link NucleoNativo#estimar}); esta classe so carrega o resultado, o grava ao
 * lado da noite ({@code noite-<ts>.jsonl.calibracao}) e o devolve ao nucleo. A
 * noite inteira usa a mesma: e o que deixa cada noite dizer com qual
 * calibracao saiu.
 *
 * <p>Sem {@link #aceita}, os parametros sao os da identidade, e o nucleo nao
 * mexe nas amostras.
 */
public final class Calibracao {

    /** Sufixo do arquivo ao lado da noite. */
    public static final String SUFIXO = ".calibracao";

    /** Tamanho do vetor que {@link NucleoNativo#estimar} devolve. */
    public static final int TAMANHO_DO_RESULTADO = 19;

    public boolean aceita;
    public final double[] desvio = {0, 0, 0};
    public final double[] escala = {1, 1, 1};
    public final double[] coefTemp = {0, 0, 0};
    public double tempRefC;
    /** 0 fixo, 1 so o desvio, 2 desvio e escala (o {@code ModoDoEixo} do nucleo). */
    public final int[] modos = {0, 0, 0};
    public boolean usouTemperatura;
    public int pontos;
    public double erroAntesG;
    public double erroDepoisG;
    public int iteracoes;

    /**
     * Do vetor do nucleo: [aceita, desvio x3, escala x3, coef_temp x3, temp_ref,
     * modos x3, usou_temperatura, n, erro_antes, erro_depois, iteracoes].
     */
    public static Calibracao doResultado(double[] r) {
        if (r == null || r.length != TAMANHO_DO_RESULTADO) {
            throw new IllegalArgumentException("resultado da estimativa malformado");
        }
        final Calibracao c = new Calibracao();
        c.aceita = r[0] != 0;
        for (int k = 0; k < 3; k++) {
            c.desvio[k] = r[1 + k];
            c.escala[k] = r[4 + k];
            c.coefTemp[k] = r[7 + k];
            c.modos[k] = (int) r[11 + k];
        }
        c.tempRefC = r[10];
        c.usouTemperatura = r[14] != 0;
        c.pontos = (int) r[15];
        c.erroAntesG = r[16];
        c.erroDepoisG = r[17];
        c.iteracoes = (int) r[18];
        return c;
    }

    /** O que {@link NucleoNativo#definirCalibracao} recebe: [aceita, desvio x3, escala x3, coef x3, temp_ref]. */
    public double[] parametros() {
        return new double[] {
            aceita ? 1 : 0,
            desvio[0], desvio[1], desvio[2],
            escala[0], escala[1], escala[2],
            coefTemp[0], coefTemp[1], coefTemp[2],
            tempRefC,
        };
    }

    private static final Locale PT_BR = Locale.forLanguageTag("pt-BR");

    /** O que a tela mostra: aceita, ou quantos pontos faltam, ou por que foi recusada. */
    public String resumo(int pontosMinimos) {
        if (aceita) {
            return String.format(PT_BR, "Calibrado: erro de %.1f mg para %.1f mg, com %d épocas paradas",
                    1000 * erroAntesG, 1000 * erroDepoisG, pontos);
        }
        if (pontos < pontosMinimos) {
            return String.format(PT_BR, "Calibrando: %d de %d épocas paradas", pontos, pontosMinimos);
        }
        return String.format(PT_BR, "Calibração recusada: o erro ficou em %.1f mg", 1000 * erroDepoisG);
    }

    public static File arquivoDa(File pasta, String noite) {
        return new File(pasta, noite + SUFIXO);
    }

    public void salvar(File destino) throws IOException {
        final Properties p = new Properties();
        p.setProperty("aceita", Boolean.toString(aceita));
        for (int k = 0; k < 3; k++) {
            p.setProperty("desvio_" + k, Double.toString(desvio[k]));
            p.setProperty("escala_" + k, Double.toString(escala[k]));
            p.setProperty("coef_temp_" + k, Double.toString(coefTemp[k]));
            p.setProperty("modo_" + k, Integer.toString(modos[k]));
        }
        p.setProperty("temp_ref_c", Double.toString(tempRefC));
        p.setProperty("usou_temperatura", Boolean.toString(usouTemperatura));
        p.setProperty("pontos", Integer.toString(pontos));
        p.setProperty("erro_antes_g", Double.toString(erroAntesG));
        p.setProperty("erro_depois_g", Double.toString(erroDepoisG));
        p.setProperty("iteracoes", Integer.toString(iteracoes));
        try (OutputStream s = new FileOutputStream(destino)) {
            p.store(s, "Dormio CAL-03");
        }
    }

    /** A calibracao gravada; a identidade se o arquivo nao existe ou nao se le. */
    public static Calibracao ler(File origem) {
        final Calibracao c = new Calibracao();
        if (!origem.exists()) return c;
        final Properties p = new Properties();
        try (InputStream s = new FileInputStream(origem)) {
            p.load(s);
            c.aceita = Boolean.parseBoolean(p.getProperty("aceita", "false"));
            for (int k = 0; k < 3; k++) {
                c.desvio[k] = Double.parseDouble(p.getProperty("desvio_" + k, "0"));
                c.escala[k] = Double.parseDouble(p.getProperty("escala_" + k, "1"));
                c.coefTemp[k] = Double.parseDouble(p.getProperty("coef_temp_" + k, "0"));
                c.modos[k] = Integer.parseInt(p.getProperty("modo_" + k, "0"));
            }
            c.tempRefC = Double.parseDouble(p.getProperty("temp_ref_c", "0"));
            c.usouTemperatura = Boolean.parseBoolean(p.getProperty("usou_temperatura", "false"));
            c.pontos = Integer.parseInt(p.getProperty("pontos", "0"));
            c.erroAntesG = Double.parseDouble(p.getProperty("erro_antes_g", "0"));
            c.erroDepoisG = Double.parseDouble(p.getProperty("erro_depois_g", "0"));
            c.iteracoes = Integer.parseInt(p.getProperty("iteracoes", "0"));
        } catch (IOException | NumberFormatException e) {
            // Um arquivo estragado nao pode calibrar com lixo: volta a identidade.
            return new Calibracao();
        }
        // Escala zero ou absurda tambem e lixo: a divisao do `desfazer` explodiria.
        for (int k = 0; k < 3; k++) {
            if (!(c.escala[k] > 0.5 && c.escala[k] < 1.5)) return new Calibracao();
        }
        return c;
    }
}
