const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");

for (const gallery of document.querySelectorAll(".case-photo")) {
    const slides = [...gallery.querySelectorAll(".case-photo__slide")];
    const controls = gallery.querySelector(".case-photo__controls");
    const counter = controls.querySelector("span");
    let activeIndex = 0;
    let transition;

    function endTransition() {
        if (!transition) return;
        transition.outgoing.hidden = true;
        for (const animation of transition.animations) animation.cancel();
        transition = null;
    }

    for (const button of controls.querySelectorAll("button")) {
        button.addEventListener("click", () => {
            endTransition();

            const step = Number(button.dataset.step);
            const outgoing = slides[activeIndex];
            activeIndex = (activeIndex + step + slides.length) % slides.length;
            const incoming = slides[activeIndex];
            incoming.hidden = false;
            counter.textContent = `${activeIndex + 1} / ${slides.length}`;

            if (reducedMotion.matches || !incoming.animate) {
                outgoing.hidden = true;
                return;
            }

            const timing = { duration: 350, easing: "cubic-bezier(.25,.7,.3,1)", fill: "both" };
            const animations = [
                outgoing.animate([{ transform: "translateX(0)" }, { transform: `translateX(${-step * 100}%)` }], timing),
                incoming.animate([{ transform: `translateX(${step * 100}%)` }, { transform: "translateX(0)" }], timing),
            ];
            const current = transition = { outgoing, animations };
            Promise.all(animations.map(animation => animation.finished)).then(() => {
                if (transition === current) endTransition();
            }, () => {});
        });
    }

    controls.hidden = false;
}
