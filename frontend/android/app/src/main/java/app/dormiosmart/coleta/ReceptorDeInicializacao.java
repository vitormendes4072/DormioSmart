package app.dormiosmart.coleta;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * Reagenda o lembrete de dormir (APP-20) quando o Android esquece os alarmes:
 * ao reiniciar, ao atualizar o app e ao mudar a hora ou o fuso.
 *
 * <p>Exportado porque recebe avisos do sistema. So reagenda, e nunca mostra
 * nada: um aviso forjado por outro app nao consegue disparar o lembrete.
 */
public class ReceptorDeInicializacao extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent intent) {
        LembreteDeDormir.agendar(c);
    }
}
