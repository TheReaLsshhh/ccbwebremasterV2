const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/college-motion.js', 'utf8');

function browser({ legacy = false, reduced = false, mobile = false, broken = -1 } = {}) {
    const timers = new Map();
    const events = {};
    let serial = 0;
    const slides = [0, 1, 2].map((index) => ({
        complete: true, naturalWidth: index === broken ? 0 : 1600,
        classList: { active: index === 0, add() { this.active = true; }, remove() { this.active = false; } },
        addEventListener() {},
    }));
    const hero = { querySelectorAll: () => slides, style: { setProperty() {} }, getBoundingClientRect: () => ({ top: 0, bottom: 600 }) };
    const document = {
        hidden: false, querySelector: () => hero, querySelectorAll: () => [hero],
        addEventListener(name, callback) { events[name] = callback; },
    };
    const window = {
        innerHeight: 900,
        matchMedia(query) {
            const media = { matches: query.includes('reduced') ? reduced : mobile };
            media[legacy ? 'addListener' : 'addEventListener'] = () => {};
            return media;
        },
        addEventListener(name, callback) { events[name] = callback; },
        requestAnimationFrame(callback) { callback(); return 1; },
        setTimeout(callback, delay) { const id = ++serial; timers.set(id, { callback, delay }); return id; },
        clearTimeout(id) { timers.delete(id); },
    };
    vm.runInNewContext(source, { window, document });
    return {
        slides, timers, events, document,
        active: () => slides.findIndex(slide => slide.classList.active),
        advance() {
            assert.equal(timers.size, 1);
            const [id, timer] = timers.entries().next().value;
            assert.equal(timer.delay, 8000);
            timers.delete(id);
            timer.callback();
        },
    };
}

for (const [name, options] of [
    ['desktop', {}], ['legacy Safari on iOS/tablets', { legacy: true, mobile: true }],
    ['reduced-motion devices', { legacy: true, reduced: true, mobile: true }],
]) {
    test(`slideshow cycles every eight seconds on ${name}`, () => {
        const page = browser(options);
        for (const expected of [1, 2, 0]) { page.advance(); assert.equal(page.active(), expected); }
    });
}

test('a broken image is skipped without stopping the slideshow', () => {
    const page = browser({ broken: 1 });
    page.advance(); assert.equal(page.active(), 2);
    page.advance(); assert.equal(page.active(), 0);
});

test('a failed first image is replaced by a loaded image', () => {
    const page = browser({ broken: 0 });
    assert.equal(page.active(), 1);
    page.advance(); assert.equal(page.active(), 2);
});

test('hidden tabs pause and resume with one timer', () => {
    const page = browser();
    page.document.hidden = true; page.events.visibilitychange();
    assert.equal(page.timers.size, 0);
    page.document.hidden = false; page.events.visibilitychange();
    page.advance(); assert.equal(page.active(), 1);
});

test('Safari back-forward page restoration resumes playback', () => {
    const page = browser({ legacy: true });
    page.events.pagehide(); assert.equal(page.timers.size, 0);
    page.events.pageshow(); page.advance(); assert.equal(page.active(), 1);
});
