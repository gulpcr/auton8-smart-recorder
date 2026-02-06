# Quick Start - Enhanced UI

## 🚀 Fastest Way to Test

### **Option 1: Double-Click (Windows)**
Simply double-click `run_enhanced.bat` in File Explorer.

### **Option 2: PowerShell Command**
```powershell
$env:PYTHONIOENCODING="utf-8"; python -m recorder.app_enhanced
```

---

## ✨ What You'll See

### **Professional UI with 3 Tabs:**

1. **📚 Library Tab** (Default)
   - Browse all your recorded tests
   - Search by name, tags, or URL
   - Filter by status (Draft/Ready/Flaky/Broken)
   - Sort by date, name, or step count
   - Quick actions: Run, Edit, Delete

2. **⚫ Record Tab**
   - Create new tests with wizard (✨ button)
   - Or quick record (enter URL → Record)
   - Live step capture with ML selectors
   - Animated step list
   - Save/Clear buttons

3. **▶️ Replay Tab**
   - Select workflow from list
   - Click "Start Replay"
   - Watch automated execution
   - Intelligent selector healing

---

## 🎯 Quick Test Flow

### **1. First Time?** Try the Wizard
- Go to Library tab
- Click **"+ Record New Test"** (or ✨ in Record tab)
- Follow 3 steps:
  1. Enter test name (e.g., "Google Search")
  2. Enter URL (e.g., "https://google.com")
  3. Click "Start Recording"

### **2. Record Steps**
- Browser opens automatically
- Click search box → Steps captured! ✅
- Type something → Another step! ✅
- Click search button → Step captured! ✅
- Click **Stop** → Recording ends

### **3. Save**
- Click **💾 Save** button
- Workflow saved with ML metadata ✅

### **4. View in Library**
- Switch to **📚 Library** tab
- See your new test card
- Status: Draft (gray dot)
- Shows: 3 steps, google.com, "Today"

### **5. Run Again**
- Click **▶ Run** on the test card
- Or go to **▶️ Replay** tab and double-click
- Watch it replay automatically! 🎉

---

## 🎨 Key Features to Notice

### **Modern UI**
- Dark theme with accent colors
- Smooth animations
- Hover effects
- Rounded corners
- Professional feel

### **ML Integration**
- "ML Active" indicator (green dot in header)
- 7+ selector strategies per element
- Intelligent healing during replay
- Console shows ML logs

### **Test Management**
- Search: Type to filter instantly
- Filter: Click status chips
- Sort: Dropdown with 4 options
- Actions: Run, Edit, Delete with confirmation

### **Wizard Flow**
- 3-step guided setup
- Visual progress indicator
- Validation at each step
- Recent URLs suggestions

### **Backward Compatible**
- Your old tests load automatically
- Migrated to v2 format transparently
- All existing data preserved

---

## 📝 What Gets Saved

Each test saves with:
```json
{
  "metadata": {
    "name": "Test Google Search",
    "status": "draft",
    "version": 2,
    "baseUrl": "https://google.com",
    "createdAt": "2026-01-22T...",
    "updatedAt": "2026-01-22T...",
    "tags": [],
    "stepCount": 3
  },
  "steps": [
    {
      "type": "click",
      "target": {
        "locators": [
          {"type": "id", "value": "...", "score": 0.95},
          {"type": "css", "value": "...", "score": 0.90},
          {"type": "xpath", "value": "...", "score": 0.85},
          // ... up to 7 selector strategies
        ]
      }
    }
  ]
}
```

---

## 🔍 Where to Look

### **During Recording:**
- **Left panel**: Live step list
- **Right panel**: Instructions
- **Top**: Recording status (🔴 Recording Active)
- **Console**: ML selector generation logs

### **In Library:**
- **Search bar**: Top of page
- **Filter chips**: Draft, Ready, Flaky, Broken
- **Sort dropdown**: Top right
- **Test cards**: Grid layout
- **⋮ menu**: More actions per test

### **During Replay:**
- **Left**: Workflow list
- **Right**: Replay controls
- **Status**: 🔄 Replaying...
- **Console**: Step execution logs

---

## ⚡ Keyboard Shortcuts (Future)
*Coming in next update:*
- `Ctrl+N` - New test wizard
- `Ctrl+R` - Start/stop recording
- `Ctrl+S` - Save workflow
- `F5` - Refresh library

---

## ❓ Troubleshooting

### App doesn't start?
```powershell
# Check virtual environment
.\.venv\Scripts\activate
python --version  # Should be 3.13

# Check dependencies
pip list | Select-String "PySide6"
```

### No workflows showing?
```powershell
# Check data folder
ls data\workflows\*.json
```

### Browser doesn't open?
- Close any existing browser windows
- Check console for errors
- Try restarting the app

### Steps not capturing?
- Check console: "server listening on 127.0.0.1:8765"
- Click/type slower
- Check browser console (F12)

---

## 📚 Full Documentation

- **Detailed Testing**: See `TESTING_GUIDE.md`
- **Architecture**: See `REPO_FINDINGS.md`
- **Roadmap**: See `IMPLEMENTATION_PLAN.md`
- **Progress**: See `PROGRESS_REPORT.md`

---

## 🎉 Next Features (Coming Soon)

- **3-panel recording** with Inspector
- **Step editor** with drag-drop
- **Timeline replay** view with screenshots
- **Export packages** as ZIP
- **Portal upload** integration
- **Loop/condition** blocks
- **Variables** and assertions

---

**Have fun testing!** 🚀

Report issues or suggestions, and I'll help you fix them immediately.
