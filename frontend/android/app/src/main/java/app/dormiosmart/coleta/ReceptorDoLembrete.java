package app.dormiosmart.coleta;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * Recebe o alarme do lembrete de dormir (APP-20). Nao exportado: so o proprio
 * app o aciona, pelo {@code PendingIntent} do {@link LembreteDeDormir}.
 */
public class ReceptorDoLembrete extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent intent) {
        if (intent != null && LembreteDeDormir.ACAO_LEMBRAR.equals(intent.getAction())) {
            LembreteDeDormir.aoDisparar(c);
        }
    }
}
