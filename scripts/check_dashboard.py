"""Optional Playwright browser verification; never part of the agent's runtime.

Run after serving site/ at 127.0.0.1:8765. Install playwright and its Chromium
separately; the dashboard itself has no browser-package or backend dependency.
"""

import argparse
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765/")
    parser.add_argument("--screenshots", type=Path, default=Path("docs/assets"))
    args = parser.parse_args()
    args.screenshots.mkdir(parents=True, exist_ok=True)
    origin = urlsplit(args.url).netloc
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1080}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

        def local_only(route):
            if urlsplit(route.request.url).netloc != origin:
                errors.append("Unexpected external request")
                route.abort()
            else:
                route.continue_()

        page.route("**/*", local_only)
        response = page.goto(args.url)
        assert response.status == 200
        page.locator("#load-status").filter(has_text="artifact loaded").wait_for()
        assert page.locator("#metrics tr").count() == 5
        assert "16" in page.locator("#configs").inner_text()
        page.screenshot(path=str(args.screenshots / "dashboard-desktop.png"), full_page=True)
        page.screenshot(path=str(args.screenshots / "dashboard-overview.png"))
        for profile in ("reference", "adversarial"):
            page.select_option("#profile", profile)
            for category in (
                "all",
                "prompt_injection",
                "tool_manipulation",
                "conflicting_evidence",
            ):
                page.select_option("#category", category)
                assert page.locator("#configs article").count() == 3
            for scenario in ("pi-004", "pi-010", "tm-002", "tm-007", "ce-001", "ce-010"):
                page.select_option("#scenario", scenario)
                for mode in ("baseline", "guarded", "guarded_oversight"):
                    page.select_option("#mode", mode)
                    assert page.locator("#trace-id").inner_text() == scenario
                    assert page.locator("#timeline details").count() > 0
        page.select_option("#profile", "adversarial")
        page.select_option("#category", "all")
        page.select_option("#scenario", "pi-010")
        page.select_option("#mode", "guarded_oversight")
        page.locator("#traces").scroll_into_view_if_needed()
        page.screenshot(path=str(args.screenshots / "dashboard-trace.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        page.evaluate("window.scrollTo(0, 0)")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(args.screenshots / "dashboard-mobile.png"), full_page=True)
        # Regression probe: untrusted HTML must stay inert in the trace viewer.
        page.evaluate("""() => {
            const row = data.profiles.adversarial.examples.find(
                r => r.scenario_id === 'pi-010' && r.mode === 'guarded_oversight');
            row.execution.trace[0].data = {
                html: '<img src=x onerror="window.demoXssExecuted=true">'
            };
            renderTrace();
        }""")
        assert page.locator("#timeline img").count() == 0
        assert page.evaluate("window.demoXssExecuted !== true")
        assert not errors, errors
        browser.close()
    print(
        "Dashboard browser checks passed: filters, 36 trace selections, mobile overflow, no errors."
    )


if __name__ == "__main__":
    main()
