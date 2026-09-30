package com.nova.assistant.reminder;

/**
 * CANONICAL REMINDER ID UTILITIES
 * 
 * Maps canonical reminder_id string to a stable positive 31-bit integer
 * for Android PendingIntent and AlarmManager request codes.
 */
public class ReminderId {
    public static int toRequestCode(String reminderId) {
        if (reminderId == null || reminderId.isEmpty()) {
            return 0;
        }
        int hash = reminderId.hashCode();
        return Math.abs(hash) & 0x7FFFFFFF;
    }

    public static int toRequestCode(int id) {
        return Math.abs(id) & 0x7FFFFFFF;
    }
}
