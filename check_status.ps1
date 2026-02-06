# Quick Status Check for ML-Powered Automation System

Write-Host "`n" -NoNewline
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "ML-POWERED AUTOMATION - SYSTEM STATUS CHECK" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Check if Python processes are running
Write-Host "🔍 Checking running processes..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    Write-Host "✅ Python processes found: $($pythonProcesses.Count)" -ForegroundColor Green
    
    foreach ($p in $pythonProcesses) {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)").CommandLine
        
        if ($cmd -like "*app_ml_integrated*") {
            Write-Host "  ✅ ML-integrated app is running (PID: $($p.Id))" -ForegroundColor Green
            $mlAppRunning = $true
        } elseif ($cmd -like "*recorder.app*") {
            Write-Host "  ⚠️  Basic app is running (PID: $($p.Id)) - Consider switching to ML app" -ForegroundColor Yellow
        } else {
            Write-Host "  ℹ️  Python process (PID: $($p.Id))" -ForegroundColor White
        }
    }
} else {
    Write-Host "❌ No Python processes running" -ForegroundColor Red
    Write-Host "   Run: $env:PYTHONIOENCODING=`"utf-8`"; python -m recorder.app_ml_integrated" -ForegroundColor Yellow
}

Write-Host ""

# Check workflows
Write-Host "📁 Checking workflows..." -ForegroundColor Yellow
$workflowDir = "data\workflows"

if (Test-Path $workflowDir) {
    $workflows = Get-ChildItem "$workflowDir\*.json"
    
    if ($workflows) {
        Write-Host "✅ Found $($workflows.Count) workflow(s)" -ForegroundColor Green
        
        # Check latest workflow
        $latest = $workflows | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        Write-Host "   Latest: $($latest.Name)" -ForegroundColor White
        Write-Host "   Modified: $($latest.LastWriteTime)" -ForegroundColor White
        
        # Check for ML metadata
        try {
            $content = Get-Content $latest.FullName -Raw | ConvertFrom-Json
            $eventCount = $content.events.Count
            
            if ($eventCount -gt 0) {
                Write-Host "   Events: $eventCount" -ForegroundColor White
                
                $firstEvent = $content.events[0]
                if ($firstEvent.locatorCandidates) {
                    $selectorCount = $firstEvent.locatorCandidates.Count
                    Write-Host "   ✅ ML-Enhanced! $selectorCount selectors per element" -ForegroundColor Green
                } else {
                    Write-Host "   ⚠️  Legacy format (no ML metadata)" -ForegroundColor Yellow
                }
            }
        } catch {
            Write-Host "   ⚠️  Could not parse workflow file" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️  No workflows found yet" -ForegroundColor Yellow
        Write-Host "   Record a workflow to get started!" -ForegroundColor White
    }
} else {
    Write-Host "⚠️  Workflows directory not found" -ForegroundColor Yellow
}

Write-Host ""

# Check screenshots
Write-Host "🖼️  Checking screenshots..." -ForegroundColor Yellow
$screenshotDir = "data\screenshots"

if (Test-Path $screenshotDir) {
    $screenshots = Get-ChildItem "$screenshotDir\*.png"
    if ($screenshots) {
        Write-Host "✅ Found $($screenshots.Count) screenshot(s)" -ForegroundColor Green
    } else {
        Write-Host "⚠️  No screenshots yet" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Screenshots directory not found" -ForegroundColor Yellow
}

Write-Host ""

# Check ML components
Write-Host "🧠 Checking ML components..." -ForegroundColor Yellow

$mlFiles = @(
    "recorder\ml\selector_engine.py",
    "recorder\ml\healing_engine.py",
    "recorder\ml\vision_engine.py",
    "recorder\ml\nlp_engine.py",
    "recorder\ml\rag_engine.py"
)

$allPresent = $true
foreach ($file in $mlFiles) {
    if (Test-Path $file) {
        Write-Host "  ✅ $($file.Split('\')[-1])" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $($file.Split('\')[-1]) missing" -ForegroundColor Red
        $allPresent = $false
    }
}

if ($allPresent) {
    Write-Host "✅ All ML components present!" -ForegroundColor Green
}

Write-Host ""

# Check GPU
Write-Host "🎮 Checking GPU acceleration..." -ForegroundColor Yellow
try {
    $gpuCheck = python -c 'import torch; print(\"CUDA\" if torch.cuda.is_available() else \"CPU\"); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"No GPU\")' 2>$null
    
    if ($gpuCheck) {
        $lines = $gpuCheck -split "`n"
        if ($lines[0] -eq "CUDA") {
            Write-Host "✅ GPU acceleration enabled: $($lines[1])" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Running on CPU (GPU not available)" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "⚠️  Could not check GPU status" -ForegroundColor Yellow
}

Write-Host ""

# Summary
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

if ($mlAppRunning) {
    Write-Host "✅ ML app is running - Ready to record!" -ForegroundColor Green
    Write-Host "   Next: Open UI and click 'Start Recording'" -ForegroundColor White
} else {
    Write-Host "⚠️  ML app not running" -ForegroundColor Yellow
    Write-Host "   Start with: `$env:PYTHONIOENCODING=`"utf-8`"; python -m recorder.app_ml_integrated" -ForegroundColor White
}

Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Cyan
Write-Host "   - START_HERE.md - Step-by-step tutorial" -ForegroundColor White
Write-Host "   - ML_APP_GUIDE.md - Full ML app documentation" -ForegroundColor White
Write-Host "   - ML_FEATURES_GUIDE.md - Feature deep-dive" -ForegroundColor White

Write-Host ""
Write-Host "🎬 Quick Commands:" -ForegroundColor Cyan
Write-Host "   Run demos: `$env:PYTHONIOENCODING=`"utf-8`"; python demo_ml_features.py" -ForegroundColor White
Write-Host "   Test healing: `$env:PYTHONIOENCODING=`"utf-8`"; python test_healing_demo.py" -ForegroundColor White

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
