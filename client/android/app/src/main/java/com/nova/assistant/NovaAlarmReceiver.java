package com.nova.assistant;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import androidx.core.content.ContextCompat;

/**
 * NovaAlarmReceiver
 * Tiếp nhận Alarm từ AlarmManager và chuyển giao ngay cho NovaAlarmService (Foreground Service)
 * để phát âm thanh chuông báo USAGE_ALARM và hiển thị thông báo tương tác an toàn.
 * Không phát âm thanh trực tiếp trong Receiver để tránh xung đột luồng và lỗi trên Android 8+.
 */
public class NovaAlarmReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (context == null) return;

        Intent serviceIntent = new Intent(context, NovaAlarmService.class);
        serviceIntent.setAction(NovaAlarmService.ACTION_START_ALARM);
        if (intent != null && intent.getExtras() != null) {
            serviceIntent.putExtras(intent.getExtras());
        }

        try {
            ContextCompat.startForegroundService(context, serviceIntent);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
