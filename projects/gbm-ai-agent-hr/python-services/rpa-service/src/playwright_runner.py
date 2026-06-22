from playwright.async_api import async_playwright


class PlaywrightBrowser:
    """Basic async Playwright browser wrapper."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._p = None
        self._browser = None
        self._page = None

    async def launch(self):
        self._p = await async_playwright().start()
        self._browser = await self._p.chromium.launch(headless=self.headless)
        self._page = await self._browser.new_page()
        return self

    async def close(self):
        if self._page:
            await self._page.close()
        if self._browser:
            await self._browser.close()
        if self._p:
            await self._p.stop()

    async def goto(self, url: str):
        await self._page.goto(url)
        return await self._page.title()

    async def click(self, selector: str):
        await self._page.click(selector)

    async def __aenter__(self):
        await self.launch()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
