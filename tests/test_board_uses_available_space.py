"""Regression test: the board must actually use the available viewport,
not sit at a small fixed size regardless of screen width.

Before this fix, --cell-size was clamp(32px, 9.2vw, 50px): on phones this
filled only ~86-94% of the width, and past ~600px wide it hit the 50px cap
and simply stopped growing -- a 1024px-wide window still showed the same
464px board (45% fill) as a 600px-wide one. Tuned to clamp(30px, 9.8vw,
74px) with the surrounding panel widened to match, empirically verified
across 300-1280px to have zero horizontal overflow while filling ~90-96%
of phone widths and growing well past the old fixed cap on larger screens.
"""
import sys

from playwright.sync_api import sync_playwright

from _helpers import launch_browser, serve_repo


def main():
    failures = []

    with serve_repo() as base_url, sync_playwright() as p:
        browser = launch_browser(p)

        widths = [320, 360, 390, 414, 428, 600, 768, 1024]
        board_widths = {}

        for w in widths:
            page = browser.new_page(viewport={"width": w, "height": 900})
            page.goto(f"{base_url}/index.html", wait_until="networkidle")
            page.wait_for_function("() => document.querySelectorAll('.cell').length === 81")
            page.wait_for_timeout(150)

            data = page.evaluate(
                """() => {
                    const b = document.getElementById('board').getBoundingClientRect();
                    const overflow = document.documentElement.scrollWidth - window.innerWidth;
                    return { boardW: b.width, overflow };
                }"""
            )
            page.close()

            board_widths[w] = data["boardW"]
            if data["overflow"] > 1:
                failures.append(f"At {w}px, the board caused {data['overflow']:.1f}px of horizontal overflow")

            fill_pct = data["boardW"] / w * 100
            min_fill = 88 if w <= 428 else 60
            if fill_pct < min_fill:
                failures.append(f"At {w}px, board only filled {fill_pct:.1f}% of the width (expected >= {min_fill}%)")

        # The board must actually keep growing on wider screens, not plateau
        # at a small fixed size the way it used to past ~600px.
        if board_widths[1024] < board_widths[600] + 50:
            failures.append(
                f"Board did not grow meaningfully between 600px ({board_widths[600]:.0f}px board) "
                f"and 1024px ({board_widths[1024]:.0f}px board) viewports"
            )
        if board_widths[1024] < 600:
            failures.append(f"At 1024px viewport width, board is only {board_widths[1024]:.0f}px -- still capped small")

        browser.close()

    if failures:
        print("FAIL: board is not using available space:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: the board fills most of the viewport on phones and keeps growing on larger screens, with no overflow")


if __name__ == "__main__":
    main()
