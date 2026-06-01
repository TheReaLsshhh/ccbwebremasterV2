(function () {
    const modalElement = document.getElementById("newsDetailModal");
    const modalBody = document.getElementById("newsDetailModalBody");

    if (!modalElement || !modalBody || !window.bootstrap || !window.bootstrap.Modal) {
        return;
    }

    function mountNewsModalToBody() {
        document.querySelectorAll(".news-detail-source").forEach(function (source) {
            document.body.appendChild(source);
        });
        document.body.appendChild(modalElement);
    }

    mountNewsModalToBody();

    const newsModal = new window.bootstrap.Modal(modalElement, {
        backdrop: true,
        keyboard: true,
        focus: true,
    });

    function shouldIgnoreClick(target) {
        return Boolean(
            target.closest(
                ".news-detail-ignore, .news-carousel-arrow, .carousel-indicators, [data-bs-slide], [data-bs-slide-to], [data-bs-target='#campusNewsCarousel'], a.news-read-more-link"
            )
        );
    }

    function openNewsDetail(newsId) {
        const source = document.getElementById("news-detail-source-" + newsId);
        if (!source) {
            return false;
        }

        modalBody.innerHTML = source.innerHTML;
        const titleElement = modalBody.querySelector(".news-detail-modal-title");
        if (titleElement) {
            modalElement.setAttribute("aria-labelledby", "newsDetailModalTitle");
            titleElement.id = "newsDetailModalTitle";
        }
        newsModal.show();
        return true;
    }

    function scrollToNewsCard(newsId) {
        const card = document.getElementById("news-" + newsId);
        if (!card) {
            return;
        }

        card.scrollIntoView({ behavior: "smooth", block: "center" });
        card.classList.add("is-news-highlight");
        window.setTimeout(function () {
            card.classList.remove("is-news-highlight");
        }, 2200);
    }

    function getAutoOpenNewsId() {
        if (window.ccbOpenNewsId) {
            return String(window.ccbOpenNewsId);
        }

        const params = new URLSearchParams(window.location.search);
        if (params.has("open")) {
            return params.get("open");
        }

        const hashMatch = window.location.hash.match(/^#news-(\d+)$/);
        return hashMatch ? hashMatch[1] : null;
    }

    function clearOpenNewsFromUrl() {
        const url = new URL(window.location.href);
        const page = url.searchParams.get("page");
        let changed = false;

        if (url.searchParams.has("open")) {
            url.searchParams.delete("open");
            changed = true;
        }

        if (url.hash.match(/^#news-\d+$/)) {
            url.hash = "";
            changed = true;
        }

        if (!changed) {
            return;
        }

        url.search = page ? "?page=" + encodeURIComponent(page) : "";
        window.history.replaceState(null, "", url.pathname + url.search + url.hash);
    }

    function handleTrigger(event) {
        const trigger = event.target.closest(".news-grid-card-interactive[data-news-id], button.news-read-more-link[data-news-id]");
        if (!trigger || shouldIgnoreClick(event.target)) {
            return;
        }

        const newsId = trigger.getAttribute("data-news-id");
        if (!newsId) {
            return;
        }

        event.preventDefault();
        openNewsDetail(newsId);
    }

    document.addEventListener("click", handleTrigger);

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " ") {
            return;
        }

        const interactiveCard = event.target.closest(".news-grid-card-interactive");
        if (!interactiveCard || event.target !== interactiveCard || shouldIgnoreClick(event.target)) {
            return;
        }

        handleTrigger(event);
    });

    modalElement.addEventListener("hidden.bs.modal", function () {
        modalBody.innerHTML = "";
        modalElement.removeAttribute("aria-labelledby");
    });

    const autoOpenNewsId = getAutoOpenNewsId();
    if (autoOpenNewsId) {
        window.requestAnimationFrame(function () {
            scrollToNewsCard(autoOpenNewsId);
            window.setTimeout(function () {
                if (openNewsDetail(autoOpenNewsId)) {
                    clearOpenNewsFromUrl();
                }
                window.ccbOpenNewsId = null;
            }, 320);
        });
    }
})();
