(function () {
  "use strict";

  var OUTPUT_SIZE = 900;
  var MAX_ZOOM = 3;

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function ready(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback);
    } else {
      callback();
    }
  }

  ready(function () {
    var input = document.getElementById("id_profile_image");
    var hidden = document.getElementById("id_profile_image_cropped_data");
    var form = input ? input.closest("form") : null;

    if (!input || !hidden || !form) {
      return;
    }

    var image = new Image();
    var objectUrl = "";
    var stageSize = 320;
    var fitScale = 1;
    var zoom = 1;
    var offsetX = 0;
    var offsetY = 0;
    var isDragging = false;
    var startX = 0;
    var startY = 0;
    var startOffsetX = 0;
    var startOffsetY = 0;

    var panel = document.createElement("div");
    panel.className = "faculty-image-crop is-hidden";
    panel.innerHTML = [
      '<div class="faculty-image-crop__header">',
      "  <strong>Crop profile image</strong>",
      "  <span>Drag to position. Use zoom for a tighter crop.</span>",
      "</div>",
      '<div class="faculty-image-crop__stage" role="application" aria-label="Profile image crop area">',
      '  <img class="faculty-image-crop__image" alt="">',
      '  <div class="faculty-image-crop__frame" aria-hidden="true"></div>',
      "</div>",
      '<div class="faculty-image-crop__controls">',
      '  <label for="faculty-image-crop-zoom">Zoom</label>',
      '  <input id="faculty-image-crop-zoom" type="range" min="1" max="' + MAX_ZOOM + '" step="0.01" value="1">',
      '  <button type="button" class="button faculty-image-crop__reset">Reset</button>',
      '  <button type="button" class="button faculty-image-crop__apply">Apply crop</button>',
      "</div>",
      '<canvas class="faculty-image-crop__preview" width="96" height="96" aria-label="Applied crop preview"></canvas>',
    ].join("");

    var row = input.closest(".form-row") || input.parentNode;
    row.insertAdjacentElement("afterend", panel);

    var stage = panel.querySelector(".faculty-image-crop__stage");
    var previewImage = panel.querySelector(".faculty-image-crop__image");
    var zoomInput = panel.querySelector("#faculty-image-crop-zoom");
    var resetButton = panel.querySelector(".faculty-image-crop__reset");
    var applyButton = panel.querySelector(".faculty-image-crop__apply");
    var previewCanvas = panel.querySelector(".faculty-image-crop__preview");

    function setStageSize() {
      stageSize = stage.clientWidth || 320;
    }

    function limitOffsets() {
      var renderedWidth = image.naturalWidth * fitScale * zoom;
      var renderedHeight = image.naturalHeight * fitScale * zoom;
      var maxOffsetX = Math.max(0, (renderedWidth - stageSize) / 2);
      var maxOffsetY = Math.max(0, (renderedHeight - stageSize) / 2);
      offsetX = clamp(offsetX, -maxOffsetX, maxOffsetX);
      offsetY = clamp(offsetY, -maxOffsetY, maxOffsetY);
    }

    function renderCropView() {
      limitOffsets();
      previewImage.style.width = image.naturalWidth * fitScale + "px";
      previewImage.style.height = image.naturalHeight * fitScale + "px";
      previewImage.style.transform = "translate(-50%, -50%) translate(" + offsetX + "px, " + offsetY + "px) scale(" + zoom + ")";
    }

    function drawCrop(targetCanvas) {
      var canvas = targetCanvas || document.createElement("canvas");
      var context = canvas.getContext("2d");
      var scaleOnStage = fitScale * zoom;
      var renderedWidth = image.naturalWidth * scaleOnStage;
      var renderedHeight = image.naturalHeight * scaleOnStage;
      var imageLeft = stageSize / 2 + offsetX - renderedWidth / 2;
      var imageTop = stageSize / 2 + offsetY - renderedHeight / 2;
      var sourceX = (0 - imageLeft) / scaleOnStage;
      var sourceY = (0 - imageTop) / scaleOnStage;
      var sourceSize = stageSize / scaleOnStage;

      canvas.width = canvas.width || OUTPUT_SIZE;
      canvas.height = canvas.height || OUTPUT_SIZE;
      context.fillStyle = "#fff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(
        image,
        sourceX,
        sourceY,
        sourceSize,
        sourceSize,
        0,
        0,
        canvas.width,
        canvas.height
      );

      return canvas;
    }

    function applyCrop() {
      if (!image.naturalWidth) {
        return;
      }

      var outputCanvas = document.createElement("canvas");
      outputCanvas.width = OUTPUT_SIZE;
      outputCanvas.height = OUTPUT_SIZE;
      hidden.value = drawCrop(outputCanvas).toDataURL("image/jpeg", 0.9);

      previewCanvas.classList.add("is-visible");
      drawCrop(previewCanvas);
    }

    function resetCrop() {
      setStageSize();
      fitScale = Math.max(stageSize / image.naturalWidth, stageSize / image.naturalHeight);
      zoom = 1;
      offsetX = 0;
      offsetY = 0;
      zoomInput.value = "1";
      renderCropView();
      applyCrop();
    }

    function pointerPosition(event) {
      if (event.touches && event.touches.length) {
        return { x: event.touches[0].clientX, y: event.touches[0].clientY };
      }
      return { x: event.clientX, y: event.clientY };
    }

    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      hidden.value = "";
      previewCanvas.classList.remove("is-visible");

      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
        objectUrl = "";
      }

      if (!file || !file.type.match(/^image\//)) {
        panel.classList.add("is-hidden");
        return;
      }

      objectUrl = URL.createObjectURL(file);
      image = new Image();
      image.onload = function () {
        previewImage.src = objectUrl;
        panel.classList.remove("is-hidden");
        resetCrop();
      };
      image.src = objectUrl;
    });

    stage.addEventListener("mousedown", function (event) {
      if (!image.naturalWidth) {
        return;
      }

      isDragging = true;
      var position = pointerPosition(event);
      startX = position.x;
      startY = position.y;
      startOffsetX = offsetX;
      startOffsetY = offsetY;
      stage.classList.add("is-dragging");
      event.preventDefault();
    });

    document.addEventListener("mousemove", function (event) {
      if (!isDragging) {
        return;
      }

      var position = pointerPosition(event);
      offsetX = startOffsetX + position.x - startX;
      offsetY = startOffsetY + position.y - startY;
      renderCropView();
      hidden.value = "";
    });

    document.addEventListener("mouseup", function () {
      if (!isDragging) {
        return;
      }

      isDragging = false;
      stage.classList.remove("is-dragging");
      applyCrop();
    });

    stage.addEventListener("touchstart", function (event) {
      if (!image.naturalWidth) {
        return;
      }

      isDragging = true;
      var position = pointerPosition(event);
      startX = position.x;
      startY = position.y;
      startOffsetX = offsetX;
      startOffsetY = offsetY;
      stage.classList.add("is-dragging");
    }, { passive: true });

    document.addEventListener("touchmove", function (event) {
      if (!isDragging) {
        return;
      }

      var position = pointerPosition(event);
      offsetX = startOffsetX + position.x - startX;
      offsetY = startOffsetY + position.y - startY;
      renderCropView();
      hidden.value = "";
    }, { passive: true });

    document.addEventListener("touchend", function () {
      if (!isDragging) {
        return;
      }

      isDragging = false;
      stage.classList.remove("is-dragging");
      applyCrop();
    });

    zoomInput.addEventListener("input", function () {
      zoom = Number(zoomInput.value) || 1;
      renderCropView();
      hidden.value = "";
    });

    zoomInput.addEventListener("change", applyCrop);
    resetButton.addEventListener("click", resetCrop);
    applyButton.addEventListener("click", applyCrop);

    form.addEventListener("submit", function () {
      if (input.files && input.files[0] && !hidden.value) {
        applyCrop();
      }
    });

    window.addEventListener("resize", function () {
      if (!panel.classList.contains("is-hidden") && image.naturalWidth) {
        resetCrop();
      }
    });
  });
})();
