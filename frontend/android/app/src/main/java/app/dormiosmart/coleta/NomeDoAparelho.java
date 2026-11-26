package app.dormiosmart.coleta;

import java.util.Locale;

/** Formata os campos publicos do sistema, sem consultar nomes pessoais. */
final class NomeDoAparelho {
    static String formatar(String fabricante, String modelo) {
        if (fabricante == null || modelo == null) return null;
        fabricante = fabricante.trim();
        modelo = modelo.trim();
        if (fabricante.isEmpty() || modelo.isEmpty()
                || fabricante.equalsIgnoreCase("unknown") || modelo.equalsIgnoreCase("unknown")) return null;
        fabricante = fabricante.substring(0, 1).toUpperCase(Locale.ROOT) + fabricante.substring(1);
        String nome = modelo.toLowerCase(Locale.ROOT).startsWith(fabricante.toLowerCase(Locale.ROOT))
                ? modelo.substring(0, 1).toUpperCase(Locale.ROOT) + modelo.substring(1) : fabricante + " " + modelo;
        return nome.length() > 60 ? nome.substring(0, 60).trim() : nome;
    }
}
