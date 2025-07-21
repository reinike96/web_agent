(function () {
  function getBetterSelector(el) {
    if (el.id) return `#${el.id}`;
    if (el.getAttribute("data-testid")) return `[data-testid="${el.getAttribute("data-testid")}"]`;
    if (el.name) return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
    if (el.classList.length > 0) {
      const cls = [...el.classList].slice(0, 2).join('.');
      return `${el.tagName.toLowerCase()}.${cls}`;
    }
    const idx = [...el.parentNode.children].indexOf(el) + 1;
    return `${el.tagName.toLowerCase()}:nth-child(${idx})`;
  }

  function getText(el) {
    const t = el.innerText?.trim();
    if (t) return t;
    const aria = el.getAttribute("aria-label");
    if (aria) return aria.trim();
    const title = el.getAttribute("title");
    if (title) return title.trim();
    const placeholder = el.getAttribute("placeholder");
    if (placeholder) return placeholder.trim();
    return null;
  }

  const elements = Array.from(document.querySelectorAll("button, input"))
    .filter(e =>
      e.offsetParent !== null &&               // visible
      (!e.disabled) &&                         // usable
      (getText(e) || e.getAttribute("data-testid") || e.name)
    )
    .map(e => {
      return {
        tag: e.tagName.toLowerCase(),
        selector: getBetterSelector(e),
        text: getText(e),
        name: e.getAttribute("name") || null,
        placeholder: e.getAttribute("placeholder") || null,
        "data-testid": e.getAttribute("data-testid") || null,
        "aria-label": e.getAttribute("aria-label") || null
      };
    });

  const output = {
    url: location.href,
    title: document.title,
    elements
  };

  console.log(output);
  return output;
})();
