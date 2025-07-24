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
    const text = el.innerText?.trim();
    if (text) return text;
    const aria = el.getAttribute("aria-label");
    if (aria) return aria.trim();
    const title = el.getAttribute("title");
    if (title) return title.trim();
    const placeholder = el.getAttribute("placeholder");
    if (placeholder) return placeholder.trim();
    return null;
  }

  function isVisibleAndEnabled(e) {
    return e.offsetParent !== null && !e.disabled;
  }

  function isEditable(e) {
    if (e.tagName.toLowerCase() === 'input' || e.tagName.toLowerCase() === 'textarea') {
      return !e.readOnly && isVisibleAndEnabled(e);
    }
    if (e.isContentEditable) {
      return isVisibleAndEnabled(e);
    }
    return false;
  }

  function isActionableButton(e) {
    const tag = e.tagName.toLowerCase();
    if (tag === 'button' || tag === 'input' || e.getAttribute('role') === 'button') {
      return isVisibleAndEnabled(e);
    }
    return false;
  }

  const elements = Array.from(document.querySelectorAll("button, input, [role='button'], [contenteditable='true']"))
    .filter(e => 
      (
        isEditable(e) || isActionableButton(e)
      ) &&
      (
        getText(e) || e.getAttribute("data-testid") || e.name
      )
    )
    .map(e => {
      return {
        tag: e.tagName.toLowerCase(),
        selector: getBetterSelector(e),
        text: getText(e),
        name: e.getAttribute("name") || null,
        placeholder: e.getAttribute("placeholder") || null,
        "data-testid": e.getAttribute("data-testid") || null,
        "aria-label": e.getAttribute("aria-label") || null,
        contenteditable: e.isContentEditable || null
      };
    });

  const seen = new Set();
  const uniqueElements = elements.filter(el => {
    const key = `${el.tag}::${el.text}`;
    if (seen.has(key)) {
      return false;
    } else {
      seen.add(key);
      return true;
    }
  });

  const output = {
    url: location.href,
    title: document.title,
    elements: uniqueElements
  };

  console.log(JSON.stringify(output, null, 2));
  return output;
})();
