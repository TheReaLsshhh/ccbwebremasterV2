(function () {
  "use strict";

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  // CSS cover + scale uses the same percentage for position and transform origin.
  function dragPosition(start, delta, viewport, rendered) {
    var overflow = rendered - viewport;
    return overflow > 0.5 ? clamp(start - delta * 100 / overflow, 0, 100) : start;
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { dragPosition: dragPosition };
  }
  if (typeof document === "undefined") return;

  function ready() {
    var fileInput = document.getElementById("id_banner_image");
    if (!fileInput) return;
    var clearInput = document.getElementById("banner_image-clear_id");
    var titleInput = document.getElementById("id_hero_title");
    var textInput = document.getElementById("id_hero_text");
    var originalUrl = fileInput.dataset.currentImage || "";
    var objectUrl = "";
    var panels = [];

    [
      { prefix: "banner", selector: ".banner-crop-desktop", width: 1440, height: 400, label: "Desktop" },
      { prefix: "banner_mobile", selector: ".banner-crop-mobile", width: 390, height: 280, label: "Mobile" }
    ].forEach(function (config) {
      var fieldset = document.querySelector(config.selector);
      if (!fieldset) return;
      var inputs = {};
      var ranges = {};
      ["position_x", "position_y", "zoom", "height"].forEach(function (name) {
        var input = document.getElementById("id_" + config.prefix + "_" + name);
        inputs[name] = input;
        var slider = document.createElement("input");
        slider.type = "range";
        slider.min = input.min;
        slider.max = input.max;
        slider.step = input.step;
        slider.value = input.value;
        slider.className = "banner-crop-slider";
        slider.setAttribute("aria-label", config.label + " " + name.replaceAll("_", " "));
        input.insertAdjacentElement("afterend", slider);
        ranges[name] = slider;
        slider.addEventListener("input", function () {
          input.value = slider.value;
          render();
        });
        input.addEventListener("input", render);
        input.addEventListener("change", function () {
          if (input.value && input.validity.valid) render();
        });
      });

      var panel = document.createElement("div");
      panel.className = "banner-crop-preview";
      panel.innerHTML = '<div class="banner-crop-stage" aria-label="' + config.label + ' banner preview">' +
        '<img class="banner-crop-image" alt="Banner crop preview" draggable="false">' +
        '<div class="banner-crop-shade"></div>' +
        '<div class="banner-crop-copy"><span>City College of Bayawan</span><strong></strong><p></p></div>' +
        '</div><p class="banner-crop-status" role="status"></p>' +
        '<button type="button" class="button">Reset ' + config.label.toLowerCase() + ' crop</button>';
      var description = fieldset.querySelector(".description") || fieldset.querySelector("h2");
      if (description) description.insertAdjacentElement("afterend", panel);
      else fieldset.prepend(panel);
      var stage = panel.querySelector(".banner-crop-stage");
      var image = panel.querySelector(".banner-crop-image");
      var status = panel.querySelector(".banner-crop-status");
      var drag = null;

      function value(name, fallback) {
        var number = Number(inputs[name].value);
        return inputs[name].value && Number.isFinite(number)
          ? clamp(number, Number(inputs[name].min), Number(inputs[name].max)) : fallback;
      }
      function render() {
        var x = value("position_x", 50), y = value("position_y", 50);
        var zoom = value("zoom", 1), height = value("height", config.height);
        stage.style.aspectRatio = config.width + " / " + height;
        stage.style.maxWidth = config.width + "px";
        image.style.objectPosition = x + "% " + y + "%";
        image.style.transformOrigin = x + "% " + y + "%";
        image.style.transform = "scale(" + zoom + ")";
        // Scale the sample title as the desktop preview shrinks to fit the editor.
        stage.style.setProperty("--preview-scale", Math.min(1, stage.clientWidth / config.width));
        stage.querySelector("strong").textContent = titleInput ? titleInput.value : "Page title";
        stage.querySelector("p").textContent = textInput ? textInput.value : "";
        Object.keys(ranges).forEach(function (name) { ranges[name].value = inputs[name].value; });
      }
      function reset() {
        inputs.position_x.value = "50";
        inputs.position_y.value = "50";
        inputs.zoom.value = "1";
        inputs.height.value = String(config.height);
        render();
      }
      function load(url, resetPosition) {
        if (resetPosition) reset();
        stage.hidden = true;
        if (!url) {
          image.removeAttribute("src");
          status.textContent = "Upload a banner image to preview the crop.";
          return;
        }
        status.textContent = "Loading banner preview…";
        image.src = url;
      }
      image.addEventListener("load", function () {
        stage.hidden = false;
        status.textContent = "Drag the image or use the sliders. Changes apply when you save the page.";
        render();
      });
      image.addEventListener("error", function () {
        stage.hidden = true;
        status.textContent = "This image could not be previewed. Choose a valid image or check its existing upload.";
      });
      panel.querySelector("button").addEventListener("click", reset);
      stage.addEventListener("pointerdown", function (event) {
        if (event.button !== 0 || !image.naturalWidth) return;
        var box = stage.getBoundingClientRect();
        var scale = Math.max(box.width / image.naturalWidth, box.height / image.naturalHeight) * value("zoom", 1);
        drag = { x: event.clientX, y: event.clientY, px: value("position_x", 50), py: value("position_y", 50), width: box.width, height: box.height, imageWidth: image.naturalWidth * scale, imageHeight: image.naturalHeight * scale };
        stage.setPointerCapture(event.pointerId);
        stage.classList.add("is-dragging");
        event.preventDefault();
      });
      stage.addEventListener("pointermove", function (event) {
        if (!drag) return;
        inputs.position_x.value = String(Math.round(dragPosition(drag.px, event.clientX - drag.x, drag.width, drag.imageWidth)));
        inputs.position_y.value = String(Math.round(dragPosition(drag.py, event.clientY - drag.y, drag.height, drag.imageHeight)));
        render();
      });
      function endDrag() { drag = null; stage.classList.remove("is-dragging"); }
      stage.addEventListener("pointerup", endDrag);
      stage.addEventListener("pointercancel", endDrag);
      stage.addEventListener("lostpointercapture", endDrag);
      if (window.ResizeObserver) new ResizeObserver(render).observe(stage);
      else window.addEventListener("resize", render);
      if (titleInput) titleInput.addEventListener("input", render);
      if (textInput) textInput.addEventListener("input", render);
      panels.push({ load: load });
    });

    function updateImage(resetPosition) {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = "";
      var file = fileInput.files && fileInput.files[0];
      if (file) objectUrl = URL.createObjectURL(file);
      var url = clearInput && clearInput.checked ? "" : objectUrl || originalUrl;
      panels.forEach(function (panel) { panel.load(url, resetPosition); });
    }
    fileInput.addEventListener("change", function () {
      if (clearInput && fileInput.files.length) clearInput.checked = false;
      updateImage(Boolean(fileInput.files.length));
    });
    if (clearInput) clearInput.addEventListener("change", function () { updateImage(false); });
    window.addEventListener("pagehide", function () { if (objectUrl) URL.revokeObjectURL(objectUrl); });
    updateImage(false);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready);
  else ready();
})();
