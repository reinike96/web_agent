(() => {
  const output = {
    url: location.href,
    title: document.title,
    headings: [],
    repeatedBlocks: []
  };

  const headers = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
  headers.forEach(h => {
    if (h.offsetParent === null) return;
    output.headings.push({
      tag: h.tagName.toLowerCase(),
      level: parseInt(h.tagName[1], 10),
      text: h.innerText.trim()
    });
  });

  const container = document.querySelector('main') || document.body;

  const counts = {};
  Array.from(container.children).forEach(child => {
    const key = `${child.tagName}.${[...child.classList].join('.')}`;
    if (!counts[key]) counts[key] = [];
    counts[key].push(child);
  });

  for (const [key, nodes] of Object.entries(counts)) {
    if (nodes.length > 2) {
      output.repeatedBlocks.push({
        pattern: key,
        count: nodes.length,
        sampleText: nodes[0].innerText.trim().slice(0, 100) || null
      });
    }
  }

  console.log(output);
  return output;
})();
