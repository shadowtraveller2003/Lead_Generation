import time
import asyncio
import csv
import os
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError

from py_lead_generation.src.engines.base import BaseEngine
from py_lead_generation.src.engines.abstract import AbstractEngine
from py_lead_generation.src.misc.utils import get_coords_by_location

output_dir = r'C:\Users\rahul\Desktop\Final_lead_Generation'
os.makedirs(output_dir, exist_ok=True)

class GoogleMapsEngine(BaseEngine, AbstractEngine):
    BASE_URL = 'https://www.google.com/maps/search/{query}/@{coords},{zoom}z/data=!3m1!4b1?entry=ttu'
    FIELD_NAMES = ['Title', 'Address', 'PhoneNumber', 'WebsiteURL', 'Department']
    FILENAME = 'google_maps_leads.csv'

    SLEEP_PER_SCROLL_S = 5
    SCROLL_TIME_DURATION_S = 600  # Increase the scroll duration to 600 seconds (10 minutes)

    def __init__(self, query: str, location: str, zoom: int | float = 12) -> None:
        self._entries = []
        self.zoom = zoom
        self.query = query
        self.location = location
        self.coords = get_coords_by_location(self.location)
        self.search_query = f'{self.query}%20{self.location}'
        self.url = self.BASE_URL.format(
            query=self.search_query, coords=','.join(self.coords), zoom=self.zoom
        )

    async def _get_search_results_urls(self) -> list[str]:
        async def hover_search_results() -> None:
            leftbar = await self.page.query_selector('[role="main"]')
            await leftbar.hover()
            await asyncio.sleep(0.5)

        async def scroll_and_sleep(delta_y: int = 1000) -> None:
            await self.page.mouse.wheel(0, delta_y)
            await asyncio.sleep(self.SLEEP_PER_SCROLL_S)

        async def end_locator_is_present() -> bool:
            end_locator = await self.page.query_selector('.m6QErb.tLjsW.eKbjU')
            return bool(end_locator)

        async def scrape_urls() -> list[str]:
            urls = []
            link_elements = await self.page.query_selector_all('a.hfpxzc')
            for link_element in link_elements:
                url = await link_element.get_attribute('href')
                urls.append(url)
            return urls

        await hover_search_results()
        start_scroll_time = time.time()

        while True:
            await scroll_and_sleep()
            finish_scroll_time = time.time()
            if (await end_locator_is_present()) or (finish_scroll_time - start_scroll_time > self.SCROLL_TIME_DURATION_S):
                break

        urls = await scrape_urls()
        return urls

    async def _open_url_and_wait(self, url: str, wait_time: float = 1.5) -> None:
        try:
            await self.page.goto(url, timeout=90000)  # Increase the timeout to 90 seconds
        except TimeoutError:
            print(f"Timeout while trying to load {url}")
        await asyncio.sleep(wait_time)

    def _parse_data_with_soup(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        title_element = soup.select_one('.DUwDvf.lfPIob')
        title = title_element.get_text(strip=True) if title_element else '-'

        address_element = soup.find('button', {'data-item-id': 'address'})
        address = address_element.get_text(strip=True) if address_element else '-'
        address_words = address.split()
        truncated_address = ' '.join(address_words[-7:]) if address_words else '-'

        phone_element = soup.select_one('a[href^="tel:"]')
        phone = phone_element.get('href').replace('tel:', '') if phone_element else '-'

        website_element = soup.select_one('a[href^="https://"]')
        website_url = website_element.get('href') if website_element else '-'

        department_element = soup.select_one('button[jsaction*="category"], span[jsaction*="category"]')
        department = department_element.get_text(strip=True) if department_element else '-'

        return {
            'Title': title,
            'Address': truncated_address,
            'PhoneNumber': phone,
            'WebsiteURL': website_url,
            'Department': department
        }

    async def _scrape_entry(self, url: str) -> None:
        try:
            await self._open_url_and_wait(url)
            html = await self.page.content()
            entry_data = self._parse_data_with_soup(html)
            if isinstance(entry_data, dict):
                self._entries.append(entry_data)
            else:
                print(f"Skipping entry as it's not a dictionary: {entry_data}")
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    async def run(self) -> None:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            self.page = await browser.new_page()
            try:
                await self.page.goto(self.url, timeout=90000)  # Increase the timeout to 90 seconds
            except TimeoutError:
                print(f"Timeout while trying to load {self.url}")
                return

            search_results_urls = await self._get_search_results_urls()

            for url in search_results_urls:
                await self._scrape_entry(url)

            await browser.close()

        self._save_to_csv()

    def _save_to_csv(self) -> None:
        if not self._entries:
            return
        with open(os.path.join(output_dir, self.FILENAME), mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=self.FIELD_NAMES)
            writer.writeheader()
            for entry in self._entries:
                writer.writerow(entry)
