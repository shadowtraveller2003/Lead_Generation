import csv
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

output_csv = "C:\\Users\\rahul\\Desktop\\Final_lead_Generation\\company_info.csv"

company_search_base_url = "https://www.insiderbiz.in/company/"

output_directory = "C:\\Users\\rahul\\Desktop\\Final_lead_Generation\\Scraped_Info"
software_directory = os.path.join(output_directory, "Software")
error_directory = os.path.join(output_directory, "Error")
os.makedirs(output_directory, exist_ok=True)
os.makedirs(software_directory, exist_ok=True)
os.makedirs(error_directory, exist_ok=True)

async def scrape_basic_company_info(pincode, page):
    base_url = "https://www.insiderbiz.in/company-by-address/"
    page_number = 1
    url = f"{base_url}{pincode}/?page={page_number}"

    async def extract_last_page_number(page):
        try:
            last_page_link = await page.query_selector('ul.pagination li:last-child a')
            
            if last_page_link:
                last_page_number = int((await last_page_link.get_attribute('href')).split('=')[-1])
                return last_page_number
            else:
                print("Last page link not found.")
                return None
        except Exception as e:
            print(f"Error occurred while extracting last page number: {str(e)}")
            return None

    await page.goto(url)
    await page.wait_for_load_state('networkidle')

    last_page = await extract_last_page_number(page)
    if not last_page:
        raise ValueError("Failed to retrieve last page number.")

    while page_number <= last_page:
        await page.wait_for_selector('tbody')
        with open(output_csv, 'a', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)

            if page_number == 1:
                csv_writer.writerow(['ROC', 'CIN Number', 'Company Address', 'Company Name'])

            async def extract_row_data(row):
                company_name = (await (await row.query_selector('td:nth-child(1)')).inner_text()).strip() if await row.query_selector('td:nth-child(1)') else ''
                company_address = (await (await row.query_selector('td:nth-child(2)')).inner_text()).strip() if await row.query_selector('td:nth-child(2)') else ''
                cin_number = (await (await row.query_selector('td:nth-child(3)')).inner_text()).strip() if await row.query_selector('td:nth-child(3)') else ''
                company_status = (await (await row.query_selector('td:nth-child(4)')).inner_text()).strip() if await row.query_selector('td:nth-child(4)') else ''
                return [cin_number, company_name, company_status, company_address]
            table_rows = await page.query_selector_all('tbody tr')
            for row in table_rows:
                csv_writer.writerow(await extract_row_data(row))

        next_page_link = None
        pagination_links = await page.query_selector_all('ul.pagination.pagination-small.pagination-right li:not(.disabled) a')
        for link in pagination_links:
            if (await link.inner_text()).strip() == str(page_number + 1):
                next_page_link = link
                break

        if next_page_link:
            next_url = urljoin(base_url, await next_page_link.get_attribute('href'))
            page_number += 1  
            print(f"Scraping information from {next_url}")
            await page.goto(next_url)  
            try:
                await page.wait_for_load_state('networkidle', timeout=60000)  
            except Exception as e:
                print(f"Page {page_number} took too long to load or encountered an error: {str(e)}")
                break  
        else:
            break  

async def scrape_detailed_company_info(page, company_name):
    name = company_name.replace(".", "").replace("(", "").replace(")", "").replace("& ","").replace("-","")
    url = company_search_base_url + name.replace(" ", "-").upper()
    
    try:
        response = await page.goto(url)
        
        if response and response.status == 200:
            page_text = await page.content()
            soup = BeautifulSoup(page_text, 'html.parser')
            text_content = soup.get_text(separator="\n")
            
            if "It Comes Under Division COMPUTER AND RELATED ACTIVITIES" in text_content:
                save_directory = software_directory
            else:
                save_directory = output_directory
            
            return text_content, save_directory
        else:
            return f"INFO COULD NOT BE EXTRACTED, HERE IS THE {url} FOR MORE REFERENCE", error_directory
    except Exception as e:
        return f"INFO COULD NOT BE EXTRACTED, HERE IS THE {url} FOR MORE REFERENCE: {e}", output_directory

async def main():
    pincode = int(input("Enter the Pincode where you want to search the software companies: "))
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  
        page = await browser.new_page()
        await scrape_basic_company_info(pincode, page)

        with open(output_csv, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                company_name = row['Company Name']
                print(f"Scraping detailed info for {company_name}...")
                
                company_info, save_directory = await scrape_detailed_company_info(page, company_name)
                
                safe_company_name = company_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                output_file_path = os.path.join(save_directory, f"{safe_company_name}.txt")
                
                with open(output_file_path, 'w', encoding='utf-8') as outfile:
                    outfile.write(company_info)
                
                print(f"Detailed info for {company_name} saved to {output_file_path}")
        
        await page.wait_for_timeout(30000) 
        # await browser.close()

asyncio.run(main())
