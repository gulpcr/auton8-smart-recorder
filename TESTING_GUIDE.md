# Testing Guide - Enhanced UI

## 🎯 Purpose
Test the new Test Library UI and New Test Wizard with your existing ML-powered recorder.

---

## 📋 Pre-Test Checklist

### ✅ Environment Setup
```powershell
# 1. Ensure you're in the virtual environment
cd F:\auton8\recorder
.\.venv\Scripts\activate

# 2. Verify all dependencies are installed
pip list | Select-String "PySide6|pydantic"

# 3. Check that you have existing workflow files
ls data\workflows\*.json
```

**Expected**: You should see your existing workflow JSON files (6-7 files from previous recordings)

---

## 🚀 Test Plan

### **Test 1: Launch Enhanced UI**

#### Steps:
```powershell
# Run the enhanced app
$env:PYTHONIOENCODING="utf-8"; python -m recorder.app_enhanced
```

#### Expected Results:
✅ Application window opens (1400x900)  
✅ Window title: "Test Recorder - Professional Edition"  
✅ Three tabs visible: 📚 Library, ⚫ Record, ▶️ Replay  
✅ "ML Active" indicator shown (green dot)  
✅ Status message: "Ready - Test Library loaded"  

#### What to Look For:
- Clean, modern dark UI with rounded corners
- No error messages in console
- Smooth window rendering

---

### **Test 2: Test Library - Load Existing Workflows**

#### Steps:
1. Ensure you're on the **Library tab** (should be default)
2. Observe the test cards displayed

#### Expected Results:
✅ Your existing 6-7 workflows appear as cards  
✅ Each card shows:
   - Workflow filename or name
   - Status indicator (colored dot - should be "draft" = gray)
   - Step count (e.g., "0 steps" for empty ones)
   - Base URL (if available)
   - Updated time
   - Quick action buttons (▶ Run, ✎ Edit)

#### What to Look For:
- All your existing workflows are visible
- No "No tests yet" empty state (unless you delete all workflows first)
- Cards are in a grid layout
- Hover effects work (card border turns red)

#### Screenshot:
Take a screenshot of the Library view for reference.

---

### **Test 3: Search and Filter**

#### Steps:
1. In the search bar, type "session"
2. Observe filtering behavior
3. Clear search (click X button)
4. Click **Draft** filter chip
5. Click **Draft** again to deselect

#### Expected Results:
✅ Typing "session" filters to matching workflows  
✅ Clearing search shows all workflows again  
✅ Clicking Draft chip highlights it and filters  
✅ Clicking again deselects and shows all  
✅ Filter chip shows count badge (e.g., "6" for 6 draft workflows)

#### What to Look For:
- Instant filtering (no lag)
- Smooth chip animations
- Accurate count badges

---

### **Test 4: Sort Workflows**

#### Steps:
1. Click the sort dropdown (default: "Recently Updated")
2. Select "Name A-Z"
3. Observe reordering
4. Select "Name Z-A"
5. Select "Recently Updated" again

#### Expected Results:
✅ Workflows reorder immediately  
✅ Alphabetical sorting works correctly  
✅ Most recent workflows appear first when sorted by date

---

### **Test 5: Context Menu Actions**

#### Steps:
1. Click the **⋮** (three dots) button on any workflow card
2. Observe the context menu

#### Expected Results:
✅ Menu appears with options:
   - Duplicate
   - Export Package
   - Upload to Portal
   - Delete

