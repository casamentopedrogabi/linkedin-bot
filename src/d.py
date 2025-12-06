import os
import random
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

# ==============================================================================
# ⚙️ CONFIGURATION E CAMINHOS
# ==============================================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DRIVER_FILENAME = os.path.join(PROJECT_ROOT, "msedgedriver.exe")

# Exact Base URL provided (without page parameter)
BASE_URL = "https://www.linkedin.com/search/results/people/?geoUrn=%5B%22101165590%22%2C%22103350119%22%2C%22102890719%22%2C%22106693272%22%2C%22100364837%22%2C%22105646813%22%2C%22101282230%22%2C%22104738515%22%5D&keywords=vp%20of%20data&origin=FACETED_SEARCH"

# Search parameters
START_PAGE = 1
END_PAGE = 5
MAX_LIMIT = 10


def run_scraper():
    # 1. Driver Configuration
    if not os.path.exists(DRIVER_FILENAME):
        print(f"❌ ERROR: '{DRIVER_FILENAME}' not found.")
        return

    edge_options = Options()
    edge_options.add_argument("--start-maximized")
    edge_options.add_argument("--disable-blink-features=AutomationControlled")

    # User Profile Path (Close Edge before running!)
    user_data_dir = os.path.join(
        os.getenv("LOCALAPPDATA"), "Microsoft", "Edge", "User Data"
    )
    edge_options.add_argument(f"user-data-dir={user_data_dir}")
    edge_options.add_argument("--profile-directory=Default")

    try:
        service = Service(executable_path=DRIVER_FILENAME)
        driver = webdriver.Edge(service=service, options=edge_options)
    except Exception as e:
        print(f"❌ Error opening Edge: {e}")
        return

    # File to save links
    output_file = "links_coletados.txt"

    # Set to store all unique profiles across pages
    all_collected_profiles = set()

    try:
        # 2. Loop through pages
        for page_num in range(START_PAGE, END_PAGE + 1):
            # Stop if limit reached
            if len(all_collected_profiles) >= MAX_LIMIT:
                break

            # Construct URL
            target_url = f"{BASE_URL}&page={page_num}"

            print(f"\n--- Accessing Page {page_num} ---")
            print(f"URL: {target_url}")

            driver.get(target_url)

            # Wait for load
            time.sleep(5)

            # Scroll to bottom (Mandatory for LinkedIn lazy load)
            print("📜 Scrolling page to load elements...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")  # Back to top
            time.sleep(1)

            # 3. Parse Raw HTML (The logic you confirmed works best)
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Get ALL 'a' tags with href attribute
            all_links = soup.find_all("a", href=True)

            profiles_found_on_this_page = 0

            print(f"🔎 Analyzing {len(all_links)} links found in HTML...")

            for link in all_links:
                # Stop checking links if limit reached inside the page loop
                if len(all_collected_profiles) >= MAX_LIMIT:
                    break

                href = link["href"]

                # Filter: Only profile links (/in/)
                if (
                    "/in/" in href
                    and "linkedin.com/in/" in href
                    or href.startswith("/in/")
                ):
                    # Cleanup: Remove query params
                    clean_link = href.split("?")[0]

                    # Fix relative links
                    if clean_link.startswith("/in/"):
                        clean_link = "https://www.linkedin.com" + clean_link

                    # === GARBAGE FILTER (ACo/ACw) ===
                    slug = clean_link.split("/in/")[-1]

                    # If slug starts with "ACo" or "ACw", it is internal garbage
                    if not slug.startswith("ACo") and not slug.startswith("ACw"):
                        if clean_link not in all_collected_profiles:
                            all_collected_profiles.add(clean_link)
                            profiles_found_on_this_page += 1
                            print(f"   -> {clean_link}")

            # 4. Save to file
            if profiles_found_on_this_page > 0:
                print(
                    f"✅ Found {profiles_found_on_this_page} new valid profiles on page {page_num}."
                )

                # Append to file immediately
                with open(output_file, "a", encoding="utf-8") as f:
                    # We iterate over the set, but writing only new ones is tricky in append mode without logic overlap
                    # For simplicity in this script, we rewrite the file or just dump everything at end.
                    # Given the request, let's keep it simple: write everything at the end or maintain a separate list for this page.
                    pass
            else:
                print(
                    "⚠️ No valid profile links (/in/) found. LinkedIn might have asked for Captcha or page failed to load."
                )

            # Human pause
            time.sleep(random.uniform(4, 7))

    except Exception as e:
        print(f"❌ Fatal Error: {e}")
    finally:
        print("\n🏁 Process finished.")
        print(f"🎯 Total collected: {len(all_collected_profiles)}")

        # Save final list
        with open(output_file, "w", encoding="utf-8") as f:
            for p_link in all_collected_profiles:
                f.write(f"{p_link}\n")

        driver.quit()


if __name__ == "__main__":
    run_scraper()
