package com.nova.assistant;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.util.Log;
import java.util.Map;

/**
 * Khôi phục toàn bộ danh sách báo thức khi điện thoại khởi động lại (F-09)
 */
public class NovaBootReceiver extends BroadcastReceiver {
    private static final String TAG = "NovaBootReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent != null ? intent.getAction() : null;
        if (Intent.ACTION_BOOT_COMPLETED.equals(action) ||
            "android.intent.action.MY_PACKAGE_REPLACED".equals(action) ||
            "android.intent.action.QUICKBOOT_POWERON".equals(action)) {
            
            Log.d(TAG, "Reboot/Package update detected (" + action + "), restoring scheduled alarms...");
            restoreAlarms(context);
        }
    }

    private void restoreAlarms(Context context) {
        try {
            SharedPreferences prefs = context.getSharedPreferences("nova_alarms_store", Context.MODE_PRIVATE);
            Map<String, ?> all = prefs.getAll();
            long now = System.currentTimeMillis();

            for (Map.Entry<String, ?> entry : all.entrySet()) {
                String key = entry.getKey();
                if (key.startsWith("alarm_")) {
                    try {
                        int id = Integer.parseInt(key.substring("alarm_".length()));
                        String val = String.valueOf(entry.getValue());
                        String[] parts = val.split("\\|\\|\\|");
                        if (parts.length == 2) {
                            String title = parts[0];
                            long timestamp = Long.parseLong(parts[1]);
                            if (timestamp > now) {
                                MainActivity.scheduleAlarmDirect(context, id, title, timestamp);
                                Log.d(TAG, "Restored alarm id=" + id + " for: " + title);
                            } else {
                                // Quá hạn, dọn dẹp
                                prefs.edit().remove(key).apply();
                            }
                        }
                    } catch (Exception ex) {
                        Log.w(TAG, "Error restoring alarm key: " + key, ex);
                    }
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to restore alarms", e);
        }
    }
}
