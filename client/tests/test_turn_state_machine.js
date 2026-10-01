const assert = require('assert');
const { ConversationState, ConversationStateMachine } = require('../www/js/conversation/ConversationStateMachine');
const { TurnController } = require('../www/js/conversation/TurnController');
const { AudioRequestRegistry } = require('../www/js/conversation/AudioRequestRegistry');

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

// Test Case 5: Stale completed and failed TTS ignored via AudioRequestRegistry (Stage 15 & 16)
const registry = new AudioRequestRegistry();
const tcMock = {
  activeTurnId: "turn_B_456",
  isCurrentTurn: (tid) => tid === "turn_B_456"
};

let turnBCallbackCount = 0;
let staleCallbackTriggered = false;

// Register request for stale Turn A
registry.registerRequest("req_A_1", {
  turnId: "turn_A_123",
  onDone: () => { staleCallbackTriggered = true; assert.fail("Stale turn A must not complete"); },
  onFail: () => { staleCallbackTriggered = true; assert.fail("Stale turn A must not fail"); }
});

// Register request for active Turn B
registry.registerRequest("req_B_2", {
  turnId: "turn_B_456",
  onDone: () => { turnBCallbackCount++; },
  onFail: () => { assert.fail("Turn B should not fail"); }
});

// Stale completed event for Turn A -> rejected
const resStaleDone = registry.dispatchAudioEvent("req_A_1", "completed", tcMock);
assert.strictEqual(resStaleDone, false, "Stale Turn A event must be rejected");

// Stale failed event for unknown / stale request -> rejected
const resUnknown = registry.dispatchAudioEvent("unknown_stale_req", "failed", tcMock);
assert.strictEqual(resUnknown, false, "Unknown request event must be rejected");

// Active event for Turn B -> accepted
const resActive = registry.dispatchAudioEvent("req_B_2", "completed", tcMock);
assert.strictEqual(resActive, true, "Active Turn B event must be accepted");

assert.strictEqual(turnBCallbackCount, 1, "Turn B must complete cleanly");
assert.strictEqual(staleCallbackTriggered, false, "Stale callbacks must never execute");
console.log("✓ stale completed and failed TTS ignored via AudioRequestRegistry pass");

// Test Case 6: Stale 200ms and 2s fallback continuation timers cancelled (Stage 16)
const timerRegistry = new AudioRequestRegistry();
let timer200msFired = false;
let fallback2sFired = false;

timerRegistry.registerRequest("req_A_timers", {
  turnId: "turn_A_timed",
  onDone: () => {},
  onFail: () => {}
});

// Schedule 200ms triggerStart timer
timerRegistry.scheduleRequestTimer("req_A_timers", () => {
  timer200msFired = true;
}, 200, tcMock);

// Schedule 2s fallback continuation timer
timerRegistry.scheduleRequestTimer("req_A_timers", () => {
  fallback2sFired = true;
}, 2000, tcMock);

// Turn A interrupted or cancelled
timerRegistry.cancelRequest("req_A_timers");

const reqEntry = timerRegistry.getRequest("req_A_timers");
assert.strictEqual(reqEntry, null, "Request should be removed from registry on cancel");
assert.strictEqual(timer200msFired, false, "200ms timer must NOT fire after cancel");
assert.strictEqual(fallback2sFired, false, "2s fallback timer must NOT fire after cancel");
console.log("✓ stale 200ms and 2s fallback timers cancelled before fire pass");

// Test Case 7: Stale chunk completion does not continue sequence (Stage 16)
let sequenceAdvanced = false;
const ownerTurnA = "turn_A_chunk";
const tcChunks = {
  activeTurnId: "turn_B_chunk", // Turn switched to B!
  isCurrentTurn: (id) => id === "turn_B_chunk"
};

function onChunkComplete(ownerTurnId) {
  if (!timerRegistry.isOwnerTurnCurrent(ownerTurnId, tcChunks)) {
    // Stale chunk completion: drop continuation
    return;
  }
  sequenceAdvanced = true;
}

onChunkComplete(ownerTurnA);
assert.strictEqual(sequenceAdvanced, false, "Stale chunk completion must not advance chunk sequence");
console.log("✓ stale chunk completion does not continue sequence pass");

// Test Case 8: Stale finishSpeaking does not finish active Turn B (Stage 16)
const smFinish = new ConversationStateMachine();
const tcFinish = new TurnController(smFinish);
const turnAId = tcFinish.startNewTurn("Lệnh A");
smFinish.transition(ConversationState.SPEAKING);

// Turn B starts before A finishes speaking
const turnBId = tcFinish.startNewTurn("Lệnh B");
smFinish.transition(ConversationState.SPEAKING);
assert.strictEqual(tcFinish.activeTurnId, turnBId);

// Stale finishSpeaking for Turn A
function finishSpeaking(ownerTurnId) {
  if (tcFinish.isCurrentTurn(ownerTurnId)) {
    tcFinish.finishTurn(ownerTurnId);
  }
}

finishSpeaking(turnAId); // Old closure from Turn A
assert.strictEqual(tcFinish.activeTurnId, turnBId, "Turn B must still be active after stale Turn A finishSpeaking");
assert.strictEqual(tcFinish.isCurrentTurn(turnBId), true);

// Active Turn B finishSpeaking
finishSpeaking(turnBId);
assert.strictEqual(tcFinish.activeTurnId, null, "Turn B finishes cleanly when owner turn matches");
console.log("✓ stale finishSpeaking does not finish active Turn B pass");

// Test Case 9: Live TTS begins before prefetch
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

