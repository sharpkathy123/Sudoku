"""Regression test for the generated app icon.

The Apple Touch Icon is drawn on a <canvas> at load time
(index.html, generateAppleTouchIcon) and exported as a data: URL. A
copy-paste bug once left one of the four internal grid dividers
stopping two-thirds of the way across (lineTo(115, 115) instead of
lineTo(158, 115)), so the icon rendered with a visibly broken 3x3
grid — the divider between the middle and bottom rows had no line
under the rightmost cell.

This decodes the actual generated icon and samples pixels along all
four internal dividers, so a similarly truncated line fails a test
instead of just shipping unnoticed.
"""
import sys

from playwright.sync_api import sync_playwright

from _helpers import launch_browser, serve_repo

# Positions sampled along each divider line, within the icon's 22-158
# drawn area (kept away from the 22/158 endpoints to avoid corner
# anti-aliasing from the outer border stroke).
SAMPLE_POSITIONS = [30, 60, 90, 120, 150]


def pixel_is_dark(rgba):
    r, g, b, a = rgba
    return a > 200 and r < 100 and g < 100 and b < 100


def main():
    with serve_repo() as base_url, sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page()
        page.goto(f"{base_url}/index.html", wait_until="networkidle")

        href = page.evaluate(
            "() => document.querySelector('link[rel=\"apple-touch-icon\"]')?.href"
        )
        assert href and href.startswith("data:image/png"), "No apple-touch-icon data URL found"

        lines = page.evaluate(
            """
            async ({ href, points }) => {
                const img = new Image();
                await new Promise((resolve, reject) => {
                    img.onload = resolve;
                    img.onerror = reject;
                    img.src = href;
                });
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);

                const lineDefs = [
                    { name: 'vertical divider x=67',    points: points.map(t => [67, t]) },
                    { name: 'vertical divider x=115',   points: points.map(t => [115, t]) },
                    { name: 'horizontal divider y=67',  points: points.map(t => [t, 67]) },
                    { name: 'horizontal divider y=115', points: points.map(t => [t, 115]) },
                ];
                return lineDefs.map(line => ({
                    name: line.name,
                    samples: line.points.map(([x, y]) => ({
                        at: [x, y],
                        rgba: Array.from(ctx.getImageData(x, y, 1, 1).data),
                    })),
                }));
            }
            """,
            {"href": href, "points": SAMPLE_POSITIONS},
        )

        browser.close()

    failures = []
    for line in lines:
        for sample in line["samples"]:
            if not pixel_is_dark(sample["rgba"]):
                failures.append(
                    f"{line['name']} at {tuple(sample['at'])}: pixel {sample['rgba']} "
                    f"is not dark — the line has a gap here"
                )

    if failures:
        print("FAIL: app icon's 3x3 grid has a broken/missing divider line:")
        for f in failures:
            print("  -", f)
        sys.exit(1)

    print("PASS: app icon's 3x3 grid is fully connected on all 4 internal dividers")


if __name__ == "__main__":
    main()
