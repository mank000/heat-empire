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
