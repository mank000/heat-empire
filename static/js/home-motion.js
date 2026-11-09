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
const galleryToggle = gallery?.querySelector(".gallery__toggle");

if (galleryToggle && "IntersectionObserver" in window) {
    const galleryObserver = new IntersectionObserver(([entry]) => {
        gallery.classList.toggle("gallery--visible", entry.isIntersecting);
    });

    galleryToggle.addEventListener("click", () => {
        const paused = gallery.classList.toggle("gallery--paused");
        galleryToggle.textContent = paused ? "Продолжить" : "Пауза";
    });

    gallery.classList.add("gallery--motion");
    galleryToggle.hidden = false;
    galleryObserver.observe(gallery);
}
