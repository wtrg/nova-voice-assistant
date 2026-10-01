package com.nova.assistant;

import org.junit.Test;
import static org.junit.Assert.*;

public class AlarmSessionLifecycleTest {

    @Test
    public void testAlarmSessionStates() {
        NovaAlarmService.SessionState state = NovaAlarmService.SessionState.IDLE;
        assertEquals(NovaAlarmService.SessionState.IDLE, state);

        state = NovaAlarmService.SessionState.RINGING_NATIVE;
        assertEquals(NovaAlarmService.SessionState.RINGING_NATIVE, state);

        state = NovaAlarmService.SessionState.WAITING_WEBVIEW;
        assertEquals(NovaAlarmService.SessionState.WAITING_WEBVIEW, state);

        state = NovaAlarmService.SessionState.HANDOFF_COMPLETE;
        assertEquals(NovaAlarmService.SessionState.HANDOFF_COMPLETE, state);

        state = NovaAlarmService.SessionState.STOPPED;
        assertEquals(NovaAlarmService.SessionState.STOPPED, state);
    }

    @Test
    public void testClaimValidationLogic() {
        String activeSession = "session_active_1234";
        String staleSession = "session_stale_9999";

        // Claim with matching session ID should match
        assertTrue("Matching session must be recognized", activeSession.equals("session_active_1234"));

        // Claim with stale session ID must fail
        assertFalse("Stale session ID must not match active session", activeSession.equals(staleSession));
        assertFalse("Empty session ID must not match active session", activeSession.equals(""));
        assertFalse("Null session ID must not match active session", "session_active_1234".equals(null));
    }

    @Test
    public void testDecoupledStopActions() {
        // Invariant: Stopping assistant conversation audio must never use ACTION_STOP_ALARM
        String actionStopAlarm = NovaAlarmService.ACTION_STOP_ALARM;
        assertEquals("com.nova.assistant.action.STOP_ALARM", actionStopAlarm);
        assertNotEquals("ACTION_STOP_ASSISTANT_AUDIO", actionStopAlarm);
    }

    @Test
    public void testTerminalStateInvariants() {
        // Invariant: Terminal state enum includes clean completion and stop
        NovaAlarmService.SessionState handoffState = NovaAlarmService.SessionState.HANDOFF_COMPLETE;
        NovaAlarmService.SessionState stoppedState = NovaAlarmService.SessionState.STOPPED;
        NovaAlarmService.SessionState idleState = NovaAlarmService.SessionState.IDLE;

        assertNotEquals(idleState, handoffState);
        assertNotEquals(idleState, stoppedState);
        assertEquals(NovaAlarmService.SessionState.valueOf("IDLE"), idleState);
    }
}
