(() => {
    const storageKey = "heat-empire:comparison";
    const limit = 3;
    const instruction = "Выберите 2–3 модели одного типа.";

    function readSelection() {
        try {
            const saved = JSON.parse(localStorage.getItem(storageKey));
            if (!Array.isArray(saved)) return [];
            const unique = new Map();
            for (const item of saved.slice(0, limit)) {
                if (typeof item?.slug === "string" && /^[-\w]{1,100}$/.test(item.slug)
                    && typeof item.category === "string" && typeof item.name === "string") {
                    unique.set(item.slug, item);
                }
            }
            const items = [...unique.values()];
            return items.filter(item => item.category === items[0].category);
        } catch {
            return [];
        }
    }

    let selection = readSelection();

    function updateControls(message = instruction) {
        const slugs = new Set(selection.map(item => item.slug));
        for (const button of document.querySelectorAll("[data-compare-toggle]")) {
            const selected = slugs.has(button.dataset.compareToggle);
            const label = selected ? "Убрать из сравнения" : "Добавить в сравнение";
            button.textContent = label;
            button.setAttribute("aria-label", `${label} ${button.dataset.compareName}`);
            button.toggleAttribute("data-selected", selected);
            button.hidden = false;
        }

        const controls = document.querySelector("[data-compare-controls]");
        if (!controls) return;
        const submit = controls.querySelector("[data-compare-submit]");
        submit.textContent = `Сравнить (${selection.length})`;
        submit.disabled = selection.length < 2;

        const inputs = controls.querySelector("[data-compare-inputs]");
        const list = controls.querySelector("[data-compare-selection]");
        inputs.replaceChildren();
        list.replaceChildren();
        for (const item of selection) {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = "product";
            input.value = item.slug;
            inputs.append(input);

            const entry = document.createElement("li");
            entry.textContent = item.name;
            const remove = document.createElement("button");
            remove.type = "button";
            remove.dataset.compareRemove = item.slug;
            remove.textContent = "×";
            remove.setAttribute("aria-label", `Убрать ${item.name} из сравнения`);
            entry.append(remove);
            list.append(entry);
        }
        list.hidden = !selection.length;
        controls.hidden = false;
        controls.querySelector("[data-compare-status]").textContent = message;
    }

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-compare-toggle], [data-compare-remove]");
        if (!button) return;
        const slug = button.dataset.compareToggle ?? button.dataset.compareRemove;
        const selected = selection.some(item => item.slug === slug);

        if (selected) {
            selection = selection.filter(item => item.slug !== slug);
        } else {
            const category = button.dataset.compareCategory;
            if (selection.length && selection[0].category !== category) {
                document.querySelector("[data-compare-status]").textContent =
                    "Можно сравнивать только модели одного типа. Уберите выбранные модели, чтобы сменить тип.";
                return;
            }
            if (selection.length >= limit) {
                document.querySelector("[data-compare-status]").textContent =
                    "В сравнении уже три модели. Уберите одну, чтобы добавить другую.";
                return;
            }
            selection.push({ slug, category, name: button.dataset.compareName });
        }

        try {
            localStorage.setItem(storageKey, JSON.stringify(selection));
        } catch {
            // The current page still works when storage is blocked.
        }
        updateControls(selected ? "Модель убрана из сравнения." : "Модель добавлена в сравнение.");

        if (button.hasAttribute("data-compare-remove")) {
            const nextFocus = document.querySelector("[data-compare-remove]")
                ?? document.querySelector(`[data-compare-toggle="${slug}"]`)
                ?? document.querySelector("[data-compare-controls]");
            nextFocus?.focus({ preventScroll: true });
        }
    });

    document.addEventListener("catalog:updated", () => updateControls());
    window.addEventListener("pageshow", (event) => {
        if (!event.persisted) return;
        selection = readSelection();
        updateControls();
    });
    window.addEventListener("storage", (event) => {
        if (event.key !== storageKey && event.key !== null) return;
        selection = readSelection();
        updateControls();
    });
    updateControls();
})();
