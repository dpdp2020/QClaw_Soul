/**
 * Bridge Upload for Wujie Micro-Frontend (视频号)
 * 
 * Creates a bridge <input type="file"> in the main document that forwards
 * files to the Ant Design Upload component inside the Wujie iframe.
 * 
 * Usage:
 *   1. Run this script via xbrowser eval to inject the bridge
 *   2. Use xbrowser upload to upload file to #__bridge_input__
 *   3. The change event automatically forwards the file to the iframe
 */

const BRIDGE_JS = `
var iframe = document.querySelector('iframe');
if (!iframe) { 'ERROR: no iframe found'; }
var bridge = document.createElement('input');
bridge.type = 'file';
bridge.id = '__bridge_input__';
bridge.style.cssText = 'position:fixed;top:-999px';
bridge.addEventListener('change', function() {
  try {
    var idoc = iframe.contentDocument;
    var iinp = idoc.querySelector('input[type=file]');
    if (iinp && bridge.files.length > 0) {
      var dt = new DataTransfer();
      for (var i = 0; i < bridge.files.length; i++) dt.items.add(bridge.files[i]);
      iinp.files = dt.files;
      var wrapper = iinp.closest('.ant-upload') || iinp.parentElement;
      if (wrapper) wrapper.dispatchEvent(new Event('change', {bubbles: true}));
      iinp.dispatchEvent(new Event('change', {bubbles: true}));
      'bridge forwarded ' + bridge.files.length + ' file(s)';
    }
  } catch(e) { 'bridge error: ' + e.message; }
});
document.body.appendChild(bridge);
'bridge ready, hasIframeAccess: ' + !!iframe.contentDocument;
`;

/**
 * Fill description in Wujie iframe using execCommand (triggers Vue reactivity)
 */
const FILL_DESC_JS = (text) => `
var iframe = document.querySelector('iframe');
var doc = iframe.contentDocument;
var descEl = doc.querySelector('.input-editor') || doc.querySelector('[contenteditable="true"]');
if (descEl) {
  descEl.focus();
  doc.execCommand('selectAll', false, null);
  doc.execCommand('insertText', false, ${JSON.stringify(text)});
  descEl.dispatchEvent(new Event('input', {bubbles: true}));
  descEl.dispatchEvent(new Event('change', {bubbles: true}));
  'OK filled, length: ' + (descEl.innerText || '').length;
} else { 'ERROR: desc element not found'; }
`;

/**
 * Click publish button inside Wujie iframe
 */
const CLICK_PUBLISH_JS = `
var iframe = document.querySelector('iframe');
var doc = iframe.contentDocument;
var btns = doc.querySelectorAll('button');
for (var i = 0; i < btns.length; i++) {
  if (btns[i].textContent.trim() === '\u53d1\u8868' || btns[i].textContent.indexOf('\u76f4\u63a5\u53d1\u8868') >= 0) {
    btns[i].click(); 'clicked \u53d1\u8868'; break;
  }
}
'not found';
`;

module.exports = { BRIDGE_JS, FILL_DESC_JS, CLICK_PUBLISH_JS };
