import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Initialize FastMCP server
mcp = FastMCP("browser-automation")

# Global state
browser: Optional[Browser] = None
context: Optional[BrowserContext] = None
page: Optional[Page] = None
playwright = None

async def ensure_browser():
    """Ensure the browser is running."""
    global browser, context, page, playwright
    if not playwright:
        playwright = await async_playwright().start()
    
    if not browser:
        # Launch headed so user can see what's happening (transparency/safety)
        browser = await playwright.chromium.launch(headless=False)
        
    if not context:
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
    if not page:
        page = await context.new_page()

@mcp.tool()
async def navigate(url: str) -> str:
    """Navigate to a specific URL."""
    await ensure_browser()
    if page:
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        return f"Navigated to {url}"
    return "Error: Page not initialized"

@mcp.tool()
async def get_content() -> str:
    """Get the text content of the current page."""
    await ensure_browser()
    if page:
        # Get visible text only to reduce noise
        return await page.evaluate("document.body.innerText")
    return "Error: Page not initialized"

@mcp.tool()
async def click(selector: str) -> str:
    """Click an element matching the selector."""
    await ensure_browser()
    if page:
        try:
            await page.click(selector)
            return f"Clicked {selector}"
        except Exception as e:
            return f"Error clicking {selector}: {str(e)}"
    return "Error: Page not initialized"

@mcp.tool()
async def type_text(selector: str, text: str) -> str:
    """Type text into an element matching the selector."""
    await ensure_browser()
    if page:
        try:
            await page.fill(selector, text)
            return f"Typed text into {selector}"
        except Exception as e:
            return f"Error typing into {selector}: {str(e)}"
    return "Error: Page not initialized"

@mcp.tool()
async def scroll(direction: str = "down") -> str:
    """Scroll the page 'up' or 'down'."""
    await ensure_browser()
    if page:
        if direction == "down":
            await page.evaluate("window.scrollBy(0, 500)")
        else:
            await page.evaluate("window.scrollBy(0, -500)")
        return f"Scrolled {direction}"
    return "Error: Page not initialized"

@mcp.tool()
async def google_search(query: str) -> str:
    """Perform a Google search and return the results."""
    await ensure_browser()
    if page:
        # Navigate to Google
        await page.goto(f"https://www.google.com/search?q={query}")
        await page.wait_for_load_state("domcontentloaded")
        
        # Extract results (simple extraction)
        results = await page.evaluate("""() => {
            const items = document.querySelectorAll('.g');
            return Array.from(items).map(item => {
                const title = item.querySelector('h3')?.innerText || '';
                const link = item.querySelector('a')?.href || '';
                const snippet = item.querySelector('.VwiC3b')?.innerText || '';
                return `Title: ${title}\nLink: ${link}\nSnippet: ${snippet}\n---`;
            }).join('\\n');
        }""")
        
        return results
    return "Error: Page not initialized"

if __name__ == "__main__":
    mcp.run()
