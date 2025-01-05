import asyncio
import os
import pandas as pd
from flask import Flask, request, render_template
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from urllib.parse import quote_plus
from py_lead_generation import GoogleMapsEngine
from py_lead_generation.src.google_search.search import main_google_search
from py_lead_generation.src.facebook.facebook_extraction import process_csv, extract_phone_numbers
from py_lead_generation.src.NLP.name_separation import process_nlp, preprocess_csv

app = Flask(__name__)

output_dir = r"C:\Users\rahul\Desktop\Final_lead_Generation"
os.makedirs(output_dir, exist_ok=True)

@app.route('/')
def main_page():
    return render_template('main.html')

@app.route('/location_search')
def location_search():
    return render_template('index.html')

@app.route('/pincode_search')
def pincode_search():
    return render_template('pincode_search.html')

@app.route('/add_numbers', methods=['POST'])
async def add_numbers():
    query = str(request.form['num1'])
    location = str(request.form['num2'])
    zoom = float(request.form['num3'])
    linkedin_username = str(request.form['linkedin_username'])
    linkedin_password = str(request.form['linkedin_password'])

    await main(query, location, zoom, linkedin_username, linkedin_password)

    csv_file_path = os.path.join(output_dir, 'google_maps_leads.csv')
    
    df = pd.read_csv(csv_file_path, encoding='ISO-8859-1')
    
    print("CSV Columns:", df.columns.tolist())
    
    if 'LinkedinURL' not in df.columns:
        df['LinkedinURL'] = 'NA'
    
    for role in ['CEO', 'CTO', 'IT_Manager']:
        if role not in df.columns:
            df[role] = ''

    required_columns = ['Title', 'Address', 'PhoneNumber', 'WebsiteURL', 'Department', 'LinkedinURL', 'CEO', 'CTO', 'IT_Manager']
    for col in required_columns:
        if col not in df.columns:
            print(f"Warning: Column '{col}' is not in the CSV file")
    
    df['CompanyName'] = df['Title'].apply(lambda x: x.split('|')[0].strip() if '|' in x else x.strip())

    facebook_username = request.form['facebook_username']
    facebook_password = request.form['facebook_password']
    facebook_results = await process_csv(csv_file_path, facebook_username, facebook_password)
    
    for company, posts in facebook_results.items():
        phone_numbers = []
        for post in posts:
            phone_numbers.extend(extract_phone_numbers(post))
        phone_numbers = list(set(phone_numbers))
        df.loc[df['Title'] == company, 'PhoneNumbersFacebook'] = ', '.join(phone_numbers)
    
    df.to_csv(csv_file_path, index=False)

    companies = df[required_columns].to_dict(orient='records')
    
    return render_template('results.html', companies=companies)

async def login_to_linkedin(page, username, password):
    await page.goto("https://www.linkedin.com/login")
    await page.fill("input[name='session_key']", username)
    await page.fill("input[name='session_password']", password)
    await page.click("button[type='submit']")
    await page.wait_for_selector("input[placeholder='Search']")

def create_linkedin_search_url(company_name):
    base_url = "https://www.linkedin.com/search/results/people/"
    query = f"?keywords={quote_plus(company_name)}&origin=SWITCH_SEARCH_VERTICAL"
    return base_url + query

async def update_linkedin_urls(linkedin_username, linkedin_password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            print("Logging in to LinkedIn...")
            await login_to_linkedin(page, linkedin_username, linkedin_password)
            print("Logged in successfully.")
            csv_file_path = os.path.join(output_dir, 'google_maps_leads.csv')
            
            df = pd.read_csv(csv_file_path, encoding='ISO-8859-1')
            
            companies = df['Title'].tolist()

            for company_name in companies:
                search_url = create_linkedin_search_url(company_name)
                print(f"Navigating to search URL for company: {company_name}")
                await page.goto(search_url)

                try:
                    await page.wait_for_selector("li.reusable-search__result-container, h2.artdeco-empty-state__headline", timeout=60000)

                    if await page.query_selector("h2.artdeco-empty-state__headline"):
                        print(f"No results found for company: {company_name}")
                        df.loc[df['Title'] == company_name, 'LinkedinURL'] = 'NA'
                    else:
                        print(f"LinkedIn URL found for company: {company_name}")
                        df.loc[df['Title'] == company_name, 'LinkedinURL'] = search_url

                except PlaywrightTimeoutError:
                    print(f"Failed to load search results for company: {company_name}")
                    df.loc[df['Title'] == company_name, 'LinkedinURL'] = 'NA'

            df.to_csv(csv_file_path, index=False)
            print(f"Updated CSV with LinkedIn URLs: {csv_file_path}")

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            await browser.close()

    print("LinkedIn URL update complete.")

async def main(query, location, zoom, linkedin_username, linkedin_password) -> None:
    engine = GoogleMapsEngine(query, location, zoom)
    await engine.run()
    engine.save_to_csv()
    
    df = pd.read_csv('google_maps_leads.csv', encoding='ISO-8859-1')

    cleaned_df = df.drop_duplicates(subset=['Title'], keep='first')
    cleaned_df.to_csv('google_maps_leads.csv', index=False)

    await update_linkedin_urls(linkedin_username, linkedin_password)
    await main_google_search()

    nlp_file_path = 'google_maps_leads.csv'
    
    df_nlp = pd.read_csv(nlp_file_path, encoding='ISO-8859-1')
    
    for role in ['CEO', 'CTO', 'IT_Manager']:
        if role not in df_nlp.columns:
            df_nlp[role] = ''

    df_nlp['CEO'] = df_nlp['CEO'].apply(lambda x: ', '.join(eval(x)) if isinstance(x, str) and x.startswith('[') and x.endswith(']') else x)
    df_nlp['CTO'] = df_nlp['CTO'].apply(lambda x: ', '.join(eval(x)) if isinstance(x, str) and x.startswith('[') and x.endswith(']') else x)
    df_nlp['IT_Manager'] = df_nlp['IT_Manager'].apply(lambda x: ', '.join(eval(x)) if isinstance(x, str) and x.startswith('[') and x.endswith(']') else x)
    
    df_nlp.to_csv(nlp_file_path, index=False)

    preprocess_csv(nlp_file_path)
    await process_nlp(nlp_file_path)

if __name__ == '__main__':
    app.run(debug=True)


# if __name__ == '__main__':
#     app.run(host='113.11.231.73', port=5000, debug=True)