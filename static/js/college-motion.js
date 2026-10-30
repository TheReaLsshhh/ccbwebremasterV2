(() => {
    "use strict";

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const smallScreen = window.matchMedia("(max-width: 767px)");
    const hero = document.querySelector("[data-hero-slideshow]");
    const banners = [...document.querySelectorAll(".college-home-hero, .college-page-hero")];
    let frame = null;

    function paintParallax() {
        frame = null;
        banners.forEach((banner) => {
            const rect = banner.getBoundingClientRect();
            const enabled = !reducedMotion.matches && !smallScreen.matches;
            const offset = enabled ? Math.max(-55, Math.min(55, -rect.top * 0.14)) : 0;
            if (rect.bottom >= -130 && rect.top <= window.innerHeight + 130 || !enabled) {
                banner.style.setProperty("--parallax-y", `${offset.toFixed(1)}px`);
            }
        });
    }

    function scheduleParallax() {
        if (frame === null) frame = window.requestAnimationFrame(paintParallax);
    }

    window.addEventListener("scroll", scheduleParallax, { passive: true });
    window.addEventListener("resize", scheduleParallax, { passive: true });
    reducedMotion.addEventListener("change", scheduleParallax);
    smallScreen.addEventListener("change", scheduleParallax);
    paintParallax();

    if (!hero) return;
    const slides = [...hero.querySelectorAll(".hero-slide")];
    const controls = hero.querySelector(".hero-slideshow-controls");
    const pauseButton = hero.querySelector("[data-slide-pause]");
    const count = hero.querySelector("[data-slide-count]");
    let active = 0;
    let userPaused = false;
    let pointerInside = false;
    let inView = true;
    let timer = null;

    const available = () => slides.filter((slide) => slide.complete && slide.naturalWidth > 0);

    function sync() {
        window.clearTimeout(timer);
        timer = null;
        const ready = available();
        controls.hidden = ready.length < 2;
        const paused = userPaused || reducedMotion.matches;
        pauseButton.textContent = paused ? "Play slideshow" : "Pause slideshow";
        pauseButton.setAttribute("aria-pressed", String(paused));
        pauseButton.disabled = reducedMotion.matches;
        pauseButton.title = reducedMotion.matches ? "Automatic playback is disabled by your reduced-motion preference" : "";
        count.textContent = `${Math.max(1, ready.indexOf(slides[active]) + 1)} / ${ready.length}`;
        if (ready.length > 1 && !paused && !pointerInside && !hero.contains(document.activeElement) && !document.hidden && inView) {
            timer = window.setTimeout(() => changeSlide(1), 6000);
        }
    }

    function changeSlide(direction) {
        const ready = available();
        if (!ready.length) return;
        const index = ready.indexOf(slides[active]);
        const next = ready[(index + direction + ready.length) % ready.length];
        slides[active].classList.remove("is-active");
        active = slides.indexOf(next);
        next.classList.add("is-active");
        sync();
    }

    function imageSettled() {
        if (!slides[active].naturalWidth && available().length) changeSlide(1);
        else sync();
    }

    slides.forEach((slide) => {
        slide.addEventListener("load", imageSettled);
        slide.addEventListener("error", imageSettled);
    });
    hero.querySelector("[data-slide-previous]").addEventListener("click", () => changeSlide(-1));
    hero.querySelector("[data-slide-next]").addEventListener("click", () => changeSlide(1));
    pauseButton.addEventListener("click", () => { userPaused = !userPaused; sync(); });
    hero.addEventListener("pointerenter", (event) => {
        if (event.pointerType !== "touch") { pointerInside = true; sync(); }
    });
    hero.addEventListener("pointerleave", () => { pointerInside = false; sync(); });
    hero.addEventListener("focusin", sync);
    hero.addEventListener("focusout", () => window.setTimeout(sync, 0));
    document.addEventListener("visibilitychange", sync);
    reducedMotion.addEventListener("change", sync);
    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver(([entry]) => { inView = entry.isIntersecting; sync(); });
        observer.observe(hero);
    }
    imageSettled();
})();
