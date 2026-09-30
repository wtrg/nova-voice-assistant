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

console.log("ALL TURN STATE MACHINE TESTS PASSED PERFECTLY!");
