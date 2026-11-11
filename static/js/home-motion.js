if ("IntersectionObserver" in window) {
    const groups = document.querySelectorAll("[data-reveal-group]");
    const observer = new IntersectionObserver(entries => {
        for (const entry of entries) {
            if (entry.isIntersecting) {
                entry.target.classList.add("is-revealed");
                observer.unobserve(entry.target);
            }
        }
    }, { rootMargin: "0px 0px -64px 0px" });

    for (const group of groups) {
        observer.observe(group);
    }
    document.documentElement.classList.add("motion-ready");
}

const gallery = document.querySelector(".gallery");

if (gallery && "IntersectionObserver" in window) {
    const galleryObserver = new IntersectionObserver(([entry]) => {
        gallery.classList.toggle("gallery--visible", entry.isIntersecting);
    });

    gallery.classList.add("gallery--motion");
    galleryObserver.observe(gallery);
}

const scrollPanels = document.querySelectorAll("[data-scroll-panel]");

if (scrollPanels.length && "ResizeObserver" in window) {
    const scrollObserver = new ResizeObserver(entries => {
        for (const { target } of entries) {
            const scrollable = target.scrollWidth > target.clientWidth;
            if (scrollable) {
                target.setAttribute("tabindex", "0");
                if (target.tagName === "DIV") target.setAttribute("role", "region");
                target.setAttribute("aria-label", target.dataset.scrollPanel);
            } else {
                target.removeAttribute("tabindex");
                target.removeAttribute("role");
                target.removeAttribute("aria-label");
            }
        }
    });

    for (const panel of scrollPanels) {
        scrollObserver.observe(panel);
    }
}
