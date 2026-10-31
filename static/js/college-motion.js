(() => {
    "use strict";

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const smallScreen = window.matchMedia("(max-width: 767px)");
    const hero = document.querySelector("[data-hero-slideshow]");
    const banners = [...document.querySelectorAll(".college-home-hero, .college-page-hero")];
    let frame = null;

    // Safari before 14 exposes addListener rather than addEventListener.
    function watchMedia(query, callback) {
        if (typeof query.addEventListener === "function") query.addEventListener("change", callback);
        else if (typeof query.addListener === "function") query.addListener(callback);
    }

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
    watchMedia(reducedMotion, scheduleParallax);
    watchMedia(smallScreen, scheduleParallax);
    paintParallax();

    if (!hero) return;
    const slides = [...hero.querySelectorAll(".hero-slide")];
    if (!slides.length) return;
    let active = 0;
    let inView = true;
    let timer = null;

    const available = () => slides.filter((slide) => slide.complete && slide.naturalWidth > 0);

    function sync() {
        window.clearTimeout(timer);
        timer = null;
        const ready = available();
        if (ready.length > 1 && !document.hidden && inView) {
            timer = window.setTimeout(() => changeSlide(1), 8000);
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
        else if (timer === null) sync();
    }

    slides.forEach((slide) => {
        slide.addEventListener("load", imageSettled);
        slide.addEventListener("error", imageSettled);
    });
    document.addEventListener("visibilitychange", sync);
    watchMedia(reducedMotion, sync);
    // Restart timers when iOS/Safari restores a page from its back-forward cache.
    window.addEventListener("pageshow", () => { scheduleParallax(); imageSettled(); });
    window.addEventListener("pagehide", () => { window.clearTimeout(timer); timer = null; });
    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver(([entry]) => { inView = entry.isIntersecting; sync(); });
        observer.observe(hero);
    }
    imageSettled();
})();
