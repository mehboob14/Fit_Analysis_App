import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import os
import requests
from PIL import Image
from io import BytesIO
import pillow_avif

DATA_DIR = os.path.join(os.path.dirname(__file__),'Scripts','data')
IMAGES_DIR = os.path.join(DATA_DIR, 'images')
DOWNLOADED_IMAGES_DIR = os.path.join(IMAGES_DIR, 'downloaded')

def download_images(image_links, save_dir=DOWNLOADED_IMAGES_DIR):
    print("[DEBUG] Starting download_images")
    os.makedirs(save_dir, exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/113.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.net-a-porter.com/",
        "Connection": "keep-alive"
    }
    for idx, url in enumerate(image_links):
        try:
            print(f"[DEBUG] Downloading image: {url}")
            filename = f"image_{idx}.jpeg"
            path = os.path.join(save_dir, filename)
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            img_bytes = BytesIO(response.content)
            try:
                img = Image.open(img_bytes)
                img.verify()
            except Exception as e:
                print(f"[DEBUG] Image verify failed: {e}")
                continue
            img_bytes.seek(0)
            img = Image.open(img_bytes)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(path, format="JPEG", quality=95)
            print(f"[DEBUG] Saved image: {path}")
        except Exception as e:
            print(f"[DEBUG] Failed to download image: {e}")
            pass

