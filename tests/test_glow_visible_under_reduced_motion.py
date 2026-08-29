"""Regression test: completion glow and the hint arrival-glow must still
be visible under prefers-reduced-motion, not just collapsed to nothing.

Reported live: with iOS Reduce Motion on, unit-completion glow appeared
to have vanished entirely, and a hint's target cell was momentarily hard
to spot without its usual pulse drawing the eye. Root cause: the earlier
prefers-reduced-motion fix collapsed *every* animation's duration to
0.001ms globally -- which doesn't just remove the pulsing motion, it
makes the glow complete so fast nobody can ever actually see it. That
silently deletes real state feedback (a just-completed unit, a hint's
target), which isn't what "reduced motion" is supposed to mean -- it
should mean no distracting pulsing, not no acknowledgment at all.

Fixed with a specific reduced-motion override for .glow: a plain,
non-animated box-shadow ring that stays visible for the same ~2s window
the JS-driven .glow class is present, instead of an imperceptible flash.
"""
import sys

from playwright.sync_api import sync_playwright

from _helpers import launch_browser, serve_repo


def parse_alpha(box_shadow: str) -> float:
    # e.g. "rgba(0, 150, 255, 0.85) 0px 0px 0px 3px"
    inside = box_shadow.split("(")[1].split(")")[0]
    return float(inside.split(",")[-1])


def main():
    failures = []

    with serve_repo() as base_url, sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page()
        page.emulate_media(reduced_motion="reduce")
        page.on("pageerror", lambda e: failures.append(f"page error: {e}"))
        page.goto(f"{base_url}/index.html", wait_until="networkidle")
        page.wait_for_function(
            "() => document.querySelectorAll('.cell').length === 81 "
            "&& !document.getElementById('status').textContent.includes('Generating')"
        )
        page.wait_for_timeout(300)

        # Complete row 0 for real, leaving the glow-triggering placement last.
        empties = page.evaluate(
            """() => {
                const grid = getCurrentGrid();
                const out = [];
                for (let c = 0; c < 9; c++) if (grid[0][c] === 0) out.push(c);
                return out;
            }"""
        )
        for c in empties[:-1]:
            digit = page.evaluate(f"() => solution[0][{c}]")
            page.locator(".cell").nth(c).click()
            page.wait_for_timeout(20)
            page.locator("#numberBar .number-tile").nth(digit - 1).click()
            page.wait_for_timeout(20)
        last_c = empties[-1]
        last_digit = page.evaluate(f"() => solution[0][{last_c}]")
        page.locator(".cell").nth(last_c).click()
        page.wait_for_timeout(20)
        page.locator("#numberBar .number-tile").nth(last_digit - 1).click()
        page.wait_for_timeout(150)

        completion_shadow = page.evaluate(
            "() => getComputedStyle(document.querySelectorAll('.cell')[0]).boxShadow"
        )
        if completion_shadow in ("none", "", None) or parse_alpha(completion_shadow) < 0.3:
            failures.append(f"Completion glow isn't visibly present under reduced motion: {completion_shadow!r}")

        # Hint glow.
        page.click("#HintBtn")
        page.wait_for_timeout(150)
        hint_shadow = page.evaluate(
            """() => {
                const cell = document.querySelector('.cell.hint-trace');
                return cell ? getComputedStyle(cell).boxShadow : null;
            }"""
        )
        if not hint_shadow or hint_shadow == "none" or parse_alpha(hint_shadow) < 0.3:
            failures.append(f"Hint glow isn't visibly present under reduced motion: {hint_shadow!r}")

        # The underlying animation itself should still be suppressed (no
        # actual pulsing motion) -- reduced motion should stay respected.
        anim_duration = page.evaluate(
            """() => {
                const cell = document.createElement('div');
                cell.className = 'cell glow';
                document.body.appendChild(cell);
                const d = getComputedStyle(cell).animationDuration;
                cell.remove();
                return d;
            }"""
        )
        if float(anim_duration.rstrip("s")) > 0.01:
            failures.append(f"glow's animation-duration isn't suppressed under reduced motion: {anim_duration!r}")

        browser.close()

    if failures:
        print("FAIL: glow isn't properly visible under reduced motion:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: completion and hint glow stay visible (as a steady ring) under reduced motion, without the pulsing animation")


if __name__ == "__main__":
    main()
