from __future__ import annotations

import asyncio
import json
import re
import sys
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Page, FrameLocator, TimeoutError as PlaywrightTimeoutError

from recorder.schema.workflow import Workflow, Step, Locator
from recorder.services.workflow_store import load_workflow
from recorder.services.expression_engine import (
    get_variable_store, get_assertion_engine, ComparisonMode
)


def locator_to_selector(loc: Locator) -> str:
    if loc.type == "data":
        return loc.value if loc.value.startswith("[") else f"[data-testid=\"{loc.value}\"]"
    if loc.type == "aria":
        if loc.value.startswith("[aria-"):
            return loc.value
        return f"[aria-label=\"{loc.value}\"]"
    if loc.type == "label":
        return f"label:has-text('{loc.value}')"
    if loc.type == "text":
        return f"text={loc.value}"
    if loc.type == "xpath":
        return f"xpath={loc.value}"
    if loc.type == "id":
        return loc.value if loc.value.startswith("#") else f"#{loc.value}"
    if loc.type == "name":
        return loc.value if loc.value.startswith("[name") else f"[name=\"{loc.value}\"]"
    return loc.value


async def pick_locator_handle(context, current, locs: List[Locator]):
    """
    Try each locator in order and return a Locator that resolves.
    """
    for loc in sorted(locs, key=lambda l: l.score, reverse=True):
        selector = locator_to_selector(loc)
        handle = current.locator(selector)
        if await handle.count() > 0:
            return handle, loc
    raise RuntimeError("No locator matched target")


async def resolve_frame(page: Page, frame_path):
    current = page
    for frame_hint in frame_path:
        matched = None
        # Support both Pydantic FrameHint models and plain dicts
        if hasattr(frame_hint, 'name'):
            # Pydantic model: access attributes directly
            hint_name = frame_hint.name
            hint_id = frame_hint.id
            hint_src = frame_hint.src
            hint_locators = frame_hint.locators
        else:
            # Plain dict (e.g. from injected.js framePath)
            hints = frame_hint.get("hints", frame_hint)
            hint_name = hints.get("name")
            hint_id = hints.get("id")
            hint_src = hints.get("src")
            hint_locators = frame_hint.get("locators", [])

        for frame in current.frames:
            if hint_name and frame.name == hint_name:
                matched = frame
                break
            if hint_id and frame.url.find(hint_id) >= 0:
                matched = frame
                break
            if hint_src and frame.url.find(hint_src) >= 0:
                matched = frame
                break
        if matched:
            current = matched
            continue
        locs = [l if isinstance(l, Locator) else Locator(**l) for l in hint_locators]
        if locs:
            selector = locator_to_selector(locs[0])
            # Use locator to find the iframe element, then get its content frame
            iframe_element = current.locator(selector)
            content_frame = await iframe_element.content_frame()
            if content_frame:
                current = content_frame
        else:
            break
    return current


async def resolve_target(page: Page, step: Step):
    frame = await resolve_frame(page, step.framePath)
    current_locator = frame.locator("body")
    # shadow hosts
    for host in step.shadowPath:
        # Support both Pydantic ShadowHost models and plain dicts
        if hasattr(host, 'locators'):
            host_locators = host.locators
        else:
            host_locators = host.get("locators", [])
        locs = [Locator(**l) if isinstance(l, dict) else l for l in host_locators]
        handle, _ = await pick_locator_handle(page.context, current_locator, locs)
        current_locator = handle
    locators = step.target.locators if step.target else []
    handle, used = await pick_locator_handle(page.context, current_locator, locators)
    return handle, used


async def apply_waits(target, waits: List[Dict[str, Any]]):
    for w in waits:
        kind = w.get("kind")
        timeout = w.get("timeoutMs", 5000)
        if kind == "visible":
            await target.wait_for(state="visible", timeout=timeout)
        elif kind == "attached":
            await target.wait_for(state="attached", timeout=timeout)
        elif kind == "hidden" or kind == "gone":
            await target.wait_for(state="hidden", timeout=timeout)


def parse_number(text: str) -> float:
    """Extract numeric value from text (handles currency, commas, etc.)"""
    if text is None:
        return 0.0
    # Remove currency symbols, commas, spaces
    cleaned = re.sub(r'[^\d.\-]', '', str(text))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def get_comparison_mode(mode_str: str) -> ComparisonMode:
    """Convert string to ComparisonMode enum"""
    mode_map = {
        "equals": ComparisonMode.EQUALS,
        "notEquals": ComparisonMode.NOT_EQUALS,
        "greaterThan": ComparisonMode.GREATER_THAN,
        "greaterOrEqual": ComparisonMode.GREATER_OR_EQUAL,
        "lessThan": ComparisonMode.LESS_THAN,
        "lessOrEqual": ComparisonMode.LESS_OR_EQUAL,
        "contains": ComparisonMode.CONTAINS,
        "notContains": ComparisonMode.NOT_CONTAINS,
        "startsWith": ComparisonMode.STARTS_WITH,
        "endsWith": ComparisonMode.ENDS_WITH,
        "matchesRegex": ComparisonMode.MATCHES_REGEX,
        "between": ComparisonMode.BETWEEN,
    }
    return mode_map.get(mode_str, ComparisonMode.EQUALS)


