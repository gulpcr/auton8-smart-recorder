"""
Advanced Playwright Recorder - FIXED VERSION

Fixed threading issues and navigation errors.
"""

import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext


class AdvancedRecorder:
    """Advanced recorder - fixed for sync Playwright."""
    
    def __init__(self):
        self.actions = []
        self.network_logs = []
        self.screenshots = []
        self.assertions = []
        self.start_url = None
        self.recording = False
        self._page = None
        
    def start(self, url: str, headless: bool = False, record_network: bool = True):
        """Start recording session."""
        self.start_url = url
        self.recording = True
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context()
            
            # Enable network logging if requested
            if record_network:
                self._setup_network_logging(context)
            
            page = context.new_page()
            self._page = page
            
            # Set up page listeners
            self._setup_page_listeners(page)
            
            print("\n" + "="*70)
            print("🎬 RECORDING STARTED")
            print("="*70)
            print(f"📍 URL: {url}")
            print("\n📝 Instructions:")
            print("   - Interact with the page normally")
            print("   - Right-click to capture screenshot")
            print("   - Close browser window to stop recording")
            print("="*70 + "\n")
            
            # Navigate to start
            page.goto(url)
            self._add_action('navigate', {'url': url})
            
            # Inject recorder after page loads
            self._inject_recorder(page)
            
            # Keep browser open until user closes it
            try:
                # Instead of threading, we use a simple event loop
                while self.recording:
                    # Check for recorded actions periodically
                    try:
                        self._poll_actions(page)
                    except Exception as e:
                        # Page might be navigating, that's ok
                        pass
                    
                    # Small delay to prevent CPU spinning
                    page.wait_for_timeout(200)
                    
            except Exception as e:
                # User closed browser
                self.recording = False
            
            context.close()
            browser.close()
        
        print("\n✅ Recording stopped!")
        self._print_summary()
    
    def _setup_network_logging(self, context: BrowserContext):
        """Set up network request/response logging."""
        
        def on_request(request):
            if request.resource_type in ['xhr', 'fetch']:
                self.network_logs.append({
                    'type': 'request',
                    'method': request.method,
                    'url': request.url,
                    'timestamp': datetime.now().isoformat()
                })
        
        def on_response(response):
            if response.request.resource_type in ['xhr', 'fetch']:
                self.network_logs.append({
                    'type': 'response',
                    'status': response.status,
                    'url': response.url,
                    'timestamp': datetime.now().isoformat()
                })
                print(f"   📡 API: {response.status} {response.url}")
        
        context.on("request", on_request)
        context.on("response", on_response)
    
    def _setup_page_listeners(self, page: Page):
        """Set up page event listeners."""
        
        def on_navigate(frame):
            """Handle navigation."""
            if frame.url and frame.url != self.start_url:
                self._add_action('navigate', {'url': frame.url})
                # Re-inject recorder after navigation
                try:
                    page.wait_for_load_state('domcontentloaded', timeout=3000)
                    self._inject_recorder(page)
                except:
                    pass
        
        def on_dialog(dialog):
            """Handle dialogs."""
            self._add_action('dialog', {
                'type': dialog.type,
                'message': dialog.message
            })
            dialog.accept()
        
        def on_console(msg):
            """Handle console messages."""
            if msg.type == 'error':
                print(f"   ❌ Console Error: {msg.text}")
        
        def on_close():
            """Handle page close."""
            self.recording = False
        
        page.on("framenavigated", on_navigate)
        page.on("dialog", on_dialog)
        page.on("console", on_console)
        page.on("close", on_close)
    
    def _inject_recorder(self, page: Page):
        """Inject recording JavaScript into page."""
        try:
            page.evaluate("""
                // Only inject if not already present
                if (window.__recorderInjected) return;
                window.__recorderInjected = true;
                
                // Storage for recorded actions
                window.__recordedActions = [];
                
                // Debounce helper
                function debounce(func, wait) {
                    let timeout;
                    return function executedFunction(...args) {
                        const later = () => {
                            clearTimeout(timeout);
                            func(...args);
                        };
                        clearTimeout(timeout);
                        timeout = setTimeout(later, wait);
                    };
                }
                
                // Smart selector generator
                function getSmartSelector(el) {
                    // Priority: data-testid > id > name > aria-label > role+text > text > CSS
                    
                    if (el.getAttribute('data-testid')) {
                        return '[data-testid="' + el.getAttribute('data-testid') + '"]';
                    }
                    
                    if (el.id) {
                        return '#' + el.id;
                    }
                    
                    if (el.name) {
                        return '[name="' + el.name + '"]';
                    }
                    
                    const ariaLabel = el.getAttribute('aria-label');
                    if (ariaLabel) {
                        return '[aria-label="' + ariaLabel + '"]';
                    }
                    
                    const role = el.getAttribute('role');
                    if (role) {
                        const text = el.innerText?.trim().substring(0, 30);
                        if (text) {
                            return 'role=' + role + '[name="' + text + '"]';
                        }
                    }
                    
                    // For buttons/links with text
                    if ((el.tagName === 'BUTTON' || el.tagName === 'A') && el.innerText) {
                        const text = el.innerText.trim();
                        if (text.length < 50 && text.length > 0) {
                            return 'text=' + text;
                        }
                    }
                    
                    // Fallback to CSS
                    return getCssSelector(el);
                }
                
                function getCssSelector(el) {
                    if (!(el instanceof Element)) return '';
                    
                    const path = [];
                    let current = el;
                    
                    while (current && current.nodeType === Node.ELEMENT_NODE) {
                        let selector = current.nodeName.toLowerCase();
                        
                        if (current.className && typeof current.className === 'string') {
                            const classes = current.className.trim().split(/\\s+/)
                                .filter(c => c && !c.match(/active|hover|focus|selected/));
                            if (classes.length > 0) {
                                selector += '.' + classes.slice(0, 2).join('.');
                            }
                        }
                        
                        path.unshift(selector);
                        
                        if (path.length > 2) break;
                        current = current.parentNode;
                    }
                    
                    return path.join(' > ');
                }
                
                // Record action helper
                function recordAction(action) {
                    window.__recordedActions.push({
                        ...action,
                        timestamp: Date.now()
                    });
                }
                
                // Track clicks
                document.addEventListener('click', (e) => {
                    const el = e.target;
                    const selector = getSmartSelector(el);
                    const text = el.innerText?.substring(0, 50) || '';
                    
                    recordAction({
                        type: 'click',
                        selector: selector,
                        text: text,
                        tag: el.tagName
                    });
                }, true);
                
                // Track input (debounced)
                const inputHandlers = new Map();
                document.addEventListener('input', (e) => {
                    const el = e.target;
                    const selector = getSmartSelector(el);
                    
                    // Debounce input events
                    if (!inputHandlers.has(selector)) {
                        inputHandlers.set(selector, debounce(() => {
                            recordAction({
                                type: 'fill',
                                selector: selector,
                                value: el.value,
                                tag: el.tagName
                            });
                        }, 500));
                    }
                    
                    inputHandlers.get(selector)();
                }, true);
                
                // Track checkbox/radio
                document.addEventListener('change', (e) => {
                    const el = e.target;
                    const selector = getSmartSelector(el);
                    
                    if (el.type === 'checkbox' || el.type === 'radio') {
                        recordAction({
                            type: 'check',
                            selector: selector,
                            checked: el.checked,
                            tag: el.tagName
                        });
                    } else if (el.tagName === 'SELECT') {
                        recordAction({
                            type: 'select',
                            selector: selector,
                            value: el.value,
                            text: el.options[el.selectedIndex]?.text || '',
                            tag: el.tagName
                        });
                    }
                }, true);
                
                // Inject floating control panel
                const panel = document.createElement('div');
                panel.innerHTML = `
                    <div style="
                        position: fixed;
                        top: 10px;
                        right: 10px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: #fff;
                        padding: 12px 16px;
                        border-radius: 8px;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        font-size: 13px;
                        z-index: 999999;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                        font-weight: 500;
                        letter-spacing: 0.3px;
                    ">
                        🎬 RECORDING
                    </div>
                `;
                document.body.appendChild(panel);
                
                console.log('✅ Recorder injected successfully');
            """)
        except Exception as e:
            # Injection might fail if page is navigating, that's ok
            pass
    
    def _poll_actions(self, page: Page):
        """Poll page for recorded actions."""
        try:
            actions = page.evaluate("window.__recordedActions || []")
            
            if actions:
                # Process new actions
                for action in actions:
                    self._add_action(action['type'], action)
                
                # Clear processed actions
                page.evaluate("window.__recordedActions = []")
                
        except Exception as e:
            # Page might be navigating, ignore
            pass
    
    def _add_action(self, action_type: str, data: dict):
        """Add action to recording."""
        action = {
            'type': action_type,
            'timestamp': datetime.now().isoformat(),
            **data
        }
        self.actions.append(action)
        
        # Print feedback
        icons = {
            'click': '🖱️ ',
            'fill': '⌨️ ',
            'navigate': '🌐',
            'check': '☑️ ',
            'select': '📋',
            'dialog': '💬'
        }
        icon = icons.get(action_type, '📝')
        
        if action_type == 'click':
            text = data.get('text', '')[:30]
            selector = data.get('selector', '')[:40]
            display = text if text else selector
            print(f"   {icon} Click: {display}")
        elif action_type == 'fill':
            selector = data.get('selector', '')[:40]
            print(f"   {icon} Fill: {selector}")
        elif action_type == 'navigate':
            print(f"   {icon} Navigate: {data.get('url')}")
        elif action_type == 'check':
            status = 'checked' if data.get('checked') else 'unchecked'
            print(f"   {icon} {status}: {data.get('selector', '')[:40]}")
        elif action_type == 'select':
            print(f"   {icon} Select: {data.get('text', '')[:40]}")
    
    def _print_summary(self):
        """Print recording summary."""
        print(f"\n📊 Summary:")
        print(f"   Actions: {len(self.actions)}")
        print(f"   Network Logs: {len(self.network_logs)}")
    
    def generate_code(self) -> str:
        """Generate Playwright test code."""
        lines = [
            "from playwright.sync_api import sync_playwright, expect",
            "",
            "def test_recorded_flow():",
            "    with sync_playwright() as p:",
            "        browser = p.chromium.launch(headless=False)",
            "        page = browser.new_page()",
            "",
        ]
        
        # Remove duplicate consecutive fills to same element
        processed = []
        i = 0
        while i < len(self.actions):
            action = self.actions[i]
            
            # For fills, check if there are more fills to same selector
            if action['type'] == 'fill':
                selector = action.get('selector', '')
                # Look ahead for more fills to same element
                j = i + 1
                while j < len(self.actions):
                    if self.actions[j]['type'] == 'fill' and \
                       self.actions[j].get('selector') == selector:
                        i = j  # Skip to the last fill
                    else:
                        break
                    j += 1
            
            processed.append(self.actions[i])
            i += 1
        
        # Generate code from processed actions
        for action in processed:
            atype = action['type']
            
            if atype == 'navigate':
                lines.append(f'        page.goto("{action["url"]}")')
                
            elif atype == 'click':
                selector = action['selector']
                if selector.startswith('text='):
                    text = selector[5:].replace('"', '\\"')
                    lines.append(f'        page.get_by_text("{text}").click()')
                elif selector.startswith('role='):
                    lines.append(f'        page.locator("{selector}").click()')
                else:
                    selector = selector.replace('"', '\\"')
                    lines.append(f'        page.locator("{selector}").click()')
                    
            elif atype == 'fill':
                selector = action['selector'].replace('"', '\\"')
                value = action.get('value', '').replace('"', '\\"')
                lines.append(f'        page.locator("{selector}").fill("{value}")')
                
            elif atype == 'check':
                selector = action['selector'].replace('"', '\\"')
                if action.get('checked', True):
                    lines.append(f'        page.locator("{selector}").check()')
                else:
                    lines.append(f'        page.locator("{selector}").uncheck()')
                    
            elif atype == 'select':
                selector = action['selector'].replace('"', '\\"')
                value = action.get('value', '').replace('"', '\\"')
                lines.append(f'        page.locator("{selector}").select_option("{value}")')
        
        lines.extend([
            "",
            "        # Wait a bit to see the result",
            "        page.wait_for_timeout(2000)",
            "",
            "        browser.close()",
            "",
            "if __name__ == '__main__':",
            "    test_recorded_flow()",
        ])
        
        return "\n".join(lines)
    
    def save(self, filename: str = "recorded_test.py"):
        """Save generated code."""
        code = self.generate_code()
        Path(filename).write_text(code)
        print(f"\n💾 Test saved: {filename}")
        
        # Save raw JSON
        json_file = filename.replace('.py', '.json')
        Path(json_file).write_text(json.dumps({
            'url': self.start_url,
            'actions': self.actions,
            'network_logs': self.network_logs,
            'recorded_at': datetime.now().isoformat()
        }, indent=2))
        print(f"📄 Raw data saved: {json_file}")


if __name__ == "__main__":
    print("🎬 Playwright Recorder - Fixed Version")
    print("="*70)
    
    recorder = AdvancedRecorder()
    
    url = input("Enter URL to record (default: https://example.com): ").strip()
    if not url:
        url = "https://example.com"
    
    try:
        recorder.start(url, headless=False, record_network=True)
        recorder.save("recorded_test.py")
        
        print("\n" + "="*70)
        print("📝 Generated Code Preview:")
        print("="*70)
        print(recorder.generate_code())
        print("\n✨ Done! Run with: python recorded_test.py")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Recording interrupted by user")
        recorder.recording = False
        if recorder.actions:
            recorder.save("recorded_test_partial.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()