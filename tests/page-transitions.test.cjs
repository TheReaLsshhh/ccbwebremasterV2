const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('static/js/page-transitions.js', 'utf8');
function setup(reduced = false) {
    const listeners = {}, observers = [], animations = [];
    const preference = { matches: reduced, addEventListener(_, fn) { this.change = fn; } };
    let focused = false;
    const node = { parentElement: { closest() { return null; } }, contains() { return focused; },
        animate(frames, options) {
            const animation = { frames, options, effect: { target: node }, cancelled: false,
                cancel() { this.cancelled = true; if (this.oncancel) this.oncancel(); } };
            animations.push(animation); return animation;
        } };
    const document = { activeElement: {}, querySelectorAll() { return [node]; }, addEventListener(name, fn) { listeners[name] = fn; } };
    class Observer {
        constructor(callback) { this.callback = callback; this.nodes = new Set(); observers.push(this); }
        observe(node) { this.nodes.add(node); }
        unobserve(node) { this.nodes.delete(node); }
        disconnect() { this.nodes.clear(); }
    }
    const window = { IntersectionObserver: Observer, matchMedia() { return preference; }, addEventListener(name, fn) { listeners[name] = fn; } };
    vm.runInNewContext(script, { window, document, IntersectionObserver: Observer, Element: { prototype: { animate() {} } } });
    return { observers, node, animations, preference, listeners, focus() { focused = true; } };
}
test('animates each visible item once without waiting for navigation', () => {
    const s = setup(), callback = s.observers[0].callback;
    callback([{ target: s.node, isIntersecting: false }]);
    assert.equal(s.animations.length, 0);
    callback([{ target: s.node, isIntersecting: true }]);
    callback([{ target: s.node, isIntersecting: true }]);
    assert.equal(s.animations.length, 1);
    assert.equal(s.animations[0].frames[1].opacity, 1);
});
test('reduced motion skips animation and cancels animation when enabled live', () => {
    assert.equal(setup(true).observers.length, 0);
    const s = setup();
    s.observers[0].callback([{ target: s.node, isIntersecting: true }]);
    s.preference.matches = true;
    s.preference.change();
    assert.equal(s.animations[0].cancelled, true);
    assert.equal(s.observers[0].nodes.size, 0);
});
test('keyboard interaction is never animated away', () => {
    const s = setup(); s.focus();
    s.observers[0].callback([{ target: s.node, isIntersecting: true }]);
    assert.equal(s.animations.length, 0);
});
test('leaving the page cancels active motion and ignores queued entries', () => {
    const s = setup();
    s.observers[0].callback([{ target: s.node, isIntersecting: true }]);
    s.listeners.pagehide();
    s.observers[0].callback([{ target: s.node, isIntersecting: true }]);
    assert.equal(s.animations[0].cancelled, true);
});
