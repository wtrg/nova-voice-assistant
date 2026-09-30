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
}
