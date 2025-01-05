import csv
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

async def login_to_facebook(page, email, password):
    await page.goto('https://www.facebook.com/')
    await page.fill('input[name="email"]', email)
    await page.fill('input[name="pass"]', password)
    await page.click('button[name="login"]')
    await page.wait_for_timeout(10000)

async def scroll_page(page, max_scrolls=5, scroll_pause_time=2000):
    for _ in range(max_scrolls):
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(scroll_pause_time)
        print("Scrolled down")

async def inject_expand_script(page):
    expand_script = """
    () => {
        let seeMoreButtons = document.querySelectorAll('div.x1i10hfl.xjbqb8w.x1ejq31n.xd10rxx.x1sy0etr.x17r0tee.x972fbf.xcfux6l.x1qhh985.xm0m39n.x9f619.x1ypdohk.xt0psk2.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x16tdsg8.x1hl2dhg.xggy1nq.x1a2a7pz.x1sur9pj.xkrqix3.xzsf02u.x1s688f[role="button"]');
        seeMoreButtons.forEach(button => button.click());
    }
    """
    await page.evaluate(expand_script)

async def search_facebook(page, company_name):
    search_url = f"https://www.facebook.com/search/posts?q={company_name.replace(' ', '%20')}"
    await page.goto(search_url)
    await page.wait_for_load_state('load')
    await scroll_page(page)
    await inject_expand_script(page)
    await page.wait_for_timeout(5000)

    post_texts = []
    posts = page.locator('div[data-ad-preview="message"]')
    post_count = await posts.count()
    for i in range(post_count):
        post_texts.append(await posts.nth(i).inner_text())

    return post_texts

async def process_csv(file_path, email, password):
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await login_to_facebook(page, email, password)

        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader: 
                company_name = row["Title"]
                print(f"Searching for {company_name} on Facebook...")
                posts = await search_facebook(page, company_name)
                if company_name in results:
                    results[company_name].extend(posts)
                else:
                    results[company_name] = posts
        
        await browser.close()
    return results

def extract_phone_numbers(text):
    phone_pattern = re.compile(r'\+?\d[\d\-\(\)\s]{7,}\d')
    return phone_pattern.findall(text)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python facebook.py <csv_file_path> <facebook_username> <facebook_password>")
        sys.exit(1)

    csv_file_path = sys.argv[1]
    facebook_username = sys.argv[2]
    facebook_password = sys.argv[3]

    results = asyncio.run(process_csv(csv_file_path, facebook_username, facebook_password))

    phone_numbers = {}
    for company, posts in results.items():
        phone_numbers[company] = []
        for post in posts:
            phone_numbers[company].extend(extract_phone_numbers(post))
        phone_numbers[company] = list(set(phone_numbers[company]))  # Remove duplicates

    for company, numbers in phone_numbers.items():
        print(f"Company: {company}")
        print(f"Phone Numbers: {numbers}")
