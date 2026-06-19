(function () {
    function initMobileNav() {
        const modalElement = document.getElementById("mobileNavModal");
        if (!modalElement || !window.bootstrap || !window.bootstrap.Modal) {
            return;
        }

        const mobileNavModal = window.bootstrap.Modal.getOrCreateInstance(modalElement);

        modalElement.querySelectorAll(".mobile-nav-link").forEach(function (link) {
            link.addEventListener("click", function () {
                mobileNavModal.hide();
            });
        });

        const desktopNavQuery = window.matchMedia("(min-width: 1200px)");

        function closeOnDesktop(event) {
            if (event.matches) {
                mobileNavModal.hide();
            }
        }

        if (typeof desktopNavQuery.addEventListener === "function") {
            desktopNavQuery.addEventListener("change", closeOnDesktop);
        } else if (typeof desktopNavQuery.addListener === "function") {
            desktopNavQuery.addListener(closeOnDesktop);
        }

        closeOnDesktop(desktopNavQuery);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initMobileNav);
    } else {
        initMobileNav();
    }
})();
