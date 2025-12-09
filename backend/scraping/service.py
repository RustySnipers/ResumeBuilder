"""
Web Scraping Service.

Handles scraping of content from URLs, with specific logic for LinkedIn.
"""

import logging
import asyncio
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class ScraperService:
    """Service for scraping web pages."""

    def __init__(self):
        self.playwright = None
        self.browser = None

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape content from a generic URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            Dictionary with title, content, etc.
        """
        try:
            from playwright.async_api import async_playwright
            from bs4 import BeautifulSoup
        except ImportError:
            return {"error": "Scraping dependencies missing (playwright, beautifulsoup4)."}

        logger.info(f"Scraping URL: {url}")
        
        data = {"url": url, "content": "", "title": ""}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Set user agent to avoid basic blocking
                await page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                })
                
                await page.goto(url, timeout=30000, wait_until="networkidle")
                
                title = await page.title()
                content = await page.content()
                
                # Parse with BS4 to get clean text
                soup = BeautifulSoup(content, 'html.parser')
                
                # Remove scripts, styles
                for script in soup(["script", "style"]):
                    script.decompose()
                    
                text = soup.get_text(separator='\n')
                
                # Collapse whitespace
                clean_text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
                
                data["title"] = title
                data["content"] = clean_text
                
            except Exception as e:
                logger.error(f"Playwright error scraping {url}: {e}")
                data["error"] = str(e)
            finally:
                await browser.close()
                
        return data

    async def scrape_linkedin(self, profile_url: str) -> Dict[str, Any]:
        """
        Attempt to scrape a LinkedIn profile.
        
        Note: LinkedIn is extremely aggressive against scrapers. 
        This is a best-effort local attempt.
        """
        # For now, treat it as a generic URL but maybe add specific selectors if we knew them.
        # Ideally, we would ask the user for their cookie 'li_at' to bypass login wall.
        return await self.scrape_url(profile_url)
