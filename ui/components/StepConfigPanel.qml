import QtQuick 6.4
import QtQuick.Controls 6.4
import QtQuick.Layouts 6.4
import QtQuick.Window 6.4
import QtQuick.Effects

/**
 * StepConfigPanel - Complete configuration panel for a step
 *
 * Shows all relevant configuration sections based on step type.
 * Each section is collapsible to save space.
 */
Item {
    id: root

    property var stepConfig: null  // The StepConfig object
    property string stepType: ""   // The step type (click, input, etc.)

    signal configChanged(var config)

    width: parent ? parent.width : 300
    height: configColumn.height

    // Helper to determine which sections to show
    function isActionType(types) {
        return types.indexOf(stepType) !== -1
    }

    Column {
        id: configColumn
        width: parent.width
        spacing: 10

        // ==================== EXECUTION SETTINGS ====================
        ConfigSection {
            title: "Execution"
            icon: "\u23F1"  // Timer icon
            accentColor: "#f59e0b"  // Amber
            importance: "recommended"
            summary: {
                var timeout = stepConfig && stepConfig.execution ? stepConfig.execution.timeoutMs : 30000
                var retries = stepConfig && stepConfig.execution ? stepConfig.execution.retryCount : 0
                return "Timeout: " + (timeout/1000) + "s" + (retries > 0 ? ", Retries: " + retries : "")
            }
            expanded: false

            ConfigRow {
                label: "Timeout (ms)"
                inputType: "number"
                value: stepConfig && stepConfig.execution ? stepConfig.execution.timeoutMs : 30000
                defaultValue: 30000
                minValue: 100
                maxValue: 300000
                recommended: true
                tooltip: "Maximum time to wait for the action to complete"
                onValueModified: emitChange("execution.timeoutMs", newValue)
            }

            ConfigRow {
                label: "Retry Count"
                inputType: "number"
                value: stepConfig && stepConfig.execution ? stepConfig.execution.retryCount : 0
                defaultValue: 0
                minValue: 0
                maxValue: 10
                tooltip: "Number of times to retry on failure"
                onValueModified: emitChange("execution.retryCount", newValue)
            }

            ConfigRow {
                label: "Retry Delay (ms)"
                inputType: "number"
                value: stepConfig && stepConfig.execution ? stepConfig.execution.retryDelayMs : 1000
                defaultValue: 1000
                minValue: 0
                maxValue: 30000
                tooltip: "Delay between retry attempts"
                onValueModified: emitChange("execution.retryDelayMs", newValue)
            }

            ConfigRow {
                label: "Continue on Fail"
                inputType: "checkbox"
                value: stepConfig && stepConfig.execution ? stepConfig.execution.continueOnFail : false
                defaultValue: false
                tooltip: "Continue test execution even if this step fails"
                onValueModified: emitChange("execution.continueOnFail", newValue)
            }
        }

        // ==================== CONDITIONS ====================
        ConfigSection {
            title: "Conditions"
            icon: "\u2699"  // Gear icon (not question mark which looks like error)
            accentColor: "#a855f7"  // Purple
            summary: {
                var runIf = stepConfig && stepConfig.conditions ? stepConfig.conditions.runIf : ""
                var skipIf = stepConfig && stepConfig.conditions ? stepConfig.conditions.skipIf : ""
                if (runIf || skipIf) return "Conditional execution active"
                return "No conditions set"
            }
            expanded: false

            ConfigRow {
                label: "Run If"
                inputType: "expression"
                value: stepConfig && stepConfig.conditions ? stepConfig.conditions.runIf : ""
                placeholder: "${variable} == \"value\""
                tooltip: "Only run this step if the condition is true"
                onValueModified: emitChange("conditions.runIf", newValue)
            }

            ConfigRow {
                label: "Skip If"
                inputType: "expression"
                value: stepConfig && stepConfig.conditions ? stepConfig.conditions.skipIf : ""
                placeholder: "${skipFlag}"
                tooltip: "Skip this step if the condition is true"
                onValueModified: emitChange("conditions.skipIf", newValue)
            }

            ConfigRow {
                label: "If Target Not Found"
                inputType: "dropdown"
                value: stepConfig && stepConfig.conditions ? stepConfig.conditions.onTargetNotFound : "fail"
                options: [
                    { value: "fail", label: "Fail" },
                    { value: "skip", label: "Skip" },
                    { value: "warn", label: "Warn Only" }
                ]
                tooltip: "What to do if the target element is not found"
                onValueModified: emitChange("conditions.onTargetNotFound", newValue)
            }
        }

        // ==================== STABILITY CHECKS ====================
        ConfigSection {
            title: "Stability"
            icon: "\u2693"  // Anchor
            accentColor: "#06b6d4"  // Cyan
            importance: "recommended"
            summary: "Element visibility and stability checks"
            expanded: false
            visible: isActionType(["click", "dblclick", "input", "type", "hover", "check", "uncheck"])

            ConfigRow {
                label: "Ensure Visible"
                inputType: "checkbox"
                value: stepConfig && stepConfig.stability && stepConfig.stability.ensureVisible !== null
                       ? stepConfig.stability.ensureVisible : true
                tooltip: "Wait for element to be visible before action"
                onValueModified: emitChange("stability.ensureVisible", newValue)
            }

            ConfigRow {
                label: "Ensure Enabled"
                inputType: "checkbox"
                value: stepConfig && stepConfig.stability && stepConfig.stability.ensureEnabled !== null
                       ? stepConfig.stability.ensureEnabled : true
                tooltip: "Wait for element to be enabled before action"
                onValueModified: emitChange("stability.ensureEnabled", newValue)
            }

            ConfigRow {
                label: "Ensure Stable"
                inputType: "checkbox"
                value: stepConfig && stepConfig.stability && stepConfig.stability.ensureStable !== null
                       ? stepConfig.stability.ensureStable : true
                tooltip: "Wait for element position to stabilize"
                onValueModified: emitChange("stability.ensureStable", newValue)
            }

            ConfigRow {
                label: "Auto Scroll"
                inputType: "checkbox"
                value: stepConfig && stepConfig.stability && stepConfig.stability.autoScrollIntoView !== null
                       ? stepConfig.stability.autoScrollIntoView : true
                tooltip: "Automatically scroll element into view"
                onValueModified: emitChange("stability.autoScrollIntoView", newValue)
            }
        }

        // ==================== CLICK CONFIG ====================
        ConfigSection {
            title: "Click Options"
            icon: "\u25CF"  // Filled circle (simpler than mouse emoji)
            accentColor: "#3b82f6"  // Blue
            summary: {
                var count = stepConfig && stepConfig.click ? stepConfig.click.clickCount : 1
                var btn = stepConfig && stepConfig.click ? stepConfig.click.button : "left"
                return count + "x " + btn + " click"
            }
            expanded: false
            visible: isActionType(["click", "dblclick", "contextmenu"])

            ConfigRow {
                label: "Click Count"
                inputType: "number"
                value: stepConfig && stepConfig.click ? stepConfig.click.clickCount : 1
                minValue: 1
                maxValue: 3
                tooltip: "Number of clicks (1=single, 2=double)"
                onValueModified: emitChange("click.clickCount", newValue)
            }

            ConfigRow {
                label: "Button"
                inputType: "dropdown"
                value: stepConfig && stepConfig.click ? stepConfig.click.button : "left"
                options: [
                    { value: "left", label: "Left" },
                    { value: "right", label: "Right" },
                    { value: "middle", label: "Middle" }
                ]
                tooltip: "Which mouse button to use"
                onValueModified: emitChange("click.button", newValue)
            }

            ConfigRow {
                label: "Force Click"
                inputType: "checkbox"
                value: stepConfig && stepConfig.click ? stepConfig.click.force : false
                tooltip: "Force click even if element is covered"
                onValueModified: emitChange("click.force", newValue)
            }

            ConfigRow {
                label: "No Wait After"
                inputType: "checkbox"
                value: stepConfig && stepConfig.click ? stepConfig.click.noWaitAfter : false
                tooltip: "Don't wait for navigation after click"
                onValueModified: emitChange("click.noWaitAfter", newValue)
            }
        }

        // ==================== INPUT CONFIG ====================
        ConfigSection {
            title: "Input Options"
            icon: "\u2328"  // Keyboard
            accentColor: "#10b981"  // Emerald
            expanded: false
            visible: isActionType(["input", "type", "change"])

            ConfigRow {
                label: "Clear First"
                inputType: "checkbox"
                value: stepConfig && stepConfig.inputConfig ? stepConfig.inputConfig.clearFirst : true
                tooltip: "Clear existing content before typing"
                onValueModified: emitChange("inputConfig.clearFirst", newValue)
            }

            ConfigRow {
                label: "Type Mode"
                inputType: "dropdown"
                value: stepConfig && stepConfig.inputConfig ? stepConfig.inputConfig.typeMode : "fill"
                options: [
                    { value: "fill", label: "Fill (instant)" },
                    { value: "type", label: "Type (keystroke)" }
                ]
                tooltip: "How to enter text - fill is instant, type simulates keystrokes"
                onValueModified: emitChange("inputConfig.typeMode", newValue)
            }

            ConfigRow {
                label: "Type Delay (ms)"
                inputType: "number"
                value: stepConfig && stepConfig.inputConfig ? stepConfig.inputConfig.typeDelayMs : 0
                minValue: 0
                maxValue: 500
                tooltip: "Delay between keystrokes (type mode only)"
                onValueModified: emitChange("inputConfig.typeDelayMs", newValue)
            }

            ConfigRow {
                label: "Press Enter After"
                inputType: "checkbox"
                value: stepConfig && stepConfig.inputConfig ? stepConfig.inputConfig.pressEnterAfter : false
                tooltip: "Press Enter key after typing"
                onValueModified: emitChange("inputConfig.pressEnterAfter", newValue)
            }

            ConfigRow {
                label: "Mask in Logs"
                inputType: "checkbox"
                value: stepConfig && stepConfig.inputConfig ? stepConfig.inputConfig.maskInLogs : false
                tooltip: "Hide value in logs (for passwords)"
                onValueModified: emitChange("inputConfig.maskInLogs", newValue)
            }
        }

        // ==================== HOVER CONFIG ====================
        ConfigSection {
            title: "Hover Options"
            icon: "\u261D"  // Pointing finger
            accentColor: "#ec4899"  // Pink
            expanded: false
            visible: isActionType(["hover"])

            ConfigRow {
                label: "Duration (ms)"
                inputType: "number"
                value: stepConfig && stepConfig.hover ? stepConfig.hover.hoverDurationMs : 0
                minValue: 0
                maxValue: 10000
                tooltip: "How long to hover (0 = just move mouse)"
                onValueModified: emitChange("hover.hoverDurationMs", newValue)
            }

            ConfigRow {
                label: "Force"
                inputType: "checkbox"
                value: stepConfig && stepConfig.hover ? stepConfig.hover.force : false
                tooltip: "Force hover even if element is covered"
                onValueModified: emitChange("hover.force", newValue)
            }
        }

        // ==================== ASSERT OPTIONS ====================
        ConfigSection {
            title: "Assert Options"
            icon: "\u2713"  // Checkmark
            accentColor: "#22c55e"  // Green
            importance: "required"
            summary: {
                var type = stepConfig && stepConfig.assert ? stepConfig.assert.assertType : "text"
                var mode = stepConfig && stepConfig.assert ? stepConfig.assert.matchMode : "contains"
                return type + " assertion (" + mode + ")"
            }
            expanded: true
            showHelpButton: true
            onHelpClicked: assertHelpPopup.open()
            visible: isActionType(["assert", "assertText", "assertVisible", "assertNotVisible",
                                   "assertEnabled", "assertDisabled", "assertChecked",
                                   "assertValue", "assertAttribute", "assertUrl", "assertCount"])

            // ----- Core Assertion Type -----
            ConfigRow {
                label: "Assert Type"
                inputType: "dropdown"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.assertType : "text"
                options: [
                    { value: "text", label: "Text Content" },
                    { value: "visible", label: "Is Visible" },
                    { value: "hidden", label: "Is Hidden" },
                    { value: "enabled", label: "Is Enabled" },
                    { value: "disabled", label: "Is Disabled" },
                    { value: "value", label: "Input Value" },
                    { value: "attribute", label: "Attribute" },
                    { value: "url", label: "Page URL" },
                    { value: "title", label: "Page Title" },
                    { value: "count", label: "Element Count" },
                    { value: "checked", label: "Is Checked" },
                    { value: "localStorage", label: "LocalStorage" },
                    { value: "sessionStorage", label: "SessionStorage" },
                    { value: "cookie", label: "Cookie" },
                    { value: "consoleError", label: "Console Error" },
                    { value: "consoleWarning", label: "Console Warning" },
                    { value: "consoleLog", label: "Console Log" }
                ]
                tooltip: "Type of assertion to perform"
                onValueModified: emitChange("assertConfig.assertType", newValue)
            }

            // ----- Match Mode -----
            ConfigRow {
                label: "Match Mode"
                inputType: "dropdown"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.matchMode : "contains"
                options: [
                    { value: "equals", label: "Equals (exact match)" },
                    { value: "contains", label: "Contains (substring)" },
                    { value: "startsWith", label: "Starts With" },
                    { value: "endsWith", label: "Ends With" },
                    { value: "regex", label: "Regex (pattern match)" }
                ]
                tooltip: "How to match the expected value. See documentation for regex patterns."
                onValueModified: emitChange("assertConfig.matchMode", newValue)
            }

            // ----- Expected Value -----
            ConfigRow {
                label: "Expected Value"
                inputType: "text"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.expectedValue : ""
                placeholder: "Expected text, pattern, or regex"
                tooltip: "The value to assert against. For regex: use patterns like \\d+ for digits, .* for any text"
                onValueModified: emitChange("assertConfig.expectedValue", newValue)
            }

            // ----- Negation -----
            ConfigRow {
                label: "Negate (NOT)"
                inputType: "checkbox"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.negate : false
                tooltip: "Invert the assertion - passes when condition is NOT met (e.g., text does NOT contain)"
                onValueModified: emitChange("assertConfig.negate", newValue)
            }

            // ----- Custom Error Message -----
            ConfigRow {
                label: "Custom Message"
                inputType: "text"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.customMessage : ""
                placeholder: "Custom error message for failures"
                tooltip: "User-defined message shown when assertion fails (for better debugging)"
                onValueModified: emitChange("assertConfig.customMessage", newValue)
            }

            // ----- Text Matching Options -----
            ConfigRow {
                label: "Case Sensitive"
                inputType: "checkbox"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.caseSensitive : false
                tooltip: "Perform case-sensitive comparison (default: case-insensitive)"
                onValueModified: emitChange("assertConfig.caseSensitive", newValue)
            }

            ConfigRow {
                label: "Normalize Whitespace"
                inputType: "checkbox"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.normalizeWhitespace : true
                tooltip: "Collapse multiple spaces/tabs/newlines into single space before comparison"
                onValueModified: emitChange("assertConfig.normalizeWhitespace", newValue)
            }

            // ----- Attribute Assertions -----
            ConfigRow {
                label: "Attribute Name"
                inputType: "text"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.attributeName : ""
                placeholder: "class, href, data-testid, aria-label"
                tooltip: "Attribute to check (for 'attribute' assertion type)"
                onValueModified: emitChange("assertConfig.attributeName", newValue)
            }

            // ----- Storage Key (for localStorage, sessionStorage, cookie) -----
            ConfigRow {
                label: "Storage Key"
                inputType: "text"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.storageKey : ""
                placeholder: "authToken, user_session, etc."
                tooltip: "Key name for storage assertions (localStorage, sessionStorage, cookie)"
                onValueModified: emitChange("assertConfig.storageKey", newValue)
            }

            // ----- Count Assertions -----
            ConfigRow {
                label: "Expected Count"
                inputType: "number"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.expectedCount : 1
                minValue: 0
                maxValue: 10000
                tooltip: "Expected element count (for 'count' assertion type)"
                onValueModified: emitChange("assertConfig.expectedCount", newValue)
            }

            ConfigRow {
                label: "Count Comparison"
                inputType: "dropdown"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.countComparison : "equals"
                options: [
                    { value: "equals", label: "Equals (==)" },
                    { value: "greaterThan", label: "Greater Than (>)" },
                    { value: "lessThan", label: "Less Than (<)" },
                    { value: "atLeast", label: "At Least (>=)" },
                    { value: "atMost", label: "At Most (<=)" }
                ]
                tooltip: "How to compare the element count"
                onValueModified: emitChange("assertConfig.countComparison", newValue)
            }

            // ----- Numeric Tolerance -----
            ConfigRow {
                label: "Numeric Tolerance"
                inputType: "number"
                value: stepConfig && stepConfig.assertConfig ? (stepConfig.assertConfig.numericTolerance || 0) : 0
                minValue: 0
                maxValue: 100
                tooltip: "Allow numeric values to differ by this amount (0 = exact match)"
                onValueModified: emitChange("assertConfig.numericTolerance", newValue > 0 ? newValue : null)
            }

            ConfigRow {
                label: "Tolerance Type"
                inputType: "dropdown"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.numericToleranceType : "absolute"
                options: [
                    { value: "absolute", label: "Absolute (e.g., ±5)" },
                    { value: "percent", label: "Percent (e.g., ±10%)" }
                ]
                tooltip: "How to interpret the tolerance value"
                onValueModified: emitChange("assertConfig.numericToleranceType", newValue)
            }

            // ----- Collection Mode -----
            ConfigRow {
                label: "Collection Mode"
                inputType: "dropdown"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.collectionMode : "first"
                options: [
                    { value: "first", label: "First Element" },
                    { value: "last", label: "Last Element" },
                    { value: "all", label: "ALL Must Pass" },
                    { value: "any", label: "ANY Must Pass" },
                    { value: "none", label: "NONE Should Pass" }
                ]
                tooltip: "How to handle multiple matching elements"
                onValueModified: emitChange("assertConfig.collectionMode", newValue)
            }

            // ----- Retry/Polling -----
            ConfigRow {
                label: "Retry Until Pass"
                inputType: "checkbox"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.retryUntilPass : false
                tooltip: "Keep retrying the assertion until it passes (for dynamic content)"
                onValueModified: emitChange("assertConfig.retryUntilPass", newValue)
            }

            ConfigRow {
                label: "Retry Interval (ms)"
                inputType: "number"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.retryIntervalMs : 500
                minValue: 100
                maxValue: 10000
                tooltip: "Time between retry attempts"
                onValueModified: emitChange("assertConfig.retryIntervalMs", newValue)
            }

            ConfigRow {
                label: "Max Retries"
                inputType: "number"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.maxRetries : 10
                minValue: 1
                maxValue: 100
                tooltip: "Maximum number of retry attempts before failing"
                onValueModified: emitChange("assertConfig.maxRetries", newValue)
            }

            // ----- Behavior -----
            ConfigRow {
                label: "Soft Assert"
                inputType: "checkbox"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.softAssert : false
                tooltip: "Log failure but continue test execution (don't fail the test)"
                onValueModified: emitChange("assertConfig.softAssert", newValue)
            }

            ConfigRow {
                label: "Wait for Element"
                inputType: "checkbox"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.waitForCondition : true
                tooltip: "Auto-wait for element to exist before asserting"
                onValueModified: emitChange("assertConfig.waitForCondition", newValue)
            }

            ConfigRow {
                label: "Wait Timeout (ms)"
                inputType: "number"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.assertTimeoutMs : 5000
                minValue: 100
                maxValue: 60000
                tooltip: "Maximum time to wait for element/condition"
                onValueModified: emitChange("assertConfig.assertTimeoutMs", newValue)
            }

            // ----- Evidence -----
            ConfigRow {
                label: "Screenshot on Fail"
                inputType: "checkbox"
                value: stepConfig && stepConfig.assertConfig ? stepConfig.assertConfig.screenshotOnFail : false
                tooltip: "Capture screenshot when assertion fails (saved to screenshots/assertions/)"
                onValueModified: emitChange("assertConfig.screenshotOnFail", newValue)
            }
        }

        // ==================== CALCULATE/EXPRESSION ====================
        ConfigSection {
            title: "Calculate Expression"
            icon: "\u{1F522}"  // Numbers icon
            accentColor: "#06b6d4"  // Cyan
            importance: "required"
            summary: {
                var expr = stepConfig && stepConfig.calculate ? stepConfig.calculate.expression : ""
                if (expr) return "Expression: " + (expr.length > 30 ? expr.substring(0, 30) + "..." : expr)
                return "Define calculation"
            }
            expanded: true
            visible: isActionType(["calculateAssert", "evaluate", "setVariable", "extractVariable"])

            // Expression input
            ConfigRow {
                label: "Expression"
                inputType: "expression"
                value: stepConfig && stepConfig.calculate ? stepConfig.calculate.expression : ""
                placeholder: "${price} * ${qty} + ${shipping}"
                tooltip: "Math expression with variables. Use ${varName} for variables. Supports: +, -, *, /, %, ** (power)"
                onValueModified: emitChange("calculate.expression", newValue)
            }

            // Comparison mode (for calculateAssert)
            ConfigRow {
                label: "Compare Mode"
                inputType: "dropdown"
                visible: isActionType(["calculateAssert"])
                value: stepConfig && stepConfig.calculate ? stepConfig.calculate.comparisonMode : "equals"
                options: [
                    { value: "equals", label: "Equals (==)" },
                    { value: "notEquals", label: "Not Equals (!=)" },
                    { value: "greaterThan", label: "Greater Than (>)" },
                    { value: "greaterOrEqual", label: "Greater or Equal (>=)" },
                    { value: "lessThan", label: "Less Than (<)" },
                    { value: "lessOrEqual", label: "Less or Equal (<=)" },
                    { value: "contains", label: "Contains" },
                    { value: "between", label: "Between (range)" }
                ]
                tooltip: "How to compare calculated result with actual value"
                onValueModified: emitChange("calculate.comparisonMode", newValue)
            }

            // Tolerance for numeric comparison
            ConfigRow {
                label: "Tolerance"
                inputType: "number"
                visible: isActionType(["calculateAssert"])
                value: stepConfig && stepConfig.calculate ? stepConfig.calculate.tolerance : 0
                defaultValue: 0
                minValue: 0
                maxValue: 1000
                tooltip: "Tolerance for numeric comparisons (e.g., 0.01 for floating point)"
                onValueModified: emitChange("calculate.tolerance", newValue)
            }

            // Where to get actual value
            ConfigRow {
                label: "Actual Value From"
                inputType: "dropdown"
                visible: isActionType(["calculateAssert"])
                value: stepConfig && stepConfig.calculate ? stepConfig.calculate.actualValueFrom : "element"
                options: [
                    { value: "element", label: "Target Element (text)" },
                    { value: "variable", label: "Variable" },
                    { value: "expression", label: "Another Expression" }
                ]
                tooltip: "Where to get the actual value to compare against"
                onValueModified: emitChange("calculate.actualValueFrom", newValue)
            }

            // Variable name for actual value
            ConfigRow {
                label: "Actual Variable"
                inputType: "text"
                visible: isActionType(["calculateAssert"]) && stepConfig && stepConfig.calculate && stepConfig.calculate.actualValueFrom === "variable"
                value: stepConfig && stepConfig.calculate ? stepConfig.calculate.actualVariableName : ""
                placeholder: "variableName"
                tooltip: "Variable containing the actual value"
                onValueModified: emitChange("calculate.actualVariableName", newValue)
            }

            // Store result as variable
            ConfigRow {
                label: "Store Result As"
                inputType: "text"
                value: stepConfig && stepConfig.calculate ? stepConfig.calculate.storeResultAs : ""
                placeholder: "resultVariable"
                tooltip: "Save calculation result to this variable for later use"
                onValueModified: emitChange("calculate.storeResultAs", newValue)
            }

            // Soft assertion
            ConfigRow {
                label: "Soft Assert"
                inputType: "checkbox"
                visible: isActionType(["calculateAssert"])
                value: stepConfig && stepConfig.calculate ? stepConfig.calculate.softAssert : false
                tooltip: "Log failure but continue test execution"
                onValueModified: emitChange("calculate.softAssert", newValue)
            }

            // Custom message
            ConfigRow {
                label: "Failure Message"
                inputType: "text"
                visible: isActionType(["calculateAssert"])
                value: stepConfig && stepConfig.calculate ? stepConfig.calculate.customMessage : ""
                placeholder: "Expected total to be ${expected}"
                tooltip: "Custom message shown on assertion failure"
                onValueModified: emitChange("calculate.customMessage", newValue)
            }
        }

        // ==================== VARIABLE EXTRACTION ====================
        ConfigSection {
            title: "Variable Settings"
            icon: "\u{1F4DD}"  // Memo
            accentColor: "#f97316"  // Orange
            summary: {
                var varName = stepConfig && stepConfig.variable ? stepConfig.variable.variableName : ""
                if (varName) return "Variable: $" + varName
                return "Configure variable"
            }
            expanded: true
            visible: isActionType(["extractVariable", "storeVariable", "setVariable", "storeText", "storeValue", "storeAttribute"])

            // Variable name
            ConfigRow {
                label: "Variable Name"
                inputType: "text"
                value: stepConfig && stepConfig.variable ? stepConfig.variable.variableName : ""
                placeholder: "myVariable"
                tooltip: "Name for the variable (use as ${myVariable})"
                onValueModified: emitChange("variable.variableName", newValue)
            }

            // Extract from (for extractVariable)
            ConfigRow {
                label: "Extract From"
                inputType: "dropdown"
                visible: isActionType(["extractVariable", "storeText", "storeValue", "storeAttribute"])
                value: stepConfig && stepConfig.variable ? stepConfig.variable.extractFrom : "text"
                options: [
                    { value: "text", label: "Text Content" },
                    { value: "value", label: "Input Value" },
                    { value: "attribute", label: "Attribute" },
                    { value: "count", label: "Element Count" },
                    { value: "url", label: "Page URL" },
                    { value: "title", label: "Page Title" }
                ]
                tooltip: "What to extract from the element"
                onValueModified: emitChange("variable.extractFrom", newValue)
            }

            // Attribute name
            ConfigRow {
                label: "Attribute Name"
                inputType: "text"
                visible: stepConfig && stepConfig.variable && stepConfig.variable.extractFrom === "attribute"
                value: stepConfig && stepConfig.variable ? stepConfig.variable.attributeName : ""
                placeholder: "href, class, data-id"
                tooltip: "Which attribute to extract"
                onValueModified: emitChange("variable.attributeName", newValue)
            }

            // Regex pattern
            ConfigRow {
                label: "Regex Pattern"
                inputType: "text"
                visible: isActionType(["extractVariable", "storeText", "storeValue"])
                value: stepConfig && stepConfig.variable ? stepConfig.variable.regexPattern : ""
                placeholder: "(\\d+\\.\\d{2})"
                tooltip: "Extract specific part using regex (optional)"
                onValueModified: emitChange("variable.regexPattern", newValue)
            }

            // Regex group
            ConfigRow {
                label: "Regex Group"
                inputType: "number"
                visible: stepConfig && stepConfig.variable && stepConfig.variable.regexPattern
                value: stepConfig && stepConfig.variable ? stepConfig.variable.regexGroup : 0
                minValue: 0
                maxValue: 10
                tooltip: "Which capture group to use (0 = entire match)"
                onValueModified: emitChange("variable.regexGroup", newValue)
            }
        }

        // ==================== HEALING HINTS ====================
        ConfigSection {
            title: "Healing"
            icon: "\u2695"  // Medical
            accentColor: "#ef4444"  // Red
            summary: "AI self-healing for broken selectors"
            expanded: false
            visible: isActionType(["click", "dblclick", "input", "type", "hover", "check", "uncheck"])

            ConfigRow {
                label: "Disable Healing"
                inputType: "checkbox"
                value: stepConfig && stepConfig.healingHints ? stepConfig.healingHints.disableHealing : false
                tooltip: "Skip self-healing for this step (fail at Tier 0)"
                onValueModified: emitChange("healingHints.disableHealing", newValue)
            }

            ConfigRow {
                label: "Prefer Visual"
                inputType: "checkbox"
                value: stepConfig && stepConfig.healingHints ? stepConfig.healingHints.preferVisualHealing : false
                tooltip: "Hint to try visual (CV) healing before heuristic"
                onValueModified: emitChange("healingHints.preferVisualHealing", newValue)
            }
        }

        // ==================== EVIDENCE/DEBUG ====================
        ConfigSection {
            title: "Evidence"
            icon: "\u{1F4F8}"  // Camera with flash
            accentColor: "#8b5cf6"  // Violet
            summary: {
                var screenshot = stepConfig && stepConfig.evidence ? stepConfig.evidence.captureScreenshot : false
                var html = stepConfig && stepConfig.evidence ? stepConfig.evidence.captureHtml : false
                if (screenshot && html) return "Screenshot + HTML capture"
                if (screenshot) return "Screenshot capture enabled"
                if (html) return "HTML capture enabled"
                return "No evidence capture"
            }
            expanded: false

            ConfigRow {
                label: "Screenshot on Fail"
                inputType: "checkbox"
                value: stepConfig && stepConfig.evidence ? stepConfig.evidence.screenshotOnFail : false
                tooltip: "Take screenshot if this step fails"
                onValueModified: emitChange("evidence.screenshotOnFail", newValue)
            }

            ConfigRow {
                label: "Screenshot on Success"
                inputType: "checkbox"
                value: stepConfig && stepConfig.evidence ? stepConfig.evidence.screenshotOnSuccess : false
                tooltip: "Take screenshot after successful execution"
                onValueModified: emitChange("evidence.screenshotOnSuccess", newValue)
            }

            ConfigRow {
                label: "Highlight Element"
                inputType: "checkbox"
                value: stepConfig && stepConfig.evidence ? stepConfig.evidence.highlightElement : false
                tooltip: "Visually highlight the element before action"
                onValueModified: emitChange("evidence.highlightElement", newValue)
            }

            ConfigRow {
                label: "Log Selector Resolution"
                inputType: "checkbox"
                value: stepConfig && stepConfig.evidence ? stepConfig.evidence.logSelectorResolution : false
                tooltip: "Log detailed selector resolution info"
                onValueModified: emitChange("evidence.logSelectorResolution", newValue)
            }
        }

        // ==================== POST-STEP ====================
        ConfigSection {
            title: "Post-Step"
            icon: "\u27A1"  // Right arrow
            accentColor: "#64748b"  // Slate
            summary: {
                var delay = stepConfig && stepConfig.postStep ? stepConfig.postStep.delayAfterMs : 0
                var waitFor = stepConfig && stepConfig.postStep ? stepConfig.postStep.waitForSelector : ""
                if (delay > 0 && waitFor) return delay + "ms delay + wait for element"
                if (delay > 0) return delay + "ms delay after"
                if (waitFor) return "Wait for element after"
                return "No post-step actions"
            }
            expanded: false

            ConfigRow {
                label: "Wait After"
                inputType: "dropdown"
                value: stepConfig && stepConfig.postStep ? stepConfig.postStep.waitAfter : "none"
                options: [
                    { value: "none", label: "None" },
                    { value: "networkIdle", label: "Network Idle" },
                    { value: "domContentLoaded", label: "DOM Content Loaded" },
                    { value: "load", label: "Page Load" },
                    { value: "custom", label: "Custom Time" }
                ]
                tooltip: "Wait condition after step completes"
                onValueModified: emitChange("postStep.waitAfter", newValue)
            }

            ConfigRow {
                label: "Wait Time (ms)"
                inputType: "number"
                value: stepConfig && stepConfig.postStep ? stepConfig.postStep.waitAfterMs : 0
                minValue: 0
                maxValue: 60000
                tooltip: "Time to wait (for custom wait)"
                onValueModified: emitChange("postStep.waitAfterMs", newValue)
            }

            ConfigRow {
                label: "Wait for Selector"
                inputType: "text"
                value: stepConfig && stepConfig.postStep ? stepConfig.postStep.waitForSelector : ""
                placeholder: "#element-id"
                tooltip: "Wait for this element after action"
                onValueModified: emitChange("postStep.waitForSelector", newValue)
            }
        }
    }

    // Emit config change signal with the path and value
    function emitChange(path, value) {
        var config = stepConfig ? JSON.parse(JSON.stringify(stepConfig)) : {}
        setNestedValue(config, path, value)
        configChanged(config)
    }

    // Helper to set nested object value by path
    function setNestedValue(obj, path, value) {
        var parts = path.split(".")
        var current = obj
        for (var i = 0; i < parts.length - 1; i++) {
            if (!current[parts[i]]) {
                current[parts[i]] = {}
            }
            current = current[parts[i]]
        }
        current[parts[parts.length - 1]] = value
    }

    // ==================== ASSERTION HELP POPUP ====================
    Popup {
        id: assertHelpPopup
        modal: true
        focus: true
        anchors.centerIn: Overlay.overlay
        width: 900
        height: 680
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 0

        property int currentTab: 0

        background: Rectangle {
            color: "#0f172a"
            radius: 16
            border.color: "#334155"
            border.width: 2
        }

        contentItem: Item {
            anchors.fill: parent

            // Header
            Rectangle {
                id: popupHeader
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 60
                color: "#1e293b"
                radius: 16

                // Bottom corners should be square
                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 16
                    color: "#1e293b"
                }

                // Icon
                Rectangle {
                    id: headerIcon
                    anchors.left: parent.left
                    anchors.leftMargin: 24
                    anchors.verticalCenter: parent.verticalCenter
                    width: 40
                    height: 40
                    radius: 10
                    color: "#22c55e20"
                    border.color: "#22c55e"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "\u2713"
                        font.pixelSize: 20
                        font.bold: true
                        color: "#22c55e"
                    }
                }

                // Title
                Text {
                    anchors.left: headerIcon.right
                    anchors.leftMargin: 16
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Assertion Documentation"
                    font.pixelSize: 20
                    font.weight: Font.Bold
                    color: "#f1f5f9"
                }

                // Close button
                Rectangle {
                    anchors.right: parent.right
                    anchors.rightMargin: 20
                    anchors.verticalCenter: parent.verticalCenter
                    width: 36
                    height: 36
                    radius: 8
                    color: popupCloseMouse.containsMouse ? "#ef444440" : "transparent"
                    border.color: popupCloseMouse.containsMouse ? "#ef4444" : "#475569"
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "\u2715"
                        font.pixelSize: 16
                        font.bold: true
                        color: popupCloseMouse.containsMouse ? "#ef4444" : "#94a3b8"
                    }

                    MouseArea {
                        id: popupCloseMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: assertHelpPopup.close()
                    }
                }
            }

            // Tab bar
            Rectangle {
                id: popupTabBar
                anchors.top: popupHeader.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 56
                color: "#0f172a"

                Row {
                    anchors.centerIn: parent
                    spacing: 12

                    Repeater {
                        model: [
                            {name: "Overview", icon: "\u2139"},
                            {name: "Match Modes", icon: "\u2261"},
                            {name: "Regex Guide", icon: ".*"},
                            {name: "Examples", icon: "\u270E"}
                        ]

                        Rectangle {
                            width: 140
                            height: 40
                            radius: 8
                            color: assertHelpPopup.currentTab === index ? "#22c55e20" : (tabItemMouse.containsMouse ? "#1e293b" : "transparent")
                            border.color: assertHelpPopup.currentTab === index ? "#22c55e" : "transparent"
                            border.width: assertHelpPopup.currentTab === index ? 2 : 0

                            Row {
                                anchors.centerIn: parent
                                spacing: 8

                                Text {
                                    text: modelData.icon
                                    font.pixelSize: 14
                                    font.bold: true
                                    color: assertHelpPopup.currentTab === index ? "#22c55e" : "#64748b"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: modelData.name
                                    font.pixelSize: 13
                                    font.weight: assertHelpPopup.currentTab === index ? Font.DemiBold : Font.Normal
                                    color: assertHelpPopup.currentTab === index ? "#22c55e" : "#94a3b8"
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            MouseArea {
                                id: tabItemMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: assertHelpPopup.currentTab = index
                            }
                        }
                    }
                }
            }

            // Content area
            Rectangle {
                id: popupContent
                anchors.top: popupTabBar.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 16
                anchors.topMargin: 8
                color: "#0a0f1a"
                radius: 12
                border.color: "#1e293b"
                border.width: 1

                // Tab 0: Overview
                Flickable {
                    id: tab0Flickable
                    anchors.fill: parent
                    anchors.margins: 4
                    contentWidth: width
                    contentHeight: tab0Content.height
                    clip: true
                    visible: assertHelpPopup.currentTab === 0
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                        width: 10
                    }

                    Text {
                        id: tab0Content
                        width: parent.width - 30
                        x: 20
                        y: 16
                        wrapMode: Text.Wrap
                        textFormat: Text.RichText
                        color: "#c8d4e3"
                        font.pixelSize: 13
                        lineHeight: 1.4
                        text: "<h2 style='color: #4fc3f7; margin-bottom: 12px;'>Assertion Types</h2>
<table style='color: #c8d4e3; margin-bottom: 20px; width: 100%;' cellpadding='6'>
<tr><td style='width: 120px;'><b style='color: #81c784;'>text</b></td><td>Assert element's text content</td></tr>
<tr><td><b style='color: #81c784;'>visible</b></td><td>Assert element is visible on page</td></tr>
<tr><td><b style='color: #81c784;'>hidden</b></td><td>Assert element is hidden/not visible</td></tr>
<tr><td><b style='color: #81c784;'>enabled</b></td><td>Assert element is enabled (clickable)</td></tr>
<tr><td><b style='color: #81c784;'>disabled</b></td><td>Assert element is disabled</td></tr>
<tr><td><b style='color: #81c784;'>value</b></td><td>Assert input element's value</td></tr>
<tr><td><b style='color: #81c784;'>attribute</b></td><td>Assert element attribute value</td></tr>
<tr><td><b style='color: #81c784;'>count</b></td><td>Assert number of matching elements</td></tr>
<tr><td><b style='color: #81c784;'>checked</b></td><td>Assert checkbox/radio is checked</td></tr>
<tr><td><b style='color: #81c784;'>url</b></td><td>Assert current page URL</td></tr>
<tr><td><b style='color: #81c784;'>title</b></td><td>Assert page title</td></tr>
<tr><td><b style='color: #81c784;'>localStorage</b></td><td>Assert localStorage value</td></tr>
<tr><td><b style='color: #81c784;'>sessionStorage</b></td><td>Assert sessionStorage value</td></tr>
<tr><td><b style='color: #81c784;'>cookie</b></td><td>Assert cookie value</td></tr>
<tr><td><b style='color: #81c784;'>consoleError</b></td><td>Assert console error exists</td></tr>
</table>

<h2 style='color: #4fc3f7; margin-bottom: 12px;'>Key Features</h2>
<ul style='color: #c8d4e3; margin-bottom: 20px;'>
<li style='margin-bottom: 8px;'><b style='color: #ffb74d;'>Negation (NOT)</b> - Invert assertion result (e.g., text does NOT contain)</li>
<li style='margin-bottom: 8px;'><b style='color: #ffb74d;'>Custom Messages</b> - User-defined error messages for better debugging</li>
<li style='margin-bottom: 8px;'><b style='color: #ffb74d;'>Retry/Polling</b> - Retry until pass for dynamic content</li>
<li style='margin-bottom: 8px;'><b style='color: #ffb74d;'>Collection Mode</b> - Handle multiple elements (all, any, none, first, last)</li>
<li style='margin-bottom: 8px;'><b style='color: #ffb74d;'>Numeric Tolerance</b> - Compare numbers with allowed variance</li>
<li style='margin-bottom: 8px;'><b style='color: #ffb74d;'>Soft Assert</b> - Log failure but continue test execution</li>
<li style='margin-bottom: 8px;'><b style='color: #ffb74d;'>Screenshot on Fail</b> - Capture evidence automatically</li>
</ul>

<h2 style='color: #4fc3f7; margin-bottom: 12px;'>Collection Modes</h2>
<ul style='color: #c8d4e3;'>
<li style='margin-bottom: 8px;'><b style='color: #ce93d8;'>first</b> - Assert only on first matching element (default)</li>
<li style='margin-bottom: 8px;'><b style='color: #ce93d8;'>last</b> - Assert only on last matching element</li>
<li style='margin-bottom: 8px;'><b style='color: #ce93d8;'>all</b> - ALL elements must pass the assertion</li>
<li style='margin-bottom: 8px;'><b style='color: #ce93d8;'>any</b> - At least ONE element must pass</li>
<li style='margin-bottom: 8px;'><b style='color: #ce93d8;'>none</b> - NO elements should pass (all must fail)</li>
</ul>"
                    }
                }

                // Tab 1: Match Modes
                Flickable {
                    anchors.fill: parent
                    anchors.margins: 4
                    contentWidth: width
                    contentHeight: tab1Content.height
                    clip: true
                    visible: assertHelpPopup.currentTab === 1
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                        width: 10
                    }

                    Text {
                        id: tab1Content
                        width: parent.width - 30
                        x: 20
                        y: 16
                        wrapMode: Text.Wrap
                        textFormat: Text.RichText
                        color: "#c8d4e3"
                        font.pixelSize: 13
                        lineHeight: 1.4
                        text: "<h2 style='color: #4fc3f7; margin-bottom: 16px;'>Match Modes</h2>

<h3 style='color: #81c784; margin-top: 16px;'>equals - Exact Match</h3>
<p style='margin-bottom: 8px;'>The actual value must exactly match the expected value.</p>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Expected: \"Hello World\"
Actual: \"Hello World\"  -> PASS
Actual: \"hello world\"  -> PASS (if case-insensitive)
Actual: \"Hello World!\" -> FAIL</pre>

<h3 style='color: #81c784; margin-top: 16px;'>contains - Substring Match</h3>
<p style='margin-bottom: 8px;'>The expected value must be found somewhere in the actual value.</p>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Expected: \"Hello\"
Actual: \"Hello World\"     -> PASS
Actual: \"Say Hello there\" -> PASS
Actual: \"Hi World\"        -> FAIL</pre>

<h3 style='color: #81c784; margin-top: 16px;'>startsWith - Prefix Match</h3>
<p style='margin-bottom: 8px;'>The actual value must begin with the expected value.</p>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Expected: \"Hello\"
Actual: \"Hello World\" -> PASS
Actual: \"Say Hello\"   -> FAIL</pre>

<h3 style='color: #81c784; margin-top: 16px;'>endsWith - Suffix Match</h3>
<p style='margin-bottom: 8px;'>The actual value must end with the expected value.</p>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Expected: \"World\"
Actual: \"Hello World\" -> PASS
Actual: \"World Hello\" -> FAIL</pre>

<h3 style='color: #81c784; margin-top: 16px;'>regex - Regular Expression</h3>
<p style='margin-bottom: 8px;'>The expected value is treated as a regex pattern.</p>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Expected: \"\\d{3}-\\d{4}\"
Actual: \"555-1234\"        -> PASS
Actual: \"phone: 555-1234\" -> PASS
Actual: \"5551234\"         -> FAIL</pre>

<h2 style='color: #4fc3f7; margin-top: 24px; margin-bottom: 12px;'>Options</h2>
<ul style='color: #c8d4e3;'>
<li style='margin-bottom: 8px;'><b style='color: #ffb74d;'>Case Sensitive</b> - Default OFF. Turn ON for exact case matching.</li>
<li style='margin-bottom: 8px;'><b style='color: #ffb74d;'>Normalize Whitespace</b> - Default ON. Collapses multiple spaces/tabs/newlines.</li>
</ul>"
                    }
                }

                // Tab 2: Regex Guide
                Flickable {
                    anchors.fill: parent
                    anchors.margins: 4
                    contentWidth: width
                    contentHeight: tab2Content.height
                    clip: true
                    visible: assertHelpPopup.currentTab === 2
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                        width: 10
                    }

                    Text {
                        id: tab2Content
                        width: parent.width - 30
                        x: 20
                        y: 16
                        wrapMode: Text.Wrap
                        textFormat: Text.RichText
                        color: "#c8d4e3"
                        font.pixelSize: 13
                        lineHeight: 1.4
                        text: "<h2 style='color: #4fc3f7; margin-bottom: 16px;'>Regex Quick Reference</h2>

<h3 style='color: #81c784;'>Basic Patterns</h3>
<table style='color: #c8d4e3; margin-bottom: 20px; width: 100%;' cellpadding='6'>
<tr><td style='color: #ffb74d; width: 60px; font-family: monospace;'><b>.</b></td><td style='width: 180px;'>Any single character</td><td style='color: #a5d6a7;'>a.c matches \"abc\", \"a1c\"</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>*</b></td><td>Zero or more of previous</td><td style='color: #a5d6a7;'>ab*c matches \"ac\", \"abc\"</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>+</b></td><td>One or more of previous</td><td style='color: #a5d6a7;'>ab+c matches \"abc\" not \"ac\"</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>?</b></td><td>Zero or one of previous</td><td style='color: #a5d6a7;'>colou?r matches both</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>^</b></td><td>Start of string</td><td style='color: #a5d6a7;'>^Hello at beginning</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>$</b></td><td>End of string</td><td style='color: #a5d6a7;'>World$ at end</td></tr>
</table>

<h3 style='color: #81c784;'>Character Classes</h3>
<table style='color: #c8d4e3; margin-bottom: 20px; width: 100%;' cellpadding='6'>
<tr><td style='color: #ffb74d; width: 60px; font-family: monospace;'><b>\\d</b></td><td style='width: 180px;'>Any digit (0-9)</td><td style='color: #a5d6a7;'>\\d{3} matches \"123\"</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>\\D</b></td><td>Any non-digit</td><td style='color: #a5d6a7;'>\\D+ matches \"abc\"</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>\\w</b></td><td>Word char (a-z, 0-9, _)</td><td style='color: #a5d6a7;'>\\w+ matches \"hello_123\"</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>\\s</b></td><td>Whitespace</td><td style='color: #a5d6a7;'>\\s+ matches spaces</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>[abc]</b></td><td>Any char in brackets</td><td style='color: #a5d6a7;'>[aeiou] vowels</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>[^abc]</b></td><td>NOT in brackets</td><td style='color: #a5d6a7;'>[^0-9] non-digits</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>[a-z]</b></td><td>Range of characters</td><td style='color: #a5d6a7;'>[a-zA-Z] letters</td></tr>
</table>

<h3 style='color: #81c784;'>Quantifiers</h3>
<table style='color: #c8d4e3; margin-bottom: 20px; width: 100%;' cellpadding='6'>
<tr><td style='color: #ffb74d; width: 60px; font-family: monospace;'><b>{n}</b></td><td style='width: 180px;'>Exactly n times</td><td style='color: #a5d6a7;'>\\d{4} = 4 digits</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>{n,}</b></td><td>n or more times</td><td style='color: #a5d6a7;'>\\d{2,} = 2+ digits</td></tr>
<tr><td style='color: #ffb74d; font-family: monospace;'><b>{n,m}</b></td><td>Between n and m</td><td style='color: #a5d6a7;'>\\d{2,4} = 2-4 digits</td></tr>
</table>

<h3 style='color: #81c784;'>Common Patterns</h3>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'># Phone (US):     \\d{3}[-.]?\\d{3}[-.]?\\d{4}
# Email:          [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}
# Price:          \\$?\\d+\\.?\\d{0,2}
# Date:           \\d{1,2}/\\d{1,2}/\\d{4}
# URL:            https?://[^\\s]+
# Alphanumeric:   ^[a-zA-Z0-9]+$</pre>

<h3 style='color: #f44336;'>Escape These Characters</h3>
<p style='margin-bottom: 8px;'>Use \\ before these to match literally:</p>
<pre style='background: #0d1520; padding: 12px; color: #ef9a9a; border-radius: 6px;'>. * + ? ^ $ [ ] { } ( ) | \\

To match \"$100.00\" use: \\$\\d+\\.\\d{2}</pre>"
                    }
                }

                // Tab 3: Examples
                Flickable {
                    anchors.fill: parent
                    anchors.margins: 4
                    contentWidth: width
                    contentHeight: tab3Content.height
                    clip: true
                    visible: assertHelpPopup.currentTab === 3
                    boundsBehavior: Flickable.StopAtBounds

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                        width: 10
                    }

                    Text {
                        id: tab3Content
                        width: parent.width - 30
                        x: 20
                        y: 16
                        wrapMode: Text.Wrap
                        textFormat: Text.RichText
                        color: "#c8d4e3"
                        font.pixelSize: 13
                        lineHeight: 1.4
                        text: "<h2 style='color: #4fc3f7; margin-bottom: 16px;'>Practical Examples</h2>

<h3 style='color: #81c784;'>1. Assert Error Message Appears</h3>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Assert Type: text
Match Mode: contains
Expected Value: Invalid username or password
Retry Until Pass: ON
Retry Interval: 200ms
Max Retries: 15
Screenshot on Fail: ON</pre>

<h3 style='color: #81c784;'>2. Assert NO Errors (Negation)</h3>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Assert Type: text
Match Mode: contains
Expected Value: error
Negate (NOT): ON
Custom Message: Page should not display any errors</pre>

<h3 style='color: #81c784;'>3. Assert Price Within Range</h3>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Assert Type: text
Expected Value: 29.99
Numeric Tolerance: 10
Tolerance Type: percent
Custom Message: Price should be around $29.99</pre>

<h3 style='color: #81c784;'>4. Assert At Least 5 Items</h3>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Assert Type: count
Expected Count: 5
Count Comparison: At Least (>=)
Soft Assert: ON</pre>

<h3 style='color: #81c784;'>5. Assert ALL Items Have Price</h3>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Assert Type: text
Match Mode: regex
Expected Value: \\$\\d+\\.\\d{2}
Collection Mode: ALL Must Pass</pre>

<h3 style='color: #81c784;'>6. Assert Valid Email Format</h3>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Assert Type: value
Match Mode: regex
Expected Value: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$
Custom Message: Email field should contain valid email</pre>

<h3 style='color: #81c784;'>7. Assert JWT Token Stored</h3>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Assert Type: localStorage
Storage Key: accessToken
Match Mode: regex
Expected Value: ^eyJ[A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+$</pre>

<h3 style='color: #81c784;'>8. Assert No Console Errors</h3>
<pre style='background: #0d1520; padding: 12px; color: #a5d6a7; border-radius: 6px; margin-bottom: 16px;'>Assert Type: consoleError
Negate (NOT): ON
Custom Message: Page should not have JavaScript errors</pre>

<h2 style='color: #4fc3f7; margin-top: 24px; margin-bottom: 12px;'>Tips</h2>
<ul style='color: #c8d4e3;'>
<li style='margin-bottom: 8px;'><b style='color: #ffb74d;'>contains</b> over equals - more resilient to changes</li>
<li style='margin-bottom: 8px;'>Always set <b style='color: #ffb74d;'>Custom Message</b> for debugging</li>
<li style='margin-bottom: 8px;'>Use <b style='color: #ffb74d;'>Retry Until Pass</b> for dynamic content</li>
<li style='margin-bottom: 8px;'>Enable <b style='color: #ffb74d;'>Screenshot on Fail</b> for evidence</li>
<li style='margin-bottom: 8px;'>Test regex in an online tester first</li>
</ul>"
                    }
                }
            }
        }
    }
}
