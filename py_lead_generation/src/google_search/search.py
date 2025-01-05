import asyncio
import pandas as pd
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def scrape_google_search(company, role):
    async with async_playwright() as p:
        print(f"Launching browser for {company} - {role}")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        search_query = f"Current {role} of {company}"
        print(f"Navigating to Google search for query: {search_query}")
        await page.goto(f"https://www.google.com/search?q={search_query}")

        print("Fetching page content")
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        result_div = soup.find('div', class_='dURPMd')
        if result_div:
            result_text = result_div.get_text(strip=True)
        else:
            result_text = "No relevant information found"

        await browser.close()
        return result_text

async def main_google_search():
    # Read company names from CSV
    df = pd.read_csv('google_maps_leads.csv', encoding='ISO-8859-1')
    companies = df['Title'].tolist()
    roles = ['CEO', 'CTO', 'IT_Manager']
    
    for company in companies:
        for role in roles:
            result = await scrape_google_search(company, role)
            df.loc[df['Title'] == company, role] = result

    df.to_csv('google_maps_leads.csv', index=False)

if __name__ == "__main__":
    asyncio.run(main_google_search())
