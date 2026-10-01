const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

console.log('Running test_index_syntax.js...');

const wwwDir = path.resolve(__dirname, '../www');
const indexPath = path.join(wwwDir, 'index.html');

assert(fs.existsSync(indexPath), `index.html must exist at ${indexPath}`);
const htmlContent = fs.readFileSync(indexPath, 'utf-8');

// 1. Check referenced external script files exist
const srcRegex = /<script\s+[^>]*src=["']([^"']+)["'][^>]*>/gi;
let match;
const externalScripts = [];
while ((match = srcRegex.exec(htmlContent)) !== null) {
  const src = match[1];
  if (!src.startsWith('http://') && !src.startsWith('https://')) {
    externalScripts.push(src);
  } else {
    console.warn(`[WARN] Remote script tag found: ${src}`);
  }
}

for (const src of externalScripts) {
  const scriptPath = path.join(wwwDir, src);
  assert(fs.existsSync(scriptPath), `Referenced script file does not exist: ${src} (checked ${scriptPath})`);
  const code = fs.readFileSync(scriptPath, 'utf-8');
  try {
    new vm.Script(code, { filename: src });
  } catch (err) {
    assert.fail(`Syntax error in referenced script ${src}: ${err.message}`);
  }
}
console.log(`✓ All ${externalScripts.length} referenced local scripts exist and parse without syntax errors.`);

// 2. Extract and parse all inline script tags
const inlineScriptRegex = /<script(?![^>]*src=)[^>]*>([\s\S]*?)<\/script>/gi;
let inlineCount = 0;
while ((match = inlineScriptRegex.exec(htmlContent)) !== null) {
  const inlineCode = match[1].trim();
  if (inlineCode) {
    inlineCount++;
    try {
      new vm.Script(inlineCode, { filename: `inline-script-${inlineCount}.js` });
    } catch (err) {
      assert.fail(`Syntax error in inline script #${inlineCount}: ${err.message}`);
    }
  }
}
assert(inlineCount > 0, 'At least one inline script must be present in index.html');
console.log(`✓ All ${inlineCount} inline script blocks parse without syntax errors.`);

// 3. Smoke Test: Mock browser environment and evaluate core runtime initialization
const sandbox = {
  console: {
    log: () => {},
    warn: () => {},
    error: () => {},
    info: () => {}
  },
  window: {},
  document: {
    getElementById: (id) => ({
      addEventListener: () => {},
      classList: { add: () => {}, remove: () => {}, toggle: () => {}, contains: () => false },
      style: {},
      setAttribute: () => {},
      removeAttribute: () => {},
      innerText: '',
      innerHTML: '',
      value: ''
    }),
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: () => {}
  },
  localStorage: {
    _data: {},
    getItem(k) { return this._data[k] || null; },
    setItem(k, v) { this._data[k] = String(v); },
    removeItem(k) { delete this._data[k]; },
    clear() { this._data = {}; }
  },
  navigator: {
    userAgent: 'NodeSmokeTest',
    mediaDevices: { getUserMedia: async () => ({}) }
  },
  location: { reload: () => {} },
  setTimeout: setTimeout,
  clearTimeout: clearTimeout,
  setInterval: setInterval,
  clearInterval: clearInterval,
  Audio: class {
    constructor() { this.play = async () => {}; this.pause = () => {}; }
  }
};
sandbox.window = sandbox;

const context = vm.createContext(sandbox);

// Execute referenced modules first
for (const src of externalScripts) {
  if (src.endsWith('.cdn.js') || src.endsWith('.min.js')) continue;
  const scriptPath = path.join(wwwDir, src);
  const code = fs.readFileSync(scriptPath, 'utf-8');
  vm.runInContext(code, context);
}

assert(sandbox.window.ReminderDeliveryPolicy || sandbox.ReminderDeliveryPolicy, 'ReminderDeliveryPolicy must be defined');
assert(sandbox.window.AudioRequestRegistry || sandbox.AudioRequestRegistry, 'AudioRequestRegistry must be defined');
console.log('✓ Runtime initialization smoke test passed.');
console.log('ALL INDEX SYNTAX AND SMOKE TESTS PASSED PERFECTLY!');
