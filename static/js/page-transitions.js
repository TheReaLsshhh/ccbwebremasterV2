(() => {
    "use strict";
    // Content is visible by default, including when JavaScript or observers fail.
    if (!("IntersectionObserver" in window) || typeof Element.prototype.animate !== "function") return;
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const selector = [
        ".college-page-hero > .container", ".home-hero-inner", ".section-header",
        ".content-card", ".catalog-card", ".resource-card", ".program-feature",
        ".college-story", ".news-grid-card", ".admission-step", ".admission-support-panel",
        ".about-topic-card", ".institutional-section", ".service-link", ".directory-row",
        ".detail-copy", ".news-article > article", ".legal-copy > section", ".search-result"
    ].join(",");
    const revealed = new WeakSet();
    const running = new Set();
    let observer = null;

    function stop() {
        if (observer) observer.disconnect();
        observer = null;
        running.forEach(animation => animation.cancel());
        running.clear();
    }
    function observe(root) {
        if (preference.matches) return;
        if (!observer) {
            observer = new IntersectionObserver(entries => {
                if (preference.matches || !observer) return;
                let order = 0;
                entries.forEach(entry => {
                    if (!entry.isIntersecting) return;
                    const element = entry.target;
                    observer.unobserve(element);
                    if (revealed.has(element)) return;
                    revealed.add(element);
                    // Never transform a container while someone is using its controls.
                    if (preference.matches || element.contains(document.activeElement)) return;
                    const animation = element.animate([
                        { opacity: 0, transform: "translateY(16px)" },
                        { opacity: 1, transform: "translateY(0)" }
                    ], { duration: 440, delay: Math.min(order++ * 35, 105), easing: "cubic-bezier(.2,.7,.2,1)", fill: "backwards" });
                    running.add(animation);
                    animation.onfinish = animation.oncancel = () => running.delete(animation);
                });
            }, { threshold: 0, rootMargin: "0px 0px -24px 0px" });
        }
        root.querySelectorAll(selector).forEach(element => {
            if (revealed.has(element) || element.parentElement.closest(selector)) return;
            observer.observe(element);
        });
    }
    function refresh() { stop(); observe(document); }
    if (typeof preference.addEventListener === "function") preference.addEventListener("change", refresh);
    else if (typeof preference.addListener === "function") preference.addListener(refresh);
    document.addEventListener("ccb:region-refreshed", event => observe(event.target));
    document.addEventListener("focusin", () => running.forEach(animation => {
        if (animation.effect.target.contains(document.activeElement)) animation.cancel();
    }));
    window.addEventListener("pagehide", stop);
    window.addEventListener("pageshow", () => observe(document));
    observe(document);
})();
