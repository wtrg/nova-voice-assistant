package com.nova.assistant;

import android.util.Log;

/**
 * V4-09: Điều phối độc quyền Audio (Microphone & Speaker)
 * Ngăn chặn xung đột giữa Hotword Service, STT và TTS.
 * Invariants:
 * HOTWORD -> LISTENING (Hotword detector paused)
 * LISTENING -> WAITING_LLM (Microphone released)
 * WAITING_LLM -> SPEAKING (No mic capture, output audio only)
 * SPEAKING -> IDLE hoặc HOTWORD
 * INTERRUPT: SPEAKING -> LISTENING
 */
public class AudioOwnershipCoordinator {
    private static final String TAG = "AudioOwnership";

    public enum AudioState {
        IDLE,
        HOTWORD,
        LISTENING,
        WAITING_LLM,
        SPEAKING
    }

    private static volatile AudioState currentState = AudioState.IDLE;
    private static volatile StateChangeListener listener = null;

    public interface StateChangeListener {
        void onStateChanged(AudioState oldState, AudioState newState);
    }

    public static synchronized void setListener(StateChangeListener l) {
        listener = l;
    }

    public static synchronized AudioState getCurrentState() {
        return currentState;
    }

    public static synchronized boolean requestState(AudioState requested) {
        AudioState old = currentState;
        if (old == requested) return true;

        Log.i(TAG, "Audio state transition: " + old + " -> " + requested);
        currentState = requested;

        if (listener != null) {
            try {
                listener.onStateChanged(old, requested);
            } catch (Exception e) {
                Log.w(TAG, "Error in state change listener: " + e.getMessage());
            }
        }
        return true;
    }
}
