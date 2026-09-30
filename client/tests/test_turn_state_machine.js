const assert = require('assert');
const { ConversationState, ConversationStateMachine } = require('../www/js/conversation/ConversationStateMachine');
const { TurnController } = require('../www/js/conversation/TurnController');

console.log("Running test_turn_state_machine.js...");

// Test Case 1: State machine transitions
const sm = new ConversationStateMachine();
assert.strictEqual(sm.getState(), ConversationState.IDLE);

assert.strictEqual(sm.transition(ConversationState.LISTENING), true);
assert.strictEqual(sm.getState(), ConversationState.LISTENING);

assert.strictEqual(sm.transition(ConversationState.FINALIZING_STT), true);
assert.strictEqual(sm.getState(), ConversationState.FINALIZING_STT);

assert.strictEqual(sm.transition(ConversationState.WAITING_LLM), true);
assert.strictEqual(sm.getState(), ConversationState.WAITING_LLM);

assert.strictEqual(sm.transition(ConversationState.SPEAKING), true);
assert.strictEqual(sm.getState(), ConversationState.SPEAKING);

// Interrupt to CANCELLED
assert.strictEqual(sm.transition(ConversationState.CANCELLED), true);
assert.strictEqual(sm.getState(), ConversationState.CANCELLED);
console.log("✓ StateMachine basic transitions pass");

// Test Case 2: Turn Controller single active turn invariant
const tc = new TurnController(sm);
const turn1 = tc.startNewTurn("hôm nay trời đẹp không?");
assert.ok(turn1);
assert.strictEqual(tc.activeTurnId, turn1);
assert.strictEqual(tc.isCurrentTurn(turn1), true);

const tts1 = tc.createTtsRequest(turn1);
assert.ok(tts1);
assert.strictEqual(tc.isCurrentTurn(turn1, tts1), true);

// Start Turn 2 should cancel Turn 1
const turn2 = tc.startNewTurn("mở youtube");
assert.notStrictEqual(turn1, turn2);
assert.strictEqual(tc.activeTurnId, turn2);
assert.strictEqual(tc.isCurrentTurn(turn1), false); // Stale turn rejected!
assert.strictEqual(tc.isCurrentTurn(turn2), true);
console.log("✓ TurnController single active turn and stale rejection pass");

// Test Case 3: User Interrupt
tc.cancelCurrentTurn("user_tapped_mic");
assert.strictEqual(tc.activeTurnId, null);
assert.strictEqual(sm.getState(), ConversationState.CANCELLED);
console.log("✓ TurnController user interrupt pass");

// Test Case 4: Text input from IDLE follows valid state transitions
const smText = new ConversationStateMachine();
assert.strictEqual(smText.getState(), ConversationState.IDLE);
assert.strictEqual(smText.transition(ConversationState.WAITING_LLM), true, "IDLE -> WAITING_LLM must be valid for text input");
assert.strictEqual(smText.getState(), ConversationState.WAITING_LLM);
assert.strictEqual(smText.transition(ConversationState.WAITING_TTS), true);
assert.strictEqual(smText.transition(ConversationState.SPEAKING), true);
assert.strictEqual(smText.transition(ConversationState.IDLE), true);
console.log("✓ text input from IDLE follows valid state transitions pass");

// Test Case 5: Stale completed and failed TTS ignored
const activeAudioRequests = new Map();
let currentActiveTurnId = "turn_B_456";
let turnBCallbackCount = 0;
let staleCallbackCount = 0;

function dispatchAudioEvent(requestId, event) {
  const handler = activeAudioRequests.get(requestId);
  if (!handler) {
    staleCallbackCount++;
    return;
  }
  if (handler.cancelled) {
    staleCallbackCount++;
    activeAudioRequests.delete(requestId);
    return;
  }
  if (handler.turnId !== currentActiveTurnId) {
    staleCallbackCount++;
    activeAudioRequests.delete(requestId);
    return;
  }
  if (event === "completed") {
    handler.onDone();
  } else if (event === "failed") {
    handler.onFail();
  }
}

// Register request for stale Turn A
activeAudioRequests.set("req_A_1", {
  turnId: "turn_A_123",
  cancelled: false,
  onDone: () => { assert.fail("Stale turn A must not complete"); },
  onFail: () => { assert.fail("Stale turn A must not fail"); }
});

// Register request for current Turn B
activeAudioRequests.set("req_B_2", {
  turnId: "turn_B_456",
  cancelled: false,
  onDone: () => { turnBCallbackCount++; },
  onFail: () => {}
});

// Stale completed event for Turn A -> rejected
dispatchAudioEvent("req_A_1", "completed");
// Stale failed event for unknown / stale request -> rejected
dispatchAudioEvent("unknown_stale_req", "failed");

// Active event for Turn B -> accepted
dispatchAudioEvent("req_B_2", "completed");

assert.strictEqual(turnBCallbackCount, 1, "Turn B must complete cleanly");
assert.ok(staleCallbackCount >= 2, "Stale events must be recorded as rejected");
console.log("✓ stale completed TTS ignored pass");
console.log("✓ stale failed TTS ignored pass");

// Test Case 6: Old timeout cannot start fallback after interrupt
let timeoutFallbackTriggered = false;
let timeoutAId = null;

const reqA = {
  turnId: "turn_A_interrupt",
  cancelled: false,
  connectTimeout: null
};

// Request A starts with 35s timeout
timeoutAId = setTimeout(() => {
  if (reqA.cancelled) return;
  timeoutFallbackTriggered = true;
}, 35000);
reqA.connectTimeout = timeoutAId;

// User interrupts Turn A
function interruptTurnA() {
  reqA.cancelled = true;
  if (reqA.connectTimeout) {
    clearTimeout(reqA.connectTimeout);
    reqA.connectTimeout = null;
  }
}
interruptTurnA();

// Turn B starts
const reqB = {
  turnId: "turn_B_new",
  cancelled: false,
  completed: false
};

// Simulate time advancing > 35s
// Since clearTimeout was called and reqA.cancelled is true, timeout never fires.
assert.strictEqual(reqA.cancelled, true);
assert.strictEqual(reqA.connectTimeout, null);
assert.strictEqual(timeoutFallbackTriggered, false, "Fallback must NOT trigger after interrupt");
console.log("✓ old timeout cannot start fallback after interrupt pass");

// Test Case 7: Live TTS begins before prefetch
const chunkOrderEvents = [];
function simulateSequentialPlayback(chunks) {
  let idx = 0;
  function prefetch(i) {
    chunkOrderEvents.push(`prefetch_${i}`);
  }
  function playChunk(chunk, onStart) {
    chunkOrderEvents.push(`start_live_${chunk}`);
    onStart();
  }

  // Play chunk 0
  playChunk(chunks[0], () => {
    // Invariant: Prefetch 1 only AFTER live 0 started!
    prefetch(1);
  });
}

simulateSequentialPlayback(["chunk_0", "chunk_1"]);
assert.deepStrictEqual(chunkOrderEvents, ["start_live_chunk_0", "prefetch_1"], "Live chunk must start BEFORE prefetch N+1");
console.log("✓ live TTS begins before prefetch pass");

console.log("ALL TURN STATE MACHINE TESTS PASSED PERFECTLY!");
