function showQuoteDialog(dialog) {
    if (typeof dialog?.showModal !== "function") return false;

    dialog.showModal();
    const focusTarget = dialog.querySelector("[aria-invalid='true']") || dialog.querySelector("h2");
    focusTarget.focus();
    return true;
}

for (const trigger of document.querySelectorAll("[data-open-dialog]")) {
    trigger.addEventListener("click", event => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

        const dialog = document.getElementById(trigger.dataset.openDialog);
        if (showQuoteDialog(dialog)) event.preventDefault();
    });
}

for (const dialog of document.querySelectorAll(".quote-dialog")) {
    dialog.querySelector("[data-close-dialog]").addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", event => {
        if (event.target === dialog) dialog.close();
    });
}

const initialDialog = document.querySelector(".quote-dialog[data-open-on-load]");
if (showQuoteDialog(initialDialog)) {
    const status = document.getElementById("quote-status");
    if (status) status.hidden = true;
}
