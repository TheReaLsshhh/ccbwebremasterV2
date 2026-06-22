(function () {
    const regions = Array.from(document.querySelectorAll("[data-refresh-url]"));
    if (!regions.length || !window.fetch) {
        return;
    }

    const normalizeHtml = function (html) {
        return html.trim().replace(/\s+/g, " ");
    };

    const refreshRegion = async function (region) {
        if (document.hidden || region.dataset.refreshing === "true") {
            return;
        }

        const url = region.dataset.refreshUrl;
        if (!url) {
            return;
        }

        region.dataset.refreshing = "true";
        try {
            const response = await fetch(url, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
                credentials: "same-origin",
                cache: "no-store",
            });

            if (!response.ok) {
                return;
            }

            const nextHtml = await response.text();
            if (normalizeHtml(nextHtml) === normalizeHtml(region.innerHTML)) {
                return;
            }

            region.classList.add("ajax-refresh-region-updating");
            window.setTimeout(function () {
                region.innerHTML = nextHtml;
                region.classList.remove("ajax-refresh-region-updating");
                region.dispatchEvent(new CustomEvent("ccb:region-refreshed", { bubbles: true }));
            }, 120);
        } catch (error) {
            return;
        } finally {
            region.dataset.refreshing = "false";
        }
    };

    regions.forEach(function (region) {
        const interval = Math.max(Number(region.dataset.refreshInterval) || 15000, 5000);
        region.dataset.refreshing = "false";
        window.setInterval(function () {
            refreshRegion(region);
        }, interval);
    });

    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) {
            regions.forEach(refreshRegion);
        }
    });
})();