async def run_step(page: Page, step: Step):
    var_store = get_variable_store()
    calc_engine = get_assertion_engine()

    # Handle variable/calculation steps that may not need a target
    if step.type == "setVariable":
        # Set variable to a literal value or expression result
        var_config = step.config.variable if step.config and step.config.variable else None
        if var_config:
            var_name = var_config.variableName
            value = step.input.get("value", "") if step.input else ""
            # If value looks like an expression, evaluate it
            if "${" in value:
                result = calc_engine.evaluate_only(value)
                var_store.set(var_name, result.calculated_value, source="expression")
            else:
                # Try to parse as number, fallback to string
                try:
                    var_store.set(var_name, float(value) if '.' in value else int(value), source="manual")
                except ValueError:
                    var_store.set(var_name, value, source="manual")
        return None

    if step.type == "evaluate":
        # Just evaluate an expression, optionally store result
        calc_config = step.config.calculate if step.config and step.config.calculate else None
        if calc_config:
            result = calc_engine.evaluate_only(calc_config.expression)
            if calc_config.storeResultAs:
                var_store.set(calc_config.storeResultAs, result.calculated_value, source="calculated")
            print(f"[evaluate] {calc_config.expression} = {result.calculated_value}")
        return None

    # Steps that need a target element
    target, used_locator = await resolve_target(page, step)
    await apply_waits(target, [w.model_dump() if hasattr(w, "model_dump") else w for w in step.waits])

    if step.type in ["click", "dblclick", "contextmenu", "hover"]:
        await getattr(target, step.type)()

    elif step.type == "type":
        value = step.input.get("value") if step.input else ""
        await target.fill("")
        await target.type(value)

    elif step.type == "press":
        keys = step.input.get("keys") if step.input else ""
        await target.press(keys)

    elif step.type == "selectOption":
        value = step.input.get("value") if step.input else ""
        await target.select_option(value)

    elif step.type == "scroll":
        await target.scroll_into_view_if_needed()

    elif step.type == "wait":
        await asyncio.sleep(float(step.input.get("value", 0.5)) if step.input else 0.5)

    elif step.type == "extractVariable":
        # Extract value from element and store in variable
        var_config = step.config.variable if step.config and step.config.variable else None
        if var_config:
            var_name = var_config.variableName
            extract_from = var_config.extractFrom

            if extract_from == "text":
                value = await target.text_content()
            elif extract_from == "value":
                value = await target.input_value()
            elif extract_from == "attribute" and var_config.attributeName:
                value = await target.get_attribute(var_config.attributeName)
            elif extract_from == "count":
                value = await target.count()
            else:
                value = await target.text_content()

            # Apply regex if specified
            if var_config.regexPattern and value:
                match = re.search(var_config.regexPattern, str(value))
                if match:
                    value = match.group(var_config.regexGroup)

            # Try to parse as number
            if value and re.match(r'^[\d.,\-\$\€\£\s]+$', str(value)):
                value = parse_number(value)

            var_store.set(var_name, value, source="extracted", element_selector=str(used_locator))
            print(f"[extractVariable] ${var_name} = {value}")

    elif step.type == "calculateAssert":
        # Evaluate expression and compare with actual value
        calc_config = step.config.calculate if step.config and step.config.calculate else None
        if calc_config:
            # Get actual value
            if calc_config.actualValueFrom == "element":
                actual_text = await target.text_content()
                actual_value = parse_number(actual_text)
            elif calc_config.actualValueFrom == "variable" and calc_config.actualVariableName:
                actual_value = var_store.get(calc_config.actualVariableName)
            elif calc_config.actualValueFrom == "expression" and calc_config.actualExpression:
                expr_result = calc_engine.evaluate_only(calc_config.actualExpression)
                actual_value = expr_result.calculated_value
            else:
                actual_text = await target.text_content()
                actual_value = parse_number(actual_text)

            # Perform assertion
            comparison_mode = get_comparison_mode(calc_config.comparisonMode)
            result = calc_engine.assert_expression(
                calc_config.expression,
                actual_value,
                comparison_mode,
                calc_config.tolerance
            )

            # Store result if requested
            if calc_config.storeResultAs:
                var_store.set(calc_config.storeResultAs, result.calculated_value, source="calculated")

            # Log result
            status = "PASS" if result.success else "FAIL"
            print(f"[calculateAssert] {status}: {calc_config.expression} = {result.calculated_value}, actual = {actual_value}")

            if not result.success and not calc_config.softAssert:
                msg = calc_config.customMessage or f"Calculated assertion failed: expected {result.calculated_value}, got {actual_value}"
                raise AssertionError(msg)

    # Standard assertions
    for assertion in step.assertions:
        kind = assertion.kind
        if kind == "textContains" and assertion.value:
            await target.wait_for(state="visible")
            txt = await target.text_content()
            assert assertion.value in (txt or "")
        if kind == "exists":
            await target.wait_for(state="visible")

    return used_locator


async def run_workflow(workflow: Workflow):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        if workflow.meta.get("baseUrl"):
            await page.goto(workflow.meta["baseUrl"])
        for step in workflow.steps:
            try:
                await run_step(page, step)
            except PlaywrightTimeoutError:
                print(f"[fail] timeout on step {step.id} {step.name}")
                break
            except Exception as exc:
                print(f"[fail] step {step.id} {step.name}: {exc}")
                break
        await browser.close()


def load_workflow_path(path: str) -> Workflow:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Workflow(**data)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m replay.replayer <workflow.json>")
        sys.exit(1)
    path = sys.argv[1]
    wf = load_workflow_path(path)
    asyncio.run(run_workflow(wf))


if __name__ == "__main__":
    main()

