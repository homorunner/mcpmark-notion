from __future__ import annotations

from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, BrowserContext, Page


class NotionClient:
    """Utility helper for logging into Notion using Playwright.

    The helper **never** re-uses a previously saved ``notion_state.json``. Instead it
    forces a fresh login and overwrites the state file on every successful run. This
    guarantees that outdated or invalid sessions are not reused.

    Typical usage::

        from utils.notion_client import NotionClient

        client = NotionClient(url="https://www.notion.so/my-workspace", headless=False)
        context = client.login()  # Opens a browser window, waits for login
    """

    def __init__(
        self,
        *,
        url: str | None = None,
        headless: bool = True,
        state_path: Optional[str | Path] = None,
    ) -> None:
        """Create a new ``NotionClient``.

        Args:
            url: The Notion URL that should be opened after the browser launches. The
                 URL typically points to the template or workspace root that later
                 modules will operate on.
            headless: Whether Playwright should launch the browser in headless mode.
            state_path: Where to save the Playwright storage state after a successful
                 login. Defaults to ``<project-root>/notion_state.json``.
        """
        # Default to Notion's login page if no specific URL provided.
        self.url = url or "https://www.notion.so/login"
        self.headless = headless
        # Resolve default state file location lazily to the *current* project root
        self.state_path = Path(state_path or Path.cwd() / "notion_state.json").expanduser().resolve()

        self._browser_context: Optional[BrowserContext] = None
        self._playwright = None  # Late-bound Playwright instance
        self._browser = None  # Underlying Chromium browser instance

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    def login(self) -> BrowserContext:
        """Launch a browser, perform login, and save ``notion_state.json``.

        Returns:
            The active :class:`playwright.sync_api.BrowserContext` containing the
            fresh authenticated session. Call :py:meth:`close` when finished.
        """
        # Always start from a clean slate
        if self.state_path.exists():
            try:
                self.state_path.unlink()
            except OSError:
                # Not critical – continue but warn the user
                print(f"⚠️  Unable to remove existing state file: {self.state_path}")

        # Lazily start Playwright so that the BrowserContext remains valid until
        # the caller explicitly closes it. Using a "with" block would tear down
        # the browser immediately after this method returns.
        if self._playwright is None:
            self._playwright = sync_playwright().start()

        self._browser = self._playwright.chromium.launch(headless=self.headless)
        context = self._browser.new_context()
        page = context.new_page()

        print("🔗 Navigating to Notion URL…")
        page.goto(self.url, wait_until="load")

        if self.headless:
            # ------------------------------------------------------------------
            # Headless mode: guide the user via CLI prompts
            # ------------------------------------------------------------------
            self._handle_headless_login(context)
        else:
            # ------------------------------------------------------------------
            # Non-headless mode: let the user complete the flow manually
            # ------------------------------------------------------------------
            print(
                "A browser window has been opened.\n"
                "Please complete the Notion login in the UI.\n"
                "After you see your workspace / template page, return to this terminal "
                "and press <ENTER> to finish…"
            )
            initial_url = page.url
            input()

            # After user indicates login is done, wait (briefly) for possible redirects
            # so that cookies/localStorage are final. If URL did not change, we still
            # proceed – some accounts may land on the same page slug.
            try:
                page.wait_for_url(lambda u: u != initial_url, timeout=10_000)
            except PlaywrightTimeoutError:
                pass  # Not critical

        # Give the page a moment to settle (e.g., load workspace databases) – but
        # keep it short to avoid unnecessary waiting.
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5_000)
        except PlaywrightTimeoutError:
            pass

        # Persist authenticated storage *after* login completes
        context.storage_state(path=str(self.state_path))
        print(f"✅ Login successful – session saved to {self.state_path}")

        self._browser_context = context
        return context

    def close(self) -> None:
        """Close the underlying browser (if still running)."""
        # Close BrowserContext and Browser, then stop Playwright
        if self._browser_context is not None:
            try:
                self._browser_context.close()
            finally:
                self._browser_context = None

        if self._browser is not None:
            try:
                self._browser.close()
            finally:
                self._browser = None

        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _handle_headless_login(self, context: BrowserContext) -> None:
        """Perform login flow in headless mode.

        Strategy:
        1. Always navigate to https://www.notion.so/login.
        2. Interactively ask for email, press Enter (or click "Continue").
        3. Wait for the verification code form, ask for code, press Enter (or click "Continue").
        4. After authentication, if a target URL was provided, navigate to it.
        """
        page: Page = context.pages[0]

        # Navigate to dedicated login page to avoid iframe / overlay issues
        login_url = "https://www.notion.so/login"
        page.goto(login_url, wait_until="domcontentloaded")

        email = input("Notion email address: ").strip()

        try:
            # Use placeholder to find the email input
            email_input = page.locator('input[placeholder="Enter your email address..."]')
            email_input.wait_for(state="visible", timeout=120_000)
            email_input.fill(email)
            email_input.press("Enter")
        except PlaywrightTimeoutError:
            raise RuntimeError("Timed out waiting for email input to become available.")
        except Exception:
            # Fallback to clicking the "Continue" button if pressing Enter fails
            try:
                page.get_by_role("button", name="Continue", exact=True).click()
            except Exception as e:
                raise RuntimeError(f"Could not submit email via button. Error: {e}")

        try:
            # Wait for verification code input, placeholder is "Enter code"
            code_input = page.locator('input[placeholder="Enter code"]')
            code_input.wait_for(state="visible", timeout=120_000)
            code = input("Email verification code (check your inbox): ").strip()
            code_input.fill(code)
            code_input.press("Enter")
        except PlaywrightTimeoutError:
            raise RuntimeError("Timed out waiting for verification code input to become visible.")
        except Exception:
            # Fallback to clicking the "Continue" button
            try:
                page.get_by_role("button", name="Continue", exact=True).click()
            except Exception as e:
                raise RuntimeError(f"Could not submit verification code via button. Error: {e}")

        # Wait until we are redirected away from the login page (workspace loaded)
        try:
            page.wait_for_url(lambda url: url != login_url, timeout=180_000)
        except PlaywrightTimeoutError:
            print("⚠️  Login redirect timeout – proceeding to save state anyway…")

        # If a custom target was provided and differs from the login page, visit it so
        # that storage state also covers that origin.
        if self.url and self.url != login_url:
            page.goto(self.url, wait_until="domcontentloaded")

    # Allow the helper to be used as a context manager
    def __enter__(self) -> "NotionClient":
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 