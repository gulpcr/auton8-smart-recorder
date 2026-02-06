(function () {
  const WS_URL = "ws://127.0.0.1:8765";
  let socket;
  let connected = false;

  function connect() {
    socket = new WebSocket(WS_URL);
    socket.onopen = () => {
      connected = true;
      console.info("[recorder] connected to desktop");
    };
    socket.onclose = () => {
      connected = false;
      console.info("[recorder] socket closed, retrying...");
      setTimeout(connect, 2000);
    };
    socket.onerror = (e) => console.error("[recorder] socket error", e);
  }

  function framePath(win) {
    const chain = [];
    let current = win;
    while (current && current !== current.parent) {
      const frameEl = current.frameElement;
      if (!frameEl) break;
      chain.unshift({
        hints: {
          id: frameEl.id || null,
          name: frameEl.name || null,
          src: frameEl.src || null,
          title: frameEl.title || null,
        },
        locators: locatorCandidates(frameEl),
      });
      current = current.parent;
    }
    return chain;
  }

  function shadowPathFromEvent(evt) {
    const path = evt.composedPath ? evt.composedPath() : [];
    const hosts = [];
    for (const node of path) {
      if (node instanceof ShadowRoot && node.host) {
        hosts.unshift({ locators: locatorCandidates(node.host) });
      }
    }
    return hosts;
  }

  function locatorCandidates(el) {
    const locs = [];
    const attrs = ["data-testid", "data-test", "automation-id"];
    for (const attr of attrs) {
      const val = el.getAttribute && el.getAttribute(attr);
      if (val) locs.push({ type: "data", value: `[${attr}="${val}"]`, score: 0.95 });
    }
    const aria = el.getAttribute && (el.getAttribute("aria-label") || el.getAttribute("aria-labelledby"));
    if (aria) locs.push({ type: "aria", value: aria, score: 0.85 });
    if (el.id) locs.push({ type: "css", value: `#${cssEscape(el.id)}`, score: 0.8 });
    if (el.classList && el.classList.length) {
      const cls = Array.from(el.classList).slice(0, 3).join(".");
      locs.push({ type: "css", value: `${el.tagName.toLowerCase()}.${cls}`, score: 0.65 });
    }
    locs.push({ type: "css", value: el.tagName.toLowerCase(), score: 0.4 });
    return locs;
  }

  function cssEscape(ident) {
    return ident.replace(/([ #;?%&,.+*~\':"!^$[\]()=>|\/@])/g, "\\$1");
  }

  function handleEvent(evt) {
    if (!connected) return;
    const target = evt.target;
    if (!(target instanceof Element)) return;
    const payload = {
      id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
      type: evt.type === "dblclick" ? "dblclick" : evt.type,
      targetText: target.textContent ? target.textContent.trim().slice(0, 80) : "",
      page: {
        url: window.location.href,
        title: document.title,
      },
      framePath: framePath(window),
      shadowPath: shadowPathFromEvent(evt),
      locators: locatorCandidates(target),
      domContext: {
        htmlSnippet: target.outerHTML ? target.outerHTML.slice(0, 5000) : "",
      },
      timing: { timestamp: Date.now() },
    };
    // Capture input value for input/change events
    if ((evt.type === "input" || evt.type === "change") && target.value !== undefined) {
      payload.input = { value: target.value };
    }
    // Capture key information for keydown events
    if (evt.type === "keydown") {
      payload.key = evt.key;
      payload.input = { key: evt.key, value: evt.key };
    }
    socket.send(JSON.stringify(payload));
  }

  const events = ["click", "dblclick", "contextmenu", "input", "change", "submit", "keydown"];
  events.forEach((name) => window.addEventListener(name, handleEvent, { capture: true, passive: true }));

  connect();
})();

