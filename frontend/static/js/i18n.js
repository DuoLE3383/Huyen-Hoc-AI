(() => {
  const supported = ["vi", "en", "zh", "ja"];
  const languagePicker = document.getElementById("language");
  const status = document.getElementById("i18nStatus");

  async function loadLanguage(language) {
    if (!supported.includes(language)) language = "vi";
    if (status) status.textContent = "";
    try {
      const response = await fetch(`/api/i18n/${language}`, {
        headers: { Accept: "application/json" }
      });
      if (!response.ok) throw new Error(`Translation request failed (${response.status})`);
      const result = await response.json();
      for (const element of document.querySelectorAll("[data-i18n]")) {
        const translated = result.translations[element.dataset.i18n];
        if (translated !== undefined) element.textContent = translated;
      }
      for (const element of document.querySelectorAll("[data-i18n-aria-label]")) {
        const translated = result.translations[element.dataset.i18nAriaLabel];
        if (translated !== undefined) element.setAttribute("aria-label", translated);
      }
      document.documentElement.lang = language;
      if (languagePicker) languagePicker.value = language;
      localStorage.setItem("lang", language);
    } catch (error) {
      console.error("Could not load interface translations.", error);
      if (status) status.textContent = "Không tải được bản dịch; giao diện giữ nguyên ngôn ngữ hiện tại.";
    }
  }

  languagePicker?.addEventListener("change", () => loadLanguage(languagePicker.value));
  const savedLanguage = localStorage.getItem("lang");
  const browserLanguage = navigator.language.split("-")[0].toLowerCase();
  loadLanguage(
    supported.includes(savedLanguage) ? savedLanguage :
      supported.includes(browserLanguage) ? browserLanguage : "vi"
  );
})();
