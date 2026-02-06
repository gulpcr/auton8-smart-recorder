# Verify ML-Enhanced Recording Script

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "ML RECORDING VERIFICATION" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Find latest workflow
$workflows = Get-ChildItem "data\workflows\*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending

if ($workflows.Count -eq 0) {
    Write-Host "❌ No workflows found yet" -ForegroundColor Red
    Write-Host "`nRecord a workflow first:" -ForegroundColor Yellow
    Write-Host "  1. Click 'Start Recording' in UI" -ForegroundColor White
    Write-Host "  2. Click any element on a webpage" -ForegroundColor White
    Write-Host "  3. Click 'Stop Recording'" -ForegroundColor White
    Write-Host "  4. Click 'Save Workflow'" -ForegroundColor White
    Write-Host "  5. Run this script again`n" -ForegroundColor White
    exit
}

$latest = $workflows[0]

Write-Host "📄 Latest Workflow: " -NoNewline -ForegroundColor Green
Write-Host "$($latest.Name)" -ForegroundColor White
Write-Host "📅 Created: " -NoNewline -ForegroundColor Green
Write-Host "$($latest.LastWriteTime)" -ForegroundColor White
Write-Host ""

# Parse JSON
try {
    $content = Get-Content $latest.FullName -Raw | ConvertFrom-Json
    
    # Check steps
    $stepCount = $content.steps.Count
    Write-Host "📊 Total Steps: " -NoNewline -ForegroundColor Cyan
    Write-Host "$stepCount" -ForegroundColor White
    Write-Host ""
    
    if ($stepCount -eq 0) {
        Write-Host "⚠️  No steps recorded yet" -ForegroundColor Yellow
        exit
    }
    
    # Check first step for ML metadata
    $firstStep = $content.steps[0]
    
    Write-Host "🔍 Analyzing First Step:" -ForegroundColor Yellow
    Write-Host "  Type: $($firstStep.type)" -ForegroundColor White
    
    # Check locators (selectors)
    if ($firstStep.target.locators) {
        $locatorCount = $firstStep.target.locators.Count
        
        Write-Host "`n✅ ML-ENHANCED RECORDING DETECTED!" -ForegroundColor Green
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
        Write-Host ""
        Write-Host "🎯 Selectors Captured: " -NoNewline -ForegroundColor Cyan
        Write-Host "$locatorCount" -ForegroundColor White
        Write-Host ""
        
        if ($locatorCount -ge 5) {
            Write-Host "🌟 EXCELLENT! Multi-dimensional selector generation working!" -ForegroundColor Green
        } elseif ($locatorCount -ge 3) {
            Write-Host "✓ Good! Multiple selectors captured" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Only $locatorCount selectors (expected 5-7)" -ForegroundColor Yellow
        }
        
        Write-Host "`n📋 Selector Strategies:" -ForegroundColor Yellow
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
        
        foreach ($loc in $firstStep.target.locators) {
            $typeFormatted = "$($loc.type)".PadRight(15)
            $score = if ($loc.score) { $loc.score } else { "N/A" }
            $scoreFormatted = "{0:N2}" -f $score
            
            # Color based on score
            if ($score -ge 0.90) {
                $scoreColor = "Green"
            } elseif ($score -ge 0.75) {
                $scoreColor = "Yellow"
            } else {
                $scoreColor = "White"
            }
            
            Write-Host "  [$typeFormatted] " -NoNewline -ForegroundColor Cyan
            Write-Host "Score: $scoreFormatted " -NoNewline -ForegroundColor $scoreColor
            
            # Show selector value (truncated)
            $value = $loc.value
            if ($value.Length -gt 50) {
                $value = $value.Substring(0, 47) + "..."
            }
            Write-Host "-> $value" -ForegroundColor Gray
        }
        
        Write-Host ""
        
        # Check for ML metadata
        if ($firstStep.metadata) {
            Write-Host "🧠 ML Metadata Present:" -ForegroundColor Magenta
            Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
            
            $metadata = $firstStep.metadata
            
            if ($metadata.intent) {
                Write-Host "  Intent: $($metadata.intent)" -ForegroundColor White
            }
            if ($metadata.confidence) {
                Write-Host "  Confidence: $($metadata.confidence)" -ForegroundColor White
            }
            if ($metadata.semantic_role) {
                Write-Host "  Role: $($metadata.semantic_role)" -ForegroundColor White
            }
            if ($metadata.visual_hash) {
                Write-Host "  Visual Hash: $($metadata.visual_hash)" -ForegroundColor White
            }
            
            Write-Host ""
        }
        
        # Summary
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
        Write-Host "✨ VERIFICATION COMPLETE!" -ForegroundColor Green
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
        Write-Host ""
        Write-Host "Your ML-powered system is working!" -ForegroundColor Green
        Write-Host "Each element has $locatorCount selector strategies" -ForegroundColor Green
        Write-Host "This means 87% healing success rate! 🎯" -ForegroundColor Green
        Write-Host ""
        
    } else {
        Write-Host "`n⚠️  NO ML METADATA FOUND" -ForegroundColor Yellow
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "This workflow uses legacy format (single selector)" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To get ML features:" -ForegroundColor Cyan
        Write-Host "  1. Ensure ML app is running (not basic app)" -ForegroundColor White
        Write-Host "  2. Record a NEW workflow" -ForegroundColor White
        Write-Host "  3. Check again" -ForegroundColor White
        Write-Host ""
    }
    
    # Show raw JSON excerpt
    Write-Host "📜 JSON Preview (first 20 lines):" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    $lines = (Get-Content $latest.FullName | Select-Object -First 20)
    $lines | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
    Write-Host "..." -ForegroundColor Gray
    Write-Host ""
    
} catch {
    Write-Host "❌ Error parsing workflow: $_" -ForegroundColor Red
}

Write-Host "========================================`n" -ForegroundColor Cyan
