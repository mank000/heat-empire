document.addEventListener("focusout", ({ target }) => {
    if (!target.matches("input[type='tel']")) return;

    const value = target.value.trim();
    if (!/^\+?[0-9 .()\-–—\u00a0\u202f]+$/.test(value)) return;

    let digits = value.replace(/\D/g, "");
    const hasPlus = value.startsWith("+");
    if (digits.length === 11 && (digits[0] === "7" || (digits[0] === "8" && !hasPlus))) {
        digits = digits.slice(1);
    } else if (digits.length !== 10 || hasPlus) {
        return;
    }

    target.value = `+7 (${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 8)}-${digits.slice(8)}`;
});
