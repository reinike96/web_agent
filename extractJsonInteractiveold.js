(function () {
  try {
    function getBetterSelector(el) {
      // Priority order: data-testid > id > name > class > nth-child
      if (el.getAttribute("data-testid")) return `[data-testid="${el.getAttribute("data-testid")}"]`;
      if (el.id) return `#${el.id}`;
      if (el.name) return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
      if (el.classList.length > 0) {
        const cls = [...el.classList].slice(0, 2).join('.');
        return `${el.tagName.toLowerCase()}.${cls}`;
      }
      if (el.getAttribute("aria-label")) {
        return `${el.tagName.toLowerCase()}[aria-label="${el.getAttribute("aria-label")}"]`;
      }
      // Fallback to nth-child
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
      const value = el.getAttribute("value");
      if (value) return value.trim();
      return null;
    }

    function isVisible(el) {
      try {
        return el.offsetParent !== null && 
               getComputedStyle(el).visibility !== 'hidden' && 
               getComputedStyle(el).display !== 'none';
      } catch (e) {
        // If getComputedStyle fails, assume visible if has offsetParent
        return el.offsetParent !== null;
      }
    }

    // Enhanced element selection - include more interactive elements and login-specific selectors
    const elements = Array.from(document.querySelectorAll(
      "button, input, textarea, select, a[href], [contenteditable='true'], [role='button'], [role='textbox'], [onclick], [data-testid], div[data-testid]"
    ))
      .filter(e => {
        // Basic visibility check
        try {
          return e.offsetParent !== null || e.innerText.trim() || e.getAttribute('data-testid');
        } catch (err) {
          return true; // If check fails, include it
        }
      })
      .map(e => {
        return {
          tag: e.tagName.toLowerCase(),
          selector: getBetterSelector(e),
          text: getText(e),
          name: e.getAttribute("name") || null,
          placeholder: e.getAttribute("placeholder") || null,
          "data-testid": e.getAttribute("data-testid") || null,
          "aria-label": e.getAttribute("aria-label") || null,
          type: e.getAttribute("type") || null,
          href: e.getAttribute("href") || null,
          contenteditable: e.getAttribute("contenteditable") || null,
          role: e.getAttribute("role") || null,
          className: e.className || null,
          id: e.id || null
        };
      })
      .filter(e => 
        // Keep elements that have useful identifying information
        e.text || e["data-testid"] || e.name || e.href || e["aria-label"] || 
        e.type || e.contenteditable || e.role || e.id ||
        (e.className && (e.className.includes('login') || e.className.includes('sign') || e.className.includes('button')))
      );

    const output = {
      url: location.href,
      title: document.title,
      timestamp: Date.now(),
      elements: elements
    };

    console.log('ExtractJsonInteractive result:', output);
    return output;
    
  } catch (error) {
    console.error('ExtractJsonInteractive error:', error);
    return {
      url: location.href,
      title: document.title,
      timestamp: Date.now(),
      elements: [],
      error: error.message
    };
  }
})();
