package com.nova.assistant.reminder;

import org.junit.Test;
import static org.junit.Assert.*;

public class ReminderIdTest {

    @Test
    public void testStableRequestCodeGeneration() {
        String id1 = "rem_12345_abcde";
        int reqCode1 = ReminderId.toRequestCode(id1);
        int reqCode2 = ReminderId.toRequestCode(id1);

        assertEquals("Same reminder ID must produce identical PendingIntent requestCode", reqCode1, reqCode2);
        assertTrue("Request code must be a non-negative 31-bit integer", reqCode1 >= 0);
    }

    @Test
    public void testNullAndEmptyHandling() {
        assertEquals(0, ReminderId.toRequestCode((String) null));
        assertEquals(0, ReminderId.toRequestCode(""));
    }

    @Test
    public void testIntOverload() {
        int code = ReminderId.toRequestCode(-999);
        assertTrue(code >= 0);
        assertEquals(999, code);
    }

    @Test
    public void testDeterministicRestoreIdentity() {
        String canonicalUuid = "550e8400-e29b-41d4-a716-446655440000";
        String taskTitle = "Học lập trình Android";
        long timestamp = 1790800000000L;

        // Serialized representation saved to SharedPreferences:
        String serialized = canonicalUuid + "|||" + taskTitle + "|||" + timestamp;

        // Simulate restore parsing in NovaBootReceiver:
        String[] parts = serialized.split("\\|\\|\\|");
        assertEquals(3, parts.length);
        String restoredReminderId = parts[0];
        String restoredTitle = parts[1];
        long restoredTimestamp = Long.parseLong(parts[2]);

        assertEquals("Restored canonical reminderId must match original UUID", canonicalUuid, restoredReminderId);
        assertEquals("Restored title must match", taskTitle, restoredTitle);
        assertEquals("Restored timestamp must match", timestamp, restoredTimestamp);

        int originalCode = ReminderId.toRequestCode(canonicalUuid);
        int restoredCode = ReminderId.toRequestCode(restoredReminderId);

        assertEquals("PendingIntent request code must remain identical across reboot restore", originalCode, restoredCode);
    }
}
