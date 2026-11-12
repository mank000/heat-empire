const mobileFilters = matchMedia("(max-width: 679px)");
const catalogStatus = document.querySelector("[data-catalog-status]");
document.querySelector("[data-catalog-submit]").hidden = true;
if (mobileFilters.matches) {
    document.querySelector("[data-collapse-mobile]")?.removeAttribute("open");
}

let pendingRequest;
let inputTimer;

async function updateCatalog(url) {
    clearTimeout(inputTimer);
    pendingRequest?.abort();
    const request = new AbortController();
    pendingRequest = request;
    catalogStatus.textContent = "";

    try {
        const response = await fetch(url, { signal: request.signal });
        if (!response.ok) throw new Error("Catalog request failed");
        const page = new DOMParser().parseFromString(await response.text(), "text/html");
        if (request.signal.aborted) return;

        const currentLayout = document.querySelector("[data-catalog-layout]");
        const newLayout = page.querySelector("[data-catalog-layout]");
        if (!newLayout) throw new Error("Catalog layout missing");

        const activeControl = currentLayout.contains(document.activeElement) ? document.activeElement : null;
        const currentFilters = currentLayout.querySelector("details");
        const newFilters = newLayout.querySelector("details");
        newFilters.open = currentFilters.open || Boolean(newFilters.querySelector(".errorlist"));
        newLayout.querySelector("[data-catalog-submit]").hidden = true;

        // Keep the same filter focused so keyboard input can continue across updates.
        const newControl = activeControl?.id ? page.getElementById(activeControl.id) : null;
        const selectionStart = activeControl?.selectionStart;
        const selectionEnd = activeControl?.selectionEnd;
        currentLayout.replaceWith(newLayout);
        newControl?.focus({ preventScroll: true });
        if (selectionStart != null && selectionEnd != null) {
            newControl?.setSelectionRange(selectionStart, selectionEnd);
        }
        history.replaceState(null, "", url);
        const count = newLayout.querySelector("[data-catalog-count]").textContent;
        catalogStatus.textContent = newFilters.querySelector(".errorlist")
            ? "Проверьте параметры фильтра."
            : `Найдено моделей: ${count}`;
    } catch (error) {
        if (!request.signal.aborted) location.assign(url);
    }
}

function applyFilters(form) {
    if (!form.reportValidity()) return;
    const url = new URL(form.action);
    url.hash = "";
    for (const [key, value] of new FormData(form)) {
        if (value.trim()) url.searchParams.append(key, value);
    }
    updateCatalog(url);
}

document.addEventListener("submit", (event) => {
    if (!event.target.matches("[data-catalog-filters]")) return;
    event.preventDefault();
    applyFilters(event.target);
});

document.addEventListener("change", (event) => {
    const field = event.target;
    const form = field.closest("[data-catalog-filters]");
    if (form && field.matches("select, input[type=checkbox], input[type=radio]")) applyFilters(form);
});

document.addEventListener("input", (event) => {
    const field = event.target;
    const form = field.closest("[data-catalog-filters]");
    if (!form || !field.matches("input[type=search], input[type=number]")) return;
    pendingRequest?.abort();
    clearTimeout(inputTimer);
    inputTimer = setTimeout(() => applyFilters(form), 350);
});

document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-catalog-update]");
    if (!link || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    updateCatalog(link.href);
});
