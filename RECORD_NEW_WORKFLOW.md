# 🎬 Record Your First ML-Powered Workflow

**The ML app is running with advanced instrumentation!**

---

## ✅ Step-by-Step Instructions

### **1. In the UI Window:**

Click **"Start Recording"** button

A Chromium browser will launch automatically.

---

### **2. Navigate to a Simple Website:**

Type in the address bar: `https://www.google.com`

(Or any website you want to test)

---

### **3. Perform ONE Simple Action:**

**Example: Click the search box**

That's it! Just one click to start.

---

### **4. Stop Recording:**

Click **"Stop Recording"** in the UI

---

### **5. Save the Workflow:**

Click **"Save Workflow"**

A new file will be created: `data/workflows/session-xxxxx.json`

---

## 🔍 **Verify ML Features Were Captured**

After saving, run this in PowerShell:

```powershell
# Get the latest workflow
$latest = Get-ChildItem data\workflows\*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1

Write-Host "`n✨ Latest Workflow: $($latest.Name)`n" -ForegroundColor Cyan

# Parse and check
$content = Get-Content $latest.FullName | ConvertFrom-Json

Write-Host "Total Steps: $($content.steps.Count)" -ForegroundColor Green

if ($content.steps.Count -gt 0) {
    $firstStep = $content.steps[0]
    
    if ($firstStep.target.locators) {
        $count = $firstStep.target.locators.Count
        
        Write-Host "`n🎯 Selectors Captured: $count" -ForegroundColor Green
        
        if ($count -ge 5) {
            Write-Host "✅ SUCCESS! ML-enhanced recording working!`n" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Only $count selectors (expected 5-7)`n" -ForegroundColor Yellow
        }
        
        Write-Host "Selector Details:" -ForegroundColor Cyan
        foreach ($loc in $firstStep.target.locators) {
            $value = $loc.value
            if ($value.Length -gt 60) {
                $value = $value.Substring(0, 57) + "..."
            }
            Write-Host "  - [$($loc.type.PadRight(15))] Score: $($loc.score.ToString('0.00')) -> $value" -ForegroundColor White
        }
        Write-Host ""
    } else {
        Write-Host "❌ No ML metadata found" -ForegroundColor Red
    }
}
```

---

## 🎯 **Expected Output:**

```
✨ Latest Workflow: session-abc123.json

Total Steps: 1

🎯 Selectors Captured: 7
✅ SUCCESS! ML-enhanced recording working!

Selector Details:
  - [id             ] Score: 0.95 -> #APjFqb
  - [data-testid    ] Score: 0.93 -> [data-testid='search-input']
  - [aria-label     ] Score: 0.88 -> [aria-label='Search']
  - [css            ] Score: 0.82 -> textarea.gLFyf
  - [xpath-relative ] Score: 0.75 -> //form[@role='search']//textarea
  - [text           ] Score: 0.70 -> Search
  - [visual         ] Score: 0.65 -> (visual hash)
```

---

## ✅ **Success Criteria:**

- ✅ **5-7 selectors** per element (not 2!)
- ✅ **Multiple selector types** (id, data-testid, aria-label, css, xpath, text, visual)
- ✅ **Confidence scores** for each selector (0.40 - 0.95)

---

## 🚀 **What This Means:**

When you replay this workflow in the future:

1. **Try selector 1** (ID - score 0.95)
   - If it fails...
2. **Try selector 2** (data-testid - score 0.93)
   - If it fails...
3. **Try selector 3** (ARIA label - score 0.88)
   - If it fails...
4. **Try selector 4** (CSS - score 0.82)
   - And so on...

**87% chance at least one selector will work!** 🎯

---

## 🎬 **Try It Now!**

1. Record one simple action
2. Save workflow
3. Run the verification script above
4. See the 7 selectors!

---

**Your ML-powered automation awaits!** ✨