✅ Selecting an option shows "coming soon" message (these aren't implemented yet)

---

### **Test 6: New Test Wizard - Step 1 (Name)**

#### Steps:
1. Click the big **"+ Record New Test"** button in Library (if no tests)
   OR click **"✨ Create Test with Wizard"** in Record tab
2. New Test Wizard dialog opens

#### Step 1: Enter Name
- Type: **"Test Google Search"**
- Observe validation
- Click **Next**

#### Expected Results:
✅ Wizard opens as modal dialog  
✅ Step indicator shows: 1 (active), 2 (inactive), 3 (inactive)  
✅ Name input has focus  
✅ Suggestions appear below  
✅ Clicking a suggestion fills the input  
✅ "Next" button enabled when name is entered  
✅ Moves to Step 2

#### What to Look For:
- Smooth step transition
- Visual stepper updates (step 1 gets checkmark ✓, step 2 becomes active)

---

### **Test 7: New Test Wizard - Step 2 (URL)**

#### Step 2: Enter URL
- Type: **"https://google.com"**
- Observe recent URLs list
- Click **Next**

#### Expected Results:
✅ URL input has focus  
✅ Recent URLs shown below (google.com, github.com, stackoverflow.com)  
✅ Clicking a recent URL fills the input  
✅ Validation: entering invalid URL shows warning  
✅ "Next" button enabled when valid URL entered  
✅ "Back" button visible and functional  
✅ Moves to Step 3

---

### **Test 8: New Test Wizard - Step 3 (Confirmation)**

#### Step 3: Start Recording
- Review the summary
- Click **"● Start Recording"**

#### Expected Results:
✅ Summary shows:
   - Test Name: "Test Google Search"
   - Starting URL: "https://google.com"
✅ "Start Recording" button is large and prominent  
✅ Clicking it:
   - Wizard closes
   - Switches to **Record tab**
   - Browser opens with google.com
   - Recording indicator shows "🔴 Recording Active"
   - Status message: "Recording browser opened: https://google.com"

#### What to Look For:
- Browser opens with ML instrumentation (check console for ML logs)
- No errors in Python console

---

### **Test 9: Record Steps with ML**

#### Steps:
1. In the opened Google browser:
   - Click the search input box
   - Type "test automation"
   - Click the "Google Search" button
2. Observe the **Recorded Steps** panel (left side)

#### Expected Results:
✅ Steps appear in real-time in the left panel  
✅ Each step shows:
   - Icon (● for click, ✎ for input)
   - Action type (Click, Input, etc.)
   - Target element description
✅ Steps animate in smoothly  
✅ Step count updates (e.g., "3 steps")  
✅ Console shows: "Captured step {id} ({type}) with 7 selectors" (or similar number)

#### What to Look For:
- No delays in step capture
- Accurate action descriptions
- ML selector generation logs

---

### **Test 10: Save Workflow**

#### Steps:
1. Click **"Stop"** button to stop recording
2. Click **"💾 Save"** button

#### Expected Results:
✅ Recording stops (browser stays open)  
✅ Status message: "Saved workflow to {path}"  
✅ Workflow file created in `data/workflows/`  
✅ Save button becomes disabled until new changes

#### Verification:
```powershell
# Check the saved file
$latest = Get-ChildItem data\workflows\*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content $latest.FullName | ConvertFrom-Json | Select-Object -ExpandProperty metadata
```

**Expected**: JSON with metadata containing:
- `name`: "Test Google Search"
- `status`: "draft"
- `version`: 2
- `baseUrl`: "https://google.com"
- `createdAt`, `updatedAt` timestamps

---

### **Test 11: View Saved Test in Library**

#### Steps:
1. Switch to **📚 Library tab**
2. Click the **🔄** refresh button (if needed)
3. Find your new test "Test Google Search"

#### Expected Results:
✅ New test appears in the library  
✅ Card shows:
   - Name: "Test Google Search"
   - Status: draft (gray dot)
   - Step count: 3 steps (or however many you recorded)
   - Base URL: https://google.com
   - "Today" or recent time

---

### **Test 12: Edit Existing Test**

#### Steps:
1. In Library, click the **✎ Edit** button on "Test Google Search"

#### Expected Results:
✅ Switches to **Record tab**  
✅ Steps panel populates with the 3 recorded steps  
✅ URL input shows "https://google.com"  
✅ Status message: "Loaded: Test Google Search"

#### What to Look For:
- All steps loaded correctly
- No duplicates

---

### **Test 13: Replay Test**

#### Steps:
1. In Library, click the **▶ Run** button on "Test Google Search"
   OR switch to **▶️ Replay tab** and double-click the workflow

#### Expected Results:
✅ Switches to Replay tab  
✅ Workflow selected (red border)  
✅ Status indicator: "🔄 Replaying..."  
✅ Browser opens and executes steps automatically  
✅ Console shows step execution logs  
✅ Status message: "Replay started..." then "Replay completed successfully ✓"

#### What to Look For:
- Smooth automation
- ML selector healing in action (check console for "Used locator: ..." messages)
- No errors during replay

---

### **Test 14: Delete Workflow**

#### Steps:
1. In Library, click **⋮** menu on a test
2. Select **Delete**
3. Confirmation dialog appears
4. Click **Delete** to confirm

#### Expected Results:
✅ Confirmation dialog shows warning  
✅ "⚠️ Are you sure..." message displayed  
✅ Clicking Delete:
   - Dialog closes
   - Test card disappears from library
   - Status message: "Workflow deleted"
✅ Clicking Cancel closes dialog without deleting

#### Verification:
```powershell
# Check that file is deleted
ls data\workflows\ | Measure-Object
```

---

### **Test 15: Backward Compatibility - Load Old Workflows**

#### Steps:
1. Verify your old workflow files (created before this upgrade) load correctly
2. Check that they display in the library
3. Edit one and save it

#### Expected Results:
✅ Old workflows (v1 format) load without errors  
✅ Console shows: "Migrating workflow from v1 to v2"  
✅ After saving, file is upgraded to v2 format  
✅ Old data preserved (steps, locators, etc.)

#### Verification:
```powershell
# Check file format after opening and saving
$file = Get-Content "data\workflows\<old-filename>.json" | ConvertFrom-Json
$file.metadata.version  # Should show: 2
```

---

## 🐛 Common Issues & Solutions

### Issue 1: "No module named 'recorder.app_enhanced'"
**Solution**: Make sure you're in the project root directory:
```powershell
cd F:\auton8\recorder
python -m recorder.app_enhanced
```

### Issue 2: UI doesn't open
**Solution**: Check console for QML errors. Ensure `ui/main_enhanced.qml` exists:
```powershell
ls ui\main_enhanced.qml
```

### Issue 3: Workflows don't appear in Library
**Solution**: Check data directory:
```powershell
ls data\workflows\*.json
```
If empty, record a new test first.

### Issue 4: Browser doesn't open when recording
**Solution**: 
- Check if browser is already running (close it)
- Check console for browser launch errors
- Verify `instrumentation/injected_advanced.js` exists

### Issue 5: Steps not captured during recording
**Solution**:
- Check WebSocket connection (console should show "server listening on 127.0.0.1:8765")
- Try clicking/typing slower
- Check browser console for JavaScript errors

---

## ✅ Success Criteria

Mark these as you complete them:

- [ ] **Application launches** without errors
- [ ] **Existing workflows load** in Library with metadata
- [ ] **Search and filter** work smoothly
- [ ] **Sort** reorders workflows correctly
- [ ] **New Test Wizard** completes all 3 steps
- [ ] **Recording captures steps** with ML selectors
- [ ] **Save workflow** creates proper v2 format file
- [ ] **Edit workflow** loads steps correctly
- [ ] **Replay** executes workflow successfully
- [ ] **Delete** removes workflow with confirmation
- [ ] **Backward compatibility** - old workflows migrate automatically
- [ ] **No console errors** during normal operation
- [ ] **UI is responsive** and smooth

---

## 📊 Test Report Template

```markdown
## Test Results - [Date]

### Environment
- OS: Windows 10/11
- Python: 3.13
- Virtual Env: Active ✓
- Existing Workflows: 6 files

### Tests Passed
1. ✅ Launch Enhanced UI
2. ✅ Load Existing Workflows
3. ✅ Search and Filter
4. ... (continue)

### Tests Failed
- ❌ Test X: [Description of failure]
  - Error: [Error message]
  - Steps to reproduce: ...

### Issues Found
1. [Issue description]
   - Severity: High/Medium/Low
   - Steps to reproduce: ...

### Screenshots
- Library view: [screenshot]
- Wizard: [screenshot]
- Recording: [screenshot]

### Overall Assessment
[Pass/Fail] - [Summary]
```

---

## 🔍 Advanced Testing (Optional)

### Performance Test
- Load 100+ workflows (copy existing files)
- Test search/filter performance
- Check memory usage

### Stress Test
- Record 50+ steps in one workflow
- Save and reload
- Test replay

### Edge Cases
- Empty workflow (0 steps)
- Very long test names
- Special characters in names
- Invalid URLs in wizard

---

## 📞 Next Steps After Testing

1. **If all tests pass**: 
   - Document any minor issues
   - Consider moving to Phase 3 (3-panel recording UX)

2. **If critical failures**:
   - Report errors with console logs
   - Share screenshots
   - Provide workflow JSON files for debugging

3. **Feature requests**:
   - Note any UX improvements
   - Suggest additional features
   - Prioritize next enhancements

---

**Ready to test? Start with Test 1!** 🚀

Let me know if you encounter any issues or have questions!
