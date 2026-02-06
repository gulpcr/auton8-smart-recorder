# Assertion System Documentation

The Auton8 Recorder provides a comprehensive assertion system for validating test conditions. This document covers all assertion types, configuration options, and usage examples.

## Table of Contents

1. [Assertion Types](#assertion-types)
2. [Match Modes](#match-modes)
3. [Regex Patterns Guide](#regex-patterns-guide)
4. [Negation](#negation)
5. [Collection Modes](#collection-modes)
6. [Retry/Polling](#retrypolling)
7. [Numeric Tolerance](#numeric-tolerance)
8. [Storage Assertions](#storage-assertions)
9. [Console Assertions](#console-assertions)
10. [Configuration Reference](#configuration-reference)
11. [Examples](#examples)

---

## Assertion Types

### Element Assertions

| Type | Description | Requires Element |
|------|-------------|------------------|
| `text` | Assert element's text content | Yes |
| `visible` | Assert element is visible | Yes |
| `hidden` | Assert element is hidden/not visible | Yes (or absent) |
| `enabled` | Assert element is enabled (clickable) | Yes |
| `disabled` | Assert element is disabled | Yes |
| `value` | Assert input element's value | Yes |
| `attribute` | Assert element attribute value | Yes |
| `count` | Assert number of matching elements | Yes |
| `checked` | Assert checkbox/radio is checked | Yes |

### Page Assertions

| Type | Description | Requires Element |
|------|-------------|------------------|
| `url` | Assert current page URL | No |
| `title` | Assert page title | No |

### Storage Assertions

| Type | Description | Requires Element |
|------|-------------|------------------|
| `localStorage` | Assert localStorage value | No |
| `sessionStorage` | Assert sessionStorage value | No |
| `cookie` | Assert cookie value | No |

### Console Assertions

| Type | Description | Requires Element |
|------|-------------|------------------|
| `consoleError` | Assert console error message exists | No |
| `consoleWarning` | Assert console warning exists | No |
| `consoleLog` | Assert console log message exists | No |

---

## Match Modes

Match modes determine how the expected value is compared to the actual value.

### `equals` - Exact Match
The actual value must exactly match the expected value.

```
Expected: "Hello World"
Actual: "Hello World"  -> PASS
Actual: "hello world"  -> PASS (if case-insensitive)
Actual: "Hello World!" -> FAIL
```

### `contains` - Substring Match
The expected value must be found somewhere in the actual value.

```
Expected: "Hello"
Actual: "Hello World"     -> PASS
Actual: "Say Hello there" -> PASS
Actual: "Hi World"        -> FAIL
```

### `startsWith` - Prefix Match
The actual value must begin with the expected value.

```
Expected: "Hello"
Actual: "Hello World" -> PASS
Actual: "Say Hello"   -> FAIL
```

### `endsWith` - Suffix Match
The actual value must end with the expected value.

```
Expected: "World"
Actual: "Hello World" -> PASS
Actual: "World Hello" -> FAIL
```

### `regex` - Regular Expression Match
The expected value is treated as a regular expression pattern.

```
Expected: "\\d{3}-\\d{4}"
Actual: "555-1234"    -> PASS
Actual: "phone: 555-1234" -> PASS (pattern found within)
Actual: "5551234"     -> FAIL
```

---

## Regex Patterns Guide

Regular expressions (regex) are powerful patterns for matching text. Here's a comprehensive guide:

### Basic Patterns

| Pattern | Matches | Example |
|---------|---------|---------|
| `.` | Any single character | `a.c` matches "abc", "a1c", "a-c" |
| `*` | Zero or more of previous | `ab*c` matches "ac", "abc", "abbc" |
| `+` | One or more of previous | `ab+c` matches "abc", "abbc" but not "ac" |
| `?` | Zero or one of previous | `colou?r` matches "color", "colour" |
| `^` | Start of string | `^Hello` matches "Hello World" but not "Say Hello" |
| `$` | End of string | `World$` matches "Hello World" but not "World Hello" |

### Character Classes

| Pattern | Matches | Example |
|---------|---------|---------|
| `[abc]` | Any character in brackets | `[aeiou]` matches any vowel |
| `[^abc]` | Any character NOT in brackets | `[^0-9]` matches non-digits |
| `[a-z]` | Range of characters | `[a-zA-Z]` matches any letter |
| `\d` | Any digit (0-9) | `\d{3}` matches "123", "456" |
| `\D` | Any non-digit | `\D+` matches "abc", "hello" |
| `\w` | Word character (a-z, A-Z, 0-9, _) | `\w+` matches "hello_123" |
| `\W` | Non-word character | `\W` matches " ", "!", "@" |
| `\s` | Whitespace (space, tab, newline) | `\s+` matches spaces |
| `\S` | Non-whitespace | `\S+` matches words |

### Quantifiers

| Pattern | Matches | Example |
|---------|---------|---------|
| `{n}` | Exactly n times | `\d{4}` matches exactly 4 digits |
| `{n,}` | n or more times | `\d{2,}` matches 2+ digits |
| `{n,m}` | Between n and m times | `\d{2,4}` matches 2-4 digits |

### Common Patterns

```
# Email address
[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}

# Phone number (US)
\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}

# URL
https?://[^\s]+

# Price/currency
\$?\d+\.?\d{0,2}

# Date (MM/DD/YYYY)
\d{1,2}/\d{1,2}/\d{4}

# Time (HH:MM)
\d{1,2}:\d{2}

# ZIP code (US)
\d{5}(-\d{4})?

# IP address
\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}

# UUID
[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}

# Any number (integer or decimal)
-?\d+\.?\d*

# HTML tag
<[^>]+>

# Alphanumeric only
^[a-zA-Z0-9]+$

# Contains specific word
\bword\b
```

### Escaping Special Characters

These characters have special meaning and must be escaped with `\` to match literally:

```
. * + ? ^ $ [ ] { } ( ) | \

Example: To match "$100.00"
Pattern: \$\d+\.\d{2}
```

### Practical Examples

```
# Assert price is between $10-99
Pattern: \$[1-9]\d\.\d{2}
Matches: "$15.99", "$42.00"

# Assert error code format
Pattern: ^ERR-\d{4}$
Matches: "ERR-1234", "ERR-0001"

# Assert contains order ID
Pattern: Order #\d+
Matches: "Your Order #12345 is confirmed"

# Assert ISO date format
Pattern: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}
Matches: "2024-01-15T14:30:00"
```

---

## Negation

The `negate` option inverts the assertion result. Use this for "NOT" conditions.

| Normal | Negated |
|--------|---------|
| Text contains "error" | Text does NOT contain "error" |
| Element is visible | Element is NOT visible |
| Value equals "active" | Value does NOT equal "active" |

### Example Use Cases

```yaml
# Assert no error messages
assertType: text
expectedValue: "error"
matchMode: contains
negate: true  # Passes if "error" is NOT found

# Assert element disappeared
assertType: visible
negate: true  # Passes if element is NOT visible

# Assert value changed from default
assertType: value
expectedValue: "default"
matchMode: equals
negate: true  # Passes if value is NOT "default"
```

---

## Collection Modes

When a selector matches multiple elements, collection mode determines how assertions are applied.

### `first` (Default)
Assert only on the first matching element.

```
Selector matches 5 buttons
-> Only first button is checked
```

### `last`
Assert only on the last matching element.

```
Selector matches 5 buttons
-> Only last button is checked
```

### `all`
ALL elements must pass the assertion.

```
Selector matches 5 buttons
All must be enabled -> PASS only if all 5 are enabled
If even one is disabled -> FAIL
```

### `any`
At least ONE element must pass.

```
Selector matches 5 buttons
At least one must contain "Submit" -> PASS if any contains it
All must NOT contain "Submit" -> FAIL
```

### `none`
NO elements should pass (all must fail the condition).

```
Selector matches 5 error messages
None should exist -> Use this with visible assertion
Useful for asserting no elements match
```

### Example Use Cases

```yaml
# All items in cart have price
collectionMode: all
assertType: text
matchMode: regex
expectedValue: \$\d+\.\d{2}

# At least one "Add to Cart" button exists
collectionMode: any
assertType: visible

# No error messages visible
collectionMode: none
assertType: visible
negate: true  # Combined with negate for "none visible"
```

---

## Retry/Polling

For dynamic content that may not be immediately available, use retry/polling.

### Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `retryUntilPass` | Enable retry mode | false |
| `retryIntervalMs` | Time between retries (ms) | 500 |
| `maxRetries` | Maximum retry attempts | 10 |

### How It Works

1. Execute assertion
2. If fails and retries remaining:
   - Wait `retryIntervalMs`
   - Try again
3. Repeat until pass or `maxRetries` exhausted

### Example Use Cases

```yaml
# Wait for loading spinner to disappear
assertType: hidden
retryUntilPass: true
retryIntervalMs: 500
maxRetries: 20  # Wait up to 10 seconds

# Wait for async content to load
assertType: text
expectedValue: "Data loaded"
retryUntilPass: true

# Wait for element count to stabilize
assertType: count
expectedCount: 10
countComparison: atLeast
retryUntilPass: true
```

---

## Numeric Tolerance

For comparing numeric values that may have slight variations.

### Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `numericTolerance` | Allowed difference | null (exact) |
| `numericToleranceType` | `absolute` or `percent` | absolute |

### Absolute Tolerance

The difference must be within ± the tolerance value.

```yaml
expectedValue: "100"
numericTolerance: 5
numericToleranceType: absolute

# Passes: 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105
# Fails: 94, 106
```

### Percent Tolerance

The difference must be within ± the tolerance percentage of expected.

```yaml
expectedValue: "100"
numericTolerance: 10
numericToleranceType: percent

# 10% of 100 = 10
# Passes: 90-110
# Fails: 89, 111
```

### Use Cases

```yaml
# Price may vary slightly
assertType: text
expectedValue: "$99.99"
numericTolerance: 1
numericToleranceType: absolute

# Percentage change within range
expectedValue: "50"
numericTolerance: 5
numericToleranceType: percent  # Allows 47.5-52.5
```

---

## Storage Assertions

Assert on browser storage values.

### localStorage

```yaml
assertType: localStorage
storageKey: "authToken"
expectedValue: ""
matchMode: regex
expectedValue: ^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$  # JWT format
```

### sessionStorage

```yaml
assertType: sessionStorage
storageKey: "user_session"
matchMode: contains
expectedValue: "active"
```

### Cookies

```yaml
assertType: cookie
storageKey: "session_id"
matchMode: regex
expectedValue: ^[a-f0-9]{32}$
```

---

## Console Assertions

Assert on browser console output. Useful for detecting JavaScript errors.

### Console Errors

```yaml
# Assert NO console errors
assertType: consoleError
negate: true

# Assert specific error exists
assertType: consoleError
expectedValue: "API request failed"
matchMode: contains
```

### Console Warnings

```yaml
assertType: consoleWarning
expectedValue: "deprecated"
matchMode: contains
```

### Console Logs

```yaml
assertType: consoleLog
expectedValue: "User logged in successfully"
```

---

## Configuration Reference

### Full AssertConfig Schema

```yaml
assertConfig:
  # Core
  assertType: text | visible | hidden | enabled | disabled | value | attribute | url | title | count | checked | localStorage | sessionStorage | cookie | consoleError | consoleWarning | consoleLog

  # Matching
  matchMode: equals | contains | startsWith | endsWith | regex
  expectedValue: "string"
  caseSensitive: false
  normalizeWhitespace: true

  # Negation
  negate: false

  # Custom message
  customMessage: "User-friendly error message"

  # Attribute (for assertType: attribute)
  attributeName: "data-testid"

  # Storage (for localStorage, sessionStorage, cookie)
  storageKey: "key_name"

  # Count (for assertType: count)
  expectedCount: 5
  countComparison: equals | greaterThan | lessThan | atLeast | atMost

  # Numeric tolerance
  numericTolerance: 5.0
  numericToleranceType: absolute | percent

  # Collection mode
  collectionMode: first | last | all | any | none

  # Retry/polling
  retryUntilPass: false
  retryIntervalMs: 500
  maxRetries: 10

  # Behavior
  softAssert: false
  waitForCondition: true
  assertTimeoutMs: 5000

  # Evidence
  screenshotOnFail: false
```

---

## Examples

### Example 1: Login Form Validation

```yaml
# Assert error message appears for invalid login
- type: assertText
  config:
    assertConfig:
      assertType: text
      expectedValue: "Invalid username or password"
      matchMode: contains
      retryUntilPass: true
      retryIntervalMs: 200
      maxRetries: 15
      screenshotOnFail: true
```

### Example 2: Product Price Validation

```yaml
# Assert product price is within expected range
- type: assertText
  config:
    assertConfig:
      assertType: text
      expectedValue: "29.99"
      matchMode: regex
      numericTolerance: 10
      numericToleranceType: percent
      customMessage: "Product price should be around $29.99"
```

### Example 3: Table Row Count

```yaml
# Assert at least 5 items in the table
- type: assertCount
  config:
    assertConfig:
      assertType: count
      expectedCount: 5
      countComparison: atLeast
      softAssert: true
```

### Example 4: No Errors After Action

```yaml
# Assert no console errors after form submission
- type: assert
  config:
    assertConfig:
      assertType: consoleError
      negate: true
      customMessage: "Form submission should not produce JavaScript errors"
```

### Example 5: All List Items Visible

```yaml
# Assert all menu items are visible
- type: assertVisible
  config:
    assertConfig:
      assertType: visible
      collectionMode: all
      retryUntilPass: true
```

### Example 6: Authentication Token Stored

```yaml
# Assert JWT token is stored after login
- type: assert
  config:
    assertConfig:
      assertType: localStorage
      storageKey: "accessToken"
      matchMode: regex
      expectedValue: "^eyJ[A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+$"
```

### Example 7: Email Format Validation

```yaml
# Assert email field contains valid email
- type: assertValue
  config:
    assertConfig:
      assertType: value
      matchMode: regex
      expectedValue: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
      customMessage: "Email field should contain a valid email address"
```

### Example 8: Dynamic Content Loading

```yaml
# Wait for content to load and assert it exists
- type: assertText
  config:
    assertConfig:
      assertType: text
      expectedValue: "Loading complete"
      retryUntilPass: true
      retryIntervalMs: 1000
      maxRetries: 30
      assertTimeoutMs: 30000
```

---

## Tips and Best Practices

1. **Use `contains` over `equals` when possible** - More resilient to minor text changes

2. **Always set `customMessage`** - Makes debugging easier when tests fail

3. **Enable `screenshotOnFail` for critical assertions** - Visual evidence helps debugging

4. **Use `retryUntilPass` for dynamic content** - Avoids flaky tests from timing issues

5. **Prefer `softAssert` for non-critical checks** - Collect all failures instead of stopping at first

6. **Test regex patterns separately** - Use an online regex tester before adding to test

7. **Use collection modes appropriately**:
   - `all` when every element must match
   - `any` when at least one should match
   - `none` when no elements should match

8. **Set reasonable timeouts** - Don't wait too long, but don't be too aggressive

---

## Troubleshooting

### Assertion Always Fails

1. Check if element selector is correct
2. Verify expected value matches actual (check case sensitivity)
3. Enable `retryUntilPass` for dynamic content
4. Check if element is in an iframe (may need frame switching)

### Regex Not Matching

1. Remember to escape special characters: `\. \$ \( \)`
2. Use raw strings in JSON: `"\\d"` not `"\d"`
3. Test pattern in an online regex tester first
4. Check if `caseSensitive` affects your pattern

### Flaky Assertions

1. Enable `retryUntilPass` with appropriate intervals
2. Increase `assertTimeoutMs` for slow-loading content
3. Use `waitForCondition: true` (default)
4. Consider using `softAssert` and checking results at end

### Storage/Cookie Assertions Not Working

1. Ensure `storageKey` is set correctly
2. Check if storage is being set before assertion runs
3. Cookies may have domain/path restrictions
4. sessionStorage is tab-specific

---

*Documentation version: 2.0*
*Last updated: 2024*
