for (const gallery of document.querySelectorAll(".case-photo")) {
    const slides = [...gallery.querySelectorAll(".case-photo__slide")];
    const controls = gallery.querySelector(".case-photo__controls");
    const counter = controls.querySelector("span");
    let activeIndex = 0;

    for (const button of controls.querySelectorAll("button")) {
        button.addEventListener("click", () => {
            slides[activeIndex].hidden = true;
            activeIndex = (activeIndex + Number(button.dataset.step) + slides.length) % slides.length;
            slides[activeIndex].hidden = false;
            counter.textContent = `${activeIndex + 1} / ${slides.length}`;
        });
    }

    controls.hidden = false;
}
