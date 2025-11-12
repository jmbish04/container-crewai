# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Computer Use integration for browser automation.

This module provides browser automation capabilities using Gemini's
Computer Use features with Playwright for LinkedIn job scraping and
other web automation tasks.
"""

import asyncio
import base64
import os
from io import BytesIO
from typing import Dict, List, Optional, Any
from enum import Enum

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from PIL import Image
import google.generativeai as genai


class BrowserEnvironment(str, Enum):
    """Browser environment options."""
    PLAYWRIGHT = "playwright"
    BROWSERBASE = "browserbase"


class ComputerUseAgent:
    """
    Browser automation agent using Gemini Computer Use.

    This agent can control a browser using natural language instructions
    powered by Gemini's vision and reasoning capabilities.
    """

    def __init__(
        self,
        environment: BrowserEnvironment = BrowserEnvironment.PLAYWRIGHT,
        initial_url: str = "https://www.google.com",
        highlight_mouse: bool = False,
        headless: bool = True,
        api_key: Optional[str] = None,
        linkedin_username: Optional[str] = None,
        linkedin_password: Optional[str] = None
    ):
        """
        Initialize the Computer Use Agent.

        Args:
            environment: Browser environment (playwright or browserbase)
            initial_url: Initial URL to load
            highlight_mouse: Whether to highlight mouse cursor
            headless: Whether to run browser in headless mode
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            linkedin_username: LinkedIn username (defaults to LINKEDIN_USERNAME env var)
            linkedin_password: LinkedIn password (defaults to LINKEDIN_PASSWORD env var)
        """
        self.environment = environment
        self.initial_url = initial_url
        self.highlight_mouse = highlight_mouse
        self.headless = headless

        # Get API key
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be set")

        # LinkedIn credentials (from Cloudflare Worker secrets)
        self.linkedin_username = linkedin_username or os.environ.get("LINKEDIN_USERNAME")
        self.linkedin_password = linkedin_password or os.environ.get("LINKEDIN_PASSWORD")

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", 'gemini-2.0-flash-exp'))

        # Browser state
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self._authenticated = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Start the browser."""
        if self.environment == BrowserEnvironment.PLAYWRIGHT:
            await self._start_playwright()
        elif self.environment == BrowserEnvironment.BROWSERBASE:
            await self._start_browserbase()
        else:
            raise ValueError(f"Unsupported environment: {self.environment}")

    async def _start_playwright(self):
        """Start Playwright browser."""
        self.playwright = await async_playwright().start()

        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )

        # Create context and page
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()

        # Navigate to initial URL
        await self.page.goto(self.initial_url)

    async def _start_browserbase(self):
        """Start Browserbase session."""
        api_key = os.environ.get("BROWSERBASE_API_KEY")
        project_id = os.environ.get("BROWSERBASE_PROJECT_ID")

        if not api_key or not project_id:
            raise ValueError("BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID must be set")

        # Connect to Browserbase
        # This is a placeholder - actual Browserbase connection would go here
        raise NotImplementedError("Browserbase support coming soon")

    async def close(self):
        """Close the browser and cleanup resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def take_screenshot(self) -> bytes:
        """
        Take a screenshot of the current page.

        Returns:
            Screenshot as bytes
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        screenshot = await self.page.screenshot(full_page=False)
        return screenshot

    async def get_screenshot_base64(self) -> str:
        """
        Get base64-encoded screenshot.

        Returns:
            Base64-encoded screenshot string
        """
        screenshot = await self.take_screenshot()
        return base64.b64encode(screenshot).decode('utf-8')

    async def execute_action(self, action: str) -> Dict[str, Any]:
        """
        Execute a browser action based on natural language instruction.

        Args:
            action: Natural language description of action to perform

        Returns:
            Result dictionary with success status and details
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        try:
            # Take screenshot for context
            screenshot_b64 = await self.get_screenshot_base64()

            # Create prompt for Gemini
            prompt = f"""
            You are controlling a web browser. Current task: {action}

            Based on the screenshot, provide specific actions to take.
            Respond with a JSON object containing:
            - action_type: "click", "type", "scroll", "navigate", "extract", or "wait"
            - details: object with action-specific details
            - reasoning: brief explanation of why this action

            For example:
            {{"action_type": "click", "details": {{"selector": "button.search"}}, "reasoning": "Click the search button"}}
            {{"action_type": "type", "details": {{"selector": "input.search", "text": "hello"}}, "reasoning": "Type in search box"}}
            """

            # Get action from Gemini
            response = await self._query_gemini(prompt, screenshot_b64)

            # Parse and execute the action
            result = await self._execute_browser_action(response)

            return {
                "success": True,
                "action": action,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "action": action,
                "error": str(e)
            }

    async def _query_gemini(self, prompt: str, screenshot_b64: str) -> Dict[str, Any]:
        """
        Query Gemini with screenshot and prompt.

        Args:
            prompt: Text prompt
            screenshot_b64: Base64-encoded screenshot

        Returns:
            Parsed response from Gemini
        """
        # Decode screenshot
        screenshot_bytes = base64.b64decode(screenshot_b64)
        image = Image.open(BytesIO(screenshot_bytes))

        # Query Gemini
        response = self.model.generate_content([prompt, image])

        # Parse response (simplified - actual implementation would be more robust)
        import json
        try:
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            # Fallback if response isn't JSON
            return {
                "action_type": "extract",
                "details": {"text": response.text},
                "reasoning": "Direct response from model"
            }

    async def _execute_browser_action(self, action: Dict[str, Any]) -> str:
        """
        Execute a browser action.

        Args:
            action: Action dictionary from Gemini

        Returns:
            Result message
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        action_type = action.get("action_type")
        details = action.get("details", {})

        if action_type == "click":
            selector = details.get("selector")
            await self.page.click(selector)
            return f"Clicked element: {selector}"

        elif action_type == "type":
            selector = details.get("selector")
            text = details.get("text")
            await self.page.fill(selector, text)
            return f"Typed '{text}' into {selector}"

        elif action_type == "scroll":
            direction = details.get("direction", "down")
            amount = details.get("amount", 500)
            await self.page.evaluate(f"window.scrollBy(0, {amount if direction == 'down' else -amount})")
            return f"Scrolled {direction} by {amount}px"

        elif action_type == "navigate":
            url = details.get("url")
            await self.page.goto(url)
            return f"Navigated to {url}"

        elif action_type == "extract":
            selector = details.get("selector", "body")
            text = await self.page.text_content(selector)
            return text or "No text found"

        elif action_type == "wait":
            duration = details.get("duration", 1000)
            await asyncio.sleep(duration / 1000)
            return f"Waited {duration}ms"

        else:
            return f"Unknown action type: {action_type}"

    async def login_linkedin(self) -> bool:
        """
        Log in to LinkedIn using stored credentials.

        Returns:
            True if login successful, False otherwise
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        if not self.linkedin_username or not self.linkedin_password:
            raise ValueError("LinkedIn credentials not provided. Set LINKEDIN_USERNAME and LINKEDIN_PASSWORD")

        if self._authenticated:
            return True

        try:
            # Navigate to LinkedIn login
            await self.page.goto("https://www.linkedin.com/login")
            await self.page.wait_for_load_state("networkidle")

            # Fill in username
            await self.page.fill('input[name="session_key"]', self.linkedin_username)

            # Fill in password
            await self.page.fill('input[name="session_password"]', self.linkedin_password)

            # Click sign in button
            await self.page.click('button[type="submit"]')

            # Wait for navigation to complete
            await self.page.wait_for_load_state("networkidle", timeout=15000)

            # Check if login was successful
            current_url = self.page.url
            if "feed" in current_url or "mynetwork" in current_url or "checkpoint" not in current_url:
                self._authenticated = True
                return True
            else:
                # Might need to handle 2FA or verification
                return False

        except Exception as e:
            raise RuntimeError(f"LinkedIn login failed: {e}")

    async def search_linkedin_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        experience_level: Optional[str] = None,
        job_type: Optional[str] = None,
        max_results: int = 20,
        require_auth: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search LinkedIn for jobs using browser automation.

        Args:
            keywords: Job search keywords
            location: Job location
            experience_level: Experience level filter
            job_type: Job type filter (Full-time, Remote, etc.)
            max_results: Maximum number of results
            require_auth: Whether to authenticate before searching (gets more detailed results)

        Returns:
            List of job dictionaries
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        # Authenticate if requested and not already authenticated
        if require_auth and not self._authenticated:
            await self.login_linkedin()

        jobs = []

        try:
            # Build LinkedIn search URL
            import urllib.parse
            search_query = " ".join(keywords)
            linkedin_url = f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(search_query)}"

            if location:
                linkedin_url += f"&location={urllib.parse.quote(location)}"

            # Add experience level filter if provided
            if experience_level:
                # LinkedIn experience level codes
                exp_map = {
                    "Internship": "1",
                    "Entry level": "2",
                    "Associate": "3",
                    "Mid-Senior level": "4",
                    "Director": "5",
                    "Executive": "6"
                }
                if experience_level in exp_map:
                    linkedin_url += f"&f_E={exp_map[experience_level]}"

            # Add job type filter if provided
            if job_type:
                # LinkedIn job type codes
                type_map = {
                    "Full-time": "F",
                    "Part-time": "P",
                    "Contract": "C",
                    "Temporary": "T",
                    "Volunteer": "V",
                    "Internship": "I"
                }
                if job_type in type_map:
                    linkedin_url += f"&f_JT={type_map[job_type]}"

            # Navigate to LinkedIn jobs
            await self.page.goto(linkedin_url)
            await self.page.wait_for_load_state("networkidle")

            # Wait for job listings to load
            try:
                await self.page.wait_for_selector(".job-search-card", timeout=10000)
            except Exception:
                # Try alternative selector
                await self.page.wait_for_selector(".jobs-search__results-list", timeout=10000)

            # Scroll to load more jobs
            for _ in range(min(3, max_results // 10)):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

            # Extract job listings - try multiple selectors
            job_cards = await self.page.query_selector_all(".job-search-card")
            if not job_cards:
                job_cards = await self.page.query_selector_all(".jobs-search-results__list-item")

            for i, card in enumerate(job_cards[:max_results]):
                try:
                    # Extract job details - multiple selector strategies
                    title_elem = (await card.query_selector(".job-card-list__title") or
                                 await card.query_selector("h3.job-search-card__title") or
                                 await card.query_selector("a.job-card-container__link"))

                    company_elem = (await card.query_selector(".job-card-container__company-name") or
                                   await card.query_selector(".job-search-card__subtitle-link"))

                    location_elem = (await card.query_selector(".job-card-container__metadata-item") or
                                    await card.query_selector(".job-search-card__location"))

                    link_elem = await card.query_selector("a")

                    # Get text content
                    title = await title_elem.text_content() if title_elem else "N/A"
                    company = await company_elem.text_content() if company_elem else "N/A"
                    job_location = await location_elem.text_content() if location_elem else "N/A"
                    link = await link_elem.get_attribute("href") if link_elem else "N/A"

                    # Extract additional details if authenticated
                    description = None
                    salary_range = None

                    if self._authenticated:
                        # Try to get more details
                        try:
                            desc_elem = await card.query_selector(".job-search-card__snippet")
                            if desc_elem:
                                description = await desc_elem.text_content()
                        except:
                            pass

                    job_data = {
                        "title": title.strip(),
                        "company": company.strip(),
                        "location": job_location.strip(),
                        "url": link if link.startswith("http") else f"https://www.linkedin.com{link}",
                        "source": "LinkedIn",
                        "description": description.strip() if description else None,
                        "salary_range": salary_range,
                        "authenticated_search": self._authenticated
                    }

                    jobs.append(job_data)

                except Exception as e:
                    print(f"Error extracting job {i}: {e}")
                    continue

            return jobs

        except Exception as e:
            raise RuntimeError(f"Failed to search LinkedIn jobs: {e}")

    async def get_page_content(self) -> str:
        """Get the text content of the current page."""
        if not self.page:
            raise RuntimeError("Browser not started")

        return await self.page.content()

    async def get_current_url(self) -> str:
        """Get the current page URL."""
        if not self.page:
            raise RuntimeError("Browser not started")

        return self.page.url
