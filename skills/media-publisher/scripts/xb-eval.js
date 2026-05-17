/**
 * Helper: Run JS in browser via xbrowser eval (base64 encoded)
 * 
 * Solves the problem of complex JS being corrupted by shell escaping.
 * Writes JS to temp file, base64 encodes it, then runs via xbrowser eval.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const XB_PATH = 'D:\\wujm\\QClaw\\resources\\openclaw\\config\\skills\\xbrowser\\scripts\\xb.cjs';
const BROWSER = 'cft'; // or 'chrome' for RedBookSkills

/**
 * Execute JavaScript in the browser via xbrowser eval
 * @param {string} jsCode - The JavaScript code to execute
 * @param {object} options - Options
 * @param {string} [options.browser] - Browser ID (default: cft)
 * @param {number} [options.timeout] - Timeout in ms (default: 15000)
 * @returns {string} JSON result from xbrowser
 */
function runEval(jsCode, options = {}) {
  const browser = options.browser || BROWSER;
  const timeout = options.timeout || 15000;
  
  const b64 = Buffer.from(jsCode).toString('base64');
  const evalCmd = `var _fx=new Uint8Array(atob("${b64}").split("").map(function(c){return c.charCodeAt(0)}));var _fy=new TextDecoder("utf-8").decode(_fx);eval(_fy)`;
  
  const result = execSync(
    `node "${XB_PATH}" run --browser ${browser} eval ${JSON.stringify(evalCmd)}`,
    { encoding: 'utf8', timeout }
  );
  return result;
}

/**
 * Convenience: inject bridge for Wujie iframe file upload
 */
function injectBridge(browser) {
  const { BRIDGE_JS } = require('./wujie-bridge.js');
  return runEval(BRIDGE_JS, { browser });
}

/**
 * Convenience: fill description in Wujie iframe
 */
function fillDescription(text, browser) {
  const { FILL_DESC_JS } = require('./wujie-bridge.js');
  return runEval(FILL_DESC_JS(text), { browser });
}

/**
 * Convenience: click publish button in Wujie iframe
 */
function clickPublish(browser) {
  const { CLICK_PUBLISH_JS } = require('./wujie-bridge.js');
  return runEval(CLICK_PUBLISH_JS, { browser });
}

module.exports = { runEval, injectBridge, fillDescription, clickPublish };

// CLI mode
if (require.main === module) {
  const args = process.argv.slice(2);
  if (args[0] === 'injectBridge') {
    console.log(injectBridge(args[1]));
  } else if (args[0] === 'fillDesc') {
    console.log(fillDescription(args.slice(1).join(' '), args[args.length - 1]));
  } else if (args[0] === 'clickPublish') {
    console.log(clickPublish(args[1]));
  } else if (args[0] === 'eval') {
    // Read JS from stdin or file
    let js = '';
    if (args[1] && fs.existsSync(args[1])) {
      js = fs.readFileSync(args[1], 'utf8');
    } else {
      js = args.slice(1).join(' ');
    }
    console.log(runEval(js));
  } else {
    console.log('Usage: node xb-eval.js <command> [args...]');
    console.log('Commands: injectBridge, fillDesc <text>, clickPublish, eval <js_or_file>');
  }
}
