const test = require('node:test');
const assert = require('node:assert/strict');
const { dragPosition } = require('../static/admin/js/banner-image-crop.js');

test('drag follows the pointer and stays inside the image', () => {
  assert.equal(dragPosition(50, 100, 400, 800), 25);
  assert.equal(dragPosition(50, -100, 400, 800), 75);
  assert.equal(dragPosition(50, 1000, 400, 800), 0);
  assert.equal(dragPosition(50, -1000, 400, 800), 100);
});
test('an axis without overflow cannot reveal an empty edge', () => {
  assert.equal(dragPosition(50, 100, 400, 400), 50);
  assert.equal(dragPosition(25, -100, 400, 400.1), 25);
});
test('crop position keeps the rendered image covering the preview', () => {
  for (const viewport of [390, 960, 1440]) {
    for (const zoom of [1.1, 1.5, 3]) {
      const rendered = viewport * zoom;
      for (const delta of [-2000, -20, 0, 20, 2000]) {
        const position = dragPosition(50, delta, viewport, rendered);
        const left = (viewport - rendered) * position / 100;
        assert.ok(left <= 0);
        assert.ok(left + rendered >= viewport - 1e-9);
      }
    }
  }
});