async def scrape_product_page(url):
    print("[DEBUG] scraping started")
    print("[DEBUG] Before playwright launch")
    async with async_playwright() as p:
        print("[DEBUG] Playwright started")
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        print("[DEBUG] Browser launched")
        context = await browser.new_context()
        page = await context.new_page()
        print("[DEBUG] Page created")
        await page.goto(url)
        print(f"[DEBUG] Went to {url}")
        await page.wait_for_timeout(4000)
        try:
            await page.wait_for_selector("label[for='Size & Fit-open']", timeout=5000)
            await page.click("label[for='Size & Fit-open']")
            await page.wait_for_timeout(2500)
            print("[DEBUG] Clicked Size & Fit-open")
        except Exception as e:
            print(f"[DEBUG] Size & Fit-open not found: {e}")
        try:
            await page.wait_for_selector('[data-testid="accordion-sizeguide-link"] a.SizeChartLink88__sizeGuideLink', timeout=3000)
            await page.click('[data-testid="accordion-sizeguide-link"] a.SizeChartLink88__sizeGuideLink')
            await page.wait_for_timeout(4000)
            print("[DEBUG] Clicked size guide link")
        except Exception as e:
            print(f"[DEBUG] Size guide link not found: {e}")
        print("[DEBUG] Extracting HTML content")
        full_html = await page.content()
        soup = BeautifulSoup(full_html, 'html.parser')
        result = {}
        editors_notes = soup.select_one('#EDITORS_NOTES .EditorialAccordion88__accordionContent--editors_notes')
        result["editors_notes"] = editors_notes.get_text(strip=True, separator="\n") if editors_notes else "Not found"
        print(f"[DEBUG] Editors Notes: {result['editors_notes'][:50]}...")
        size_fit_section = soup.select_one('#SIZE_AND_FIT .EditorialAccordion88__accordionContent--size_and_fit')
        size_fit_details = []
        model_measurements = []
        if size_fit_section:
            all_lis = size_fit_section.find_all('li')
            for li in all_lis:
                text = li.get_text(strip=True)
                if "model is" in text.lower():
                    model_measurements.append(text)
                else:
                    size_fit_details.append(text)
        result["size_fit"] = size_fit_details
        result["model_measurements"] = model_measurements
        print(f"[DEBUG] Size & Fit details: {size_fit_details}")
        print(f"[DEBUG] Model measurements: {model_measurements}")
        details_care_section = soup.select_one('#DETAILS_AND_CARE .EditorialAccordion88__accordionContent--details_and_care')
        result["details_care"] = [li.get_text(strip=True) for li in details_care_section.find_all('li')] if details_care_section else []
        print(f"[DEBUG] Details & Care: {result['details_care']}")
        try:
            overlay_html = await page.inner_html(".Overlay9.SizeChart88__sizeGuide")
            overlay_soup = BeautifulSoup(overlay_html, "html.parser")
            structured_popup = {}
            table = overlay_soup.select_one(".SizeTable88__table")
            if table:
                headers = [th.get_text(strip=True).lower() for th in table.select("thead th")[1:]]
                rows = table.select("tbody tr")
                for row in rows:
                    cells = row.select("td")
                    if not cells or len(cells) < 2:
                        continue
                    label = cells[0].get_text(strip=True).capitalize()
                    values = [td.get_text(strip=True) for td in cells[1:]]
                    if len(values) == len(headers):
                        structured_popup[label] = dict(zip(headers, values))
                result["size_guide_popup"] = structured_popup
            else:
                result["size_guide_popup"] = "Table not found"
            print(f"[DEBUG] Size guide popup: {result['size_guide_popup']}")
        except Exception as e:
            print(f"[DEBUG] Size guide popup error: {e}")
            result["size_guide_popup"] = "Popup not loaded"
        image_urls = []
        carousel_track = soup.select_one('ul.ImageCarousel88__track')
        noscripts = carousel_track.select('noscript img') if carousel_track else []
        for img in noscripts:
            srcset = img.get('srcset')
            if srcset:
                urls = [u.strip().split()[0] for u in srcset.split(',')]
                preferred = next((url for url in urls if '/w920_q60' in url or '/w2000_q60' in url), None)
                if preferred:
                    if preferred.startswith('//'):
                        preferred = 'https:' + preferred
                    image_urls.append(preferred)
        image_urls = list(dict.fromkeys(image_urls))
        print(f"[DEBUG] Found {len(image_urls)} image URLs")
        os.makedirs(IMAGES_DIR, exist_ok=True)
        file_path = os.path.join(IMAGES_DIR, "image_urls.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("image urls:\n")
            for url in image_urls:
                f.write(url + "\n")
        download_images(image_urls)
        await browser.close()
        print("[DEBUG] Browser closed")
        return result

def run_scrape_and_save(url):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(IMAGES_DIR, exist_ok=True)
        os.makedirs(DOWNLOADED_IMAGES_DIR, exist_ok=True)
        print(f"[DEBUG] DATA_DIR: {DATA_DIR}")
        print(f"[DEBUG] IMAGES_DIR: {IMAGES_DIR}")
        print(f"[DEBUG] DOWNLOADED_IMAGES_DIR: {DOWNLOADED_IMAGES_DIR}")
        data = asyncio.run(scrape_product_page(url))
        details_path = os.path.join(DATA_DIR, "dress_details.txt")
        print(f"[DEBUG] Writing details to: {details_path}")
        with open(details_path, "w", encoding="utf-8") as f:
            f.write("EDITOR'S NOTES:\n" + data.get("editors_notes", "") + "\n\n")
            f.write("SIZE & FIT:\n")
            for detail in data.get("size_fit", []):
                f.write("- " + detail + "\n")
            f.write("\nMODEL MEASUREMENTS:\n")
            for measurement in data.get("model_measurements", []):
                f.write("- " + measurement + "\n")
            f.write("\nDETAILS & CARE:\n")
            for item in data.get("details_care", []):
                f.write("- " + item + "\n")
        size_guide_path = os.path.join(DATA_DIR, "Size_guide.json")
        print(f"[DEBUG] Writing size guide to: {size_guide_path}")
        with open(size_guide_path, "w", encoding="utf-8") as f:
            json.dump(data.get("size_guide_popup", {}), f, ensure_ascii=False, indent=2)
        print("[DEBUG] run_scrape_and_save completed successfully")
    except Exception as e:
        print(f"[DEBUG] Error during scraping: {e}")


if __name__ == "__main__":
    dress_url = "https://www.net-a-porter.com/en-us/shop/product/max-mara/clothing/mini-dresses/bartolo-twill-mini-dress/1647597354715458"
    run_scrape_and_save(dress_url)
