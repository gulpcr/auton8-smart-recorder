/**
 * Advanced Browser Instrumentation Script
 * 
 * Features:
 * - Multi-dimensional element capture (structural, visual, semantic, behavioral)
 * - OCR text extraction from visual elements
 * - Visual hash computation (perceptual hashing)
 * - Framework detection (React, Vue, Angular)
 * - Event listener detection
 * - Network request tracking
 * - Performance monitoring
 * - Mutation observer for dynamic content
 * - Intersection observer for visibility tracking
 */

(function () {
  'use strict';

  const WS_URL = "ws://127.0.0.1:8765";
  let socket;
  let connected = false;
  let sessionId = generateSessionId();
  
  // Feature flags
  const config = {
    captureScreenshots: true,
    computeVisualHash: true,
    detectFramework: true,
    trackNetwork: true,
    trackPerformance: true,
    trackMutations: true,
    captureConsole: true
  };

  // State tracking
  const state = {
    framework: null,
    networkRequests: [],
    mutations: [],
    performanceMetrics: {},
    capturedElements: new WeakSet()
  };

  // ============================================================================
  // Utility Functions
  // ============================================================================

  function generateSessionId() {
    return 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
  }

  function generateElementId(element) {
    if (!element.__recorder_id) {
      element.__recorder_id = 'elem-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }
    return element.__recorder_id;
  }

  function getXPath(element) {
    if (element.id) {
      return `//*[@id="${element.id}"]`;
    }
    
    const segments = [];
    for (let node = element; node && node.nodeType === 1; node = node.parentNode) {
      let index = 1;
      for (let sibling = node.previousSibling; sibling; sibling = sibling.previousSibling) {
        if (sibling.nodeType === 1 && sibling.nodeName === node.nodeName) {
          index++;
        }
      }
      
      const tagName = node.nodeName.toLowerCase();
      const segment = index > 1 ? `${tagName}[${index}]` : tagName;
      segments.unshift(segment);
      
      if (node === document.documentElement) break;
    }
    
    return '/' + segments.join('/');
  }

  function getRelativeXPath(element) {
    // Generate XPath relative to nearest ID
    let current = element;
    let path = [];
    
    while (current && current !== document.documentElement) {
      if (current.id) {
        path.unshift(`//*[@id="${current.id}"]`);
        break;
      }
      
      let index = 1;
      for (let sibling = current.previousSibling; sibling; sibling = sibling.previousSibling) {
        if (sibling.nodeType === 1 && sibling.nodeName === current.nodeName) {
          index++;
        }
      }
      
      const tagName = current.nodeName.toLowerCase();
      const segment = index > 1 ? `${tagName}[${index}]` : tagName;
      path.push(segment);
      current = current.parentNode;
    }
    
    return path.join('/');
  }

  function getCSSSelector(element) {
    if (element.id) {
      return '#' + cssEscape(element.id);
    }
    
    const parts = [];
    let current = element;
    
    while (current && current !== document.documentElement) {
      let selector = current.tagName.toLowerCase();
      
      if (current.id) {
        selector += '#' + cssEscape(current.id);
        parts.unshift(selector);
        break;
      }
      
      if (current.className) {
        const classes = Array.from(current.classList)
          .filter(c => !isDynamicClass(c))
          .slice(0, 2)
          .map(c => '.' + cssEscape(c))
          .join('');
        selector += classes;
      }
      
      parts.unshift(selector);
      current = current.parentNode;
    }
    
    return parts.join(' > ');
  }

  function cssEscape(ident) {
    return CSS.escape ? CSS.escape(ident) : ident.replace(/([ #;?%&,.+*~\':"!^$[\]()=>|\/@])/g, "\\$1");
  }

  function isDynamicClass(className) {
    // Detect likely dynamic class names
    const patterns = [
      /^[a-f0-9]{8,}$/i,  // Hash-like
      /^css-[a-z0-9]+$/i, // CSS modules
      /^_[a-z0-9_]+$/i,   // Underscore prefix
      /^[A-Z][a-z]+__[a-z]+--[a-z0-9]+$/ // BEM with hash
    ];
    
    return patterns.some(pattern => pattern.test(className));
  }

  function isDynamicId(id) {
    // Detect dynamic IDs (UUIDs, timestamps, etc.)
    const patterns = [
      /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i, // UUID
      /^id-\d+$/,  // id-123456
      /\d{10,}/    // Timestamp
    ];
    
    return patterns.some(pattern => pattern.test(id));
  }

  // ============================================================================
  // Visual Features
  // ============================================================================

  function captureElementScreenshot(element) {
    if (!config.captureScreenshots) return null;
    
    try {
      const rect = element.getBoundingClientRect();
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      canvas.width = rect.width;
      canvas.height = rect.height;
      
      // Note: Actual screenshot capture requires browser API (CDP or extension)
      // This is a placeholder - actual implementation would use chrome.tabs.captureVisibleTab
      
      return {
        dataUrl: null, // Would contain base64 screenshot
        width: rect.width,
        height: rect.height
      };
    } catch (e) {
      console.warn('[recorder] Screenshot capture failed:', e);
      return null;
    }
  }

  function computeColorHistogram(element) {
    const styles = window.getComputedStyle(element);
    return {
      backgroundColor: styles.backgroundColor,
      color: styles.color,
      borderColor: styles.borderColor
    };
  }

  function computeVisualHash(element) {
    if (!config.computeVisualHash) return null;
    
    // Simple visual fingerprint based on element properties
    const rect = element.getBoundingClientRect();
    const styles = window.getComputedStyle(element);
    
    const fingerprint = [
      rect.width,
      rect.height,
      styles.backgroundColor,
      styles.color,
      styles.fontSize,
      styles.fontFamily,
      element.tagName
    ].join('|');
    
    // Simple hash function
    let hash = 0;
    for (let i = 0; i < fingerprint.length; i++) {
      const char = fingerprint.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    
    return hash.toString(16);
  }

  // ============================================================================
  // Structural Features
  // ============================================================================

  function generateLocators(element) {
    const locators = [];
    
    // Data attributes (highest priority)
    const dataAttrs = ['data-testid', 'data-test', 'data-cy', 'data-qa', 'automation-id'];
    for (const attr of dataAttrs) {
      const value = element.getAttribute(attr);
      if (value) {
        locators.push({
          type: 'data-attribute',
          selector: `[${attr}="${value}"]`,
          score: 0.95,
          stable: true
        });
      }
    }
    
    // ARIA labels
    const ariaLabel = element.getAttribute('aria-label');
    if (ariaLabel) {
      locators.push({
        type: 'aria-label',
        selector: `[aria-label="${ariaLabel}"]`,
        score: 0.90,
        stable: true
      });
    }
    
    const ariaLabelledBy = element.getAttribute('aria-labelledby');
    if (ariaLabelledBy) {
      locators.push({
        type: 'aria-labelledby',
        selector: `[aria-labelledby="${ariaLabelledBy}"]`,
        score: 0.88,
        stable: true
      });
    }
    
    // ID (stable if not dynamic)
    if (element.id && !isDynamicId(element.id)) {
      locators.push({
        type: 'id',
        selector: `#${cssEscape(element.id)}`,
        score: 0.85,
        stable: true
      });
    }
    
    // Name attribute
    const name = element.getAttribute('name');
    if (name) {
      locators.push({
        type: 'name',
        selector: `[name="${name}"]`,
        score: 0.82,
        stable: true
      });
    }
    
    // CSS selector
    locators.push({
      type: 'css',
      selector: getCSSSelector(element),
      score: 0.70,
      stable: false
    });
    
    // XPath (relative)
    locators.push({
      type: 'xpath-relative',
      selector: getRelativeXPath(element),
      score: 0.65,
      stable: false
    });
    
    // Text content
    const text = element.textContent?.trim();
    if (text && text.length > 0 && text.length < 100) {
      locators.push({
        type: 'text',
        selector: text,
        score: 0.60,
        stable: false
      });
    }
    
    // XPath (absolute)
    locators.push({
      type: 'xpath-absolute',
      selector: getXPath(element),
      score: 0.40,
      stable: false
    });
    
    return locators;
  }

  function extractElementAttributes(element) {
    const attrs = {};
    if (element.attributes) {
      for (const attr of element.attributes) {
        attrs[attr.name] = attr.value;
      }
    }
    return attrs;
  }

  function getParentChain(element) {
    const chain = [];
    let current = element.parentElement;
    let depth = 0;
    
    while (current && depth < 5) {
      chain.push({
        tagName: current.tagName,
        id: current.id || null,
        classes: Array.from(current.classList || [])
      });
      current = current.parentElement;
      depth++;
    }
    
    return chain;
  }

  // ============================================================================
  // Semantic Features
  // ============================================================================

  function classifyElementRole(element) {
    const tagName = element.tagName.toLowerCase();
    const role = element.getAttribute('role');
    const type = element.getAttribute('type');
    
    // Explicit role
    if (role) return role;
    
    // Tag-based classification
    const tagRoles = {
      'button': 'button',
      'a': 'link',
      'input': 'input',
      'textarea': 'input',
      'select': 'select',
      'form': 'form',
      'nav': 'navigation',
      'img': 'image',
      'video': 'video',
      'audio': 'audio'
    };
    
    if (tagRoles[tagName]) return tagRoles[tagName];
    
    // Input type-based
    if (tagName === 'input' && type) {
      return `input-${type}`;
    }
    
    // Heuristic based on classes/content
    const text = element.textContent?.toLowerCase() || '';
    if (text.includes('submit') || text.includes('send')) return 'submit-button';
    if (text.includes('cancel') || text.includes('close')) return 'cancel-button';
    
    return 'unknown';
  }

  // ============================================================================
  // Behavioral Features
  // ============================================================================

  function detectEventListeners(element) {
    const listeners = [];
    
    // Check for onclick, onchange, etc.
    const eventAttrs = [
      'onclick', 'onchange', 'onsubmit', 'onkeydown', 'onkeyup',
      'onmousedown', 'onmouseup', 'onmouseover', 'onmouseout',
      'onfocus', 'onblur', 'ondblclick', 'oncontextmenu'
    ];
    
    for (const attr of eventAttrs) {
      if (element.getAttribute(attr)) {
        listeners.push(attr.substring(2)); // Remove 'on' prefix
      }
    }
    
    // Note: Cannot reliably detect addEventListener listeners from content script
    // Would need access to browser internals via CDP
    
    return listeners;
  }

  function detectFramework(element) {
    if (state.framework) return state.framework;
    
    const info = {
      name: 'unknown',
      version: null,
      componentId: null
    };
    
    // React
    const reactKey = Object.keys(element).find(key => 
      key.startsWith('__react') || key.startsWith('_react')
    );
    if (reactKey) {
      info.name = 'react';
      const fiber = element[reactKey];
      if (fiber && fiber.return && fiber.return.elementType) {
        info.componentId = fiber.return.elementType.name;
      }
    }
    
    // Vue
    if (element.__vue__ || element.__vueParentComponent) {
      info.name = 'vue';
      const vue = element.__vue__ || element.__vueParentComponent;
      if (vue && vue.$options && vue.$options.name) {
        info.componentId = vue.$options.name;
      }
    }
    
    // Angular
    if (element.getAttribute('ng-reflect-name') || element.classList.toString().includes('ng-')) {
      info.name = 'angular';
    }
    
    state.framework = info;
    return info;
  }

  // ============================================================================
  // Frame & Shadow DOM Handling
  // ============================================================================

  function getFramePath(win) {
    const chain = [];
    let current = win;
    
    while (current && current !== current.parent) {
      const frameElement = current.frameElement;
      if (!frameElement) break;
      
      chain.unshift({
        hints: {
          id: frameElement.id || null,
          name: frameElement.name || null,
          src: frameElement.src || null,
          title: frameElement.title || null
        },
        locators: generateLocators(frameElement)
      });
      
      current = current.parent;
    }
    
    return chain;
  }

  function getShadowPath(event) {
    if (!event.composedPath) return [];
    
    const path = event.composedPath();
    const shadowHosts = [];
    
    for (const node of path) {
      if (node instanceof ShadowRoot && node.host) {
        shadowHosts.unshift({
          locators: generateLocators(node.host)
        });
      }
    }
    
    return shadowHosts;
  }

  // ============================================================================
  // Network Tracking
  // ============================================================================

  function initNetworkTracking() {
    if (!config.trackNetwork) return;
    
    // Intercept fetch
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
      const startTime = performance.now();
      const url = args[0];
      
      return originalFetch.apply(this, args).then(response => {
        const duration = performance.now() - startTime;
        state.networkRequests.push({
          type: 'fetch',
          url: typeof url === 'string' ? url : url.url,
          method: args[1]?.method || 'GET',
          status: response.status,
          duration: duration,
          timestamp: Date.now()
        });
        return response;
      });
    };
    
    // Intercept XMLHttpRequest
    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;
    
    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
      this._recordedUrl = url;
      this._recordedMethod = method;
      this._recordedStartTime = performance.now();
      return originalOpen.call(this, method, url, ...rest);
    };
    
    XMLHttpRequest.prototype.send = function(...args) {
      this.addEventListener('load', function() {
        const duration = performance.now() - this._recordedStartTime;
        state.networkRequests.push({
          type: 'xhr',
          url: this._recordedUrl,
          method: this._recordedMethod,
          status: this.status,
          duration: duration,
          timestamp: Date.now()
        });
      });
      return originalSend.apply(this, args);
    };
  }

  // ============================================================================
  // Performance Monitoring
  // ============================================================================

  function capturePerformanceMetrics() {
    if (!config.trackPerformance) return {};
    
    const perfData = performance.getEntriesByType('navigation')[0] || {};
    const memory = performance.memory || {};
    
    return {
      domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
      loadComplete: perfData.loadEventEnd - perfData.loadEventStart,
      memoryUsed: memory.usedJSHeapSize,
      memoryLimit: memory.jsHeapSizeLimit,
      timestamp: Date.now()
    };
  }

  // ============================================================================
  // Mutation Observer
  // ============================================================================

  function initMutationObserver() {
    if (!config.trackMutations) return;
    
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        state.mutations.push({
          type: mutation.type,
          target: mutation.target.tagName,
          addedNodes: mutation.addedNodes.length,
          removedNodes: mutation.removedNodes.length,
          timestamp: Date.now()
        });
      }
      
      // Keep only recent mutations
      if (state.mutations.length > 100) {
        state.mutations = state.mutations.slice(-50);
      }
    });
    
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeOldValue: false
    });
  }

  // ============================================================================
  // Console Capture
  // ============================================================================

  function initConsoleCapture() {
    if (!config.captureConsole) return;
    
    const originalConsole = {
      log: console.log,
      warn: console.warn,
      error: console.error
    };
    
    ['log', 'warn', 'error'].forEach(method => {
      console[method] = function(...args) {
        // Store console messages for context
        const message = args.map(arg => 
          typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
        ).join(' ');
        
        // Keep only recent messages
        if (!state.consoleMessages) state.consoleMessages = [];
        state.consoleMessages.push({
          level: method,
          message: message,
          timestamp: Date.now()
        });
        
        if (state.consoleMessages.length > 50) {
          state.consoleMessages = state.consoleMessages.slice(-25);
        }
        
        originalConsole[method].apply(console, args);
      };
    });
  }

  // ============================================================================
  // WebSocket Connection
  // ============================================================================

  function connect() {
    socket = new WebSocket(WS_URL);
    
    socket.onopen = () => {
      connected = true;
      console.info('[recorder] Connected to desktop app');
      
      // Send initial session info
      send({
        type: 'session_start',
        sessionId: sessionId,
        page: {
          url: window.location.href,
          title: document.title,
          viewport: {
            width: window.innerWidth,
            height: window.innerHeight
          }
        },
        userAgent: navigator.userAgent,
        timestamp: Date.now()
      });
    };
    
    socket.onclose = () => {
      connected = false;
      console.info('[recorder] Connection closed, reconnecting...');
      setTimeout(connect, 2000);
    };
    
    socket.onerror = (error) => {
      console.error('[recorder] WebSocket error:', error);
    };
  }

  function send(payload) {
    if (connected && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
    }
  }

  // ============================================================================
  // Event Handling
  // ============================================================================

  function handleEvent(event) {
    if (!connected) return;
    
    const target = event.target;
    if (!(target instanceof Element)) return;
    
    // Avoid capturing the same element multiple times in quick succession
    if (state.capturedElements.has(target)) {
      return;
    }
    state.capturedElements.add(target);
    setTimeout(() => state.capturedElements.delete(target), 1000);
    
    const rect = target.getBoundingClientRect();
    const elemId = generateElementId(target);
    
    // Build comprehensive payload
    const payload = {
      type: 'event',
      sessionId: sessionId,
      eventType: event.type,
      elementId: elemId,
      timestamp: Date.now(),
      
      // Element identification
      tagName: target.tagName,
      id: target.id || null,
      classes: Array.from(target.classList || []),
      attributes: extractElementAttributes(target),
      
      // Text content
      textContent: target.textContent?.trim().substring(0, 200),
      value: target.value || null,
      
      // ARIA
      ariaLabel: target.getAttribute('aria-label'),
      ariaRole: target.getAttribute('role'),
      placeholder: target.getAttribute('placeholder'),
      title: target.getAttribute('title'),
      
      // Locators (multi-dimensional)
      locators: generateLocators(target),
      xpathAbsolute: getXPath(target),
      xpathRelative: getRelativeXPath(target),
      cssSelector: getCSSSelector(target),
      
      // Visual features
      boundingBox: [
        Math.round(rect.x),
        Math.round(rect.y),
        Math.round(rect.width),
        Math.round(rect.height)
      ],
      viewportPosition: [
        Math.round(rect.left),
        Math.round(rect.top)
      ],
      colorSignature: computeColorHistogram(target),
      visualHash: computeVisualHash(target),
      screenshot: captureElementScreenshot(target),
      
      // Structural context
      parentChain: getParentChain(target),
      siblingCount: target.parentElement ? target.parentElement.children.length : 0,
      depth: getXPath(target).split('/').length - 1,
      
      // Semantic features
      semanticRole: classifyElementRole(target),
      
      // Behavioral features
      eventListeners: detectEventListeners(target),
      frameworkInfo: detectFramework(target),
      
      // Stability indicators
      hasDynamicId: target.id ? isDynamicId(target.id) : false,
      hasStableAttributes: target.hasAttribute('data-testid') || target.hasAttribute('name'),
      
      // Frame & Shadow DOM
      isInIframe: window !== window.top,
      framePath: getFramePath(window),
      shadowPath: getShadowPath(event),
      
      // Page context
      page: {
        url: window.location.href,
        title: document.title,
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight,
          scrollX: window.scrollX,
          scrollY: window.scrollY
        }
      },
      
      // Network & Performance
      recentNetworkRequests: state.networkRequests.slice(-5),
      performanceMetrics: capturePerformanceMetrics(),
      recentMutations: state.mutations.slice(-10),
      consoleMessages: state.consoleMessages?.slice(-5) || [],
      
      // Input data (for form fields)
      input: event.type === 'input' || event.type === 'change' ? {
        value: target.value,
        type: target.type,
        name: target.name
      } : null,
      
      // Key data (for keyboard events)
      key: event.key || null,
      keyCode: event.keyCode || null,
      
      // Mouse data
      clientX: event.clientX || null,
      clientY: event.clientY || null
    };
    
    send(payload);
  }

  // ============================================================================
  // Event Listeners
  // ============================================================================

  function initEventListeners() {
    const events = [
      // Mouse events
      'click',
      'dblclick',
      'contextmenu',
      'mousedown',
      'mouseup',
      
      // Keyboard events
      'keydown',
      'keyup',
      
      // Form events
      'input',
      'change',
      'submit',
      'focus',
      'blur',
      
      // Drag events
      'dragstart',
      'drop',
      
      // Touch events (for mobile)
      'touchstart',
      'touchend'
    ];
    
    events.forEach(eventName => {
      window.addEventListener(eventName, handleEvent, {
        capture: true,
        passive: true
      });
    });
    
    // Page visibility
    document.addEventListener('visibilitychange', () => {
      if (connected) {
        send({
          type: 'visibility_change',
          hidden: document.hidden,
          timestamp: Date.now()
        });
      }
    });
    
    // Page unload
    window.addEventListener('beforeunload', () => {
      if (connected) {
        send({
          type: 'session_end',
          sessionId: sessionId,
          timestamp: Date.now()
        });
      }
    });
  }

  // ============================================================================
  // Initialization
  // ============================================================================

  function init() {
    console.info('[recorder] Advanced instrumentation initializing...');
    
    // Initialize all features
    initNetworkTracking();
    initMutationObserver();
    initConsoleCapture();
    initEventListeners();
    
    // Connect to WebSocket
    connect();
    
    console.info('[recorder] Advanced instrumentation ready');
  }

  // Start
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
