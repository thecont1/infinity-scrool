import sys
import time
import argparse
import csv
import json
import re
import random
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

class JustDialScraper:
    def __init__(self, headless=True, timeout=10):
        """
        Initialize the JustDial scraper with Chrome WebDriver

        Args:
            headless (bool): Run browser in headless mode
            timeout (int): Timeout for WebDriver waits
        """
        self.timeout = timeout
        self.setup_driver(headless)

    def setup_driver(self, headless=True):
        """Setup Chrome WebDriver with options"""
        chrome_options = Options()

        if headless:
            chrome_options.add_argument('--headless')

        # Additional options for better performance and stability
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # User agent to avoid detection
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

        try:
            try:
                service = Service()
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, self.timeout)

            # Execute script to avoid detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            version = None
            try:
                caps = getattr(self.driver, 'capabilities', {}) or {}
                version = caps.get('browserVersion') or caps.get('version')
            except Exception:
                pass
            if version:
                print(f"Chrome WebDriver initialized successfully (Chrome {version})")
            else:
                print("Chrome WebDriver initialized successfully")

        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            raise

    def strings_to_number(self, encoded_string):
        """
        Decode JustDial's encoded phone numbers

        Args:
            encoded_string (str): Encoded phone number string

        Returns:
            str: Decoded phone number
        """
        switcher = {
            'dc': '+', 'fe': '(', 'hg': ')', 'ba': '-',
            'acb': '0', 'yz': '1', 'wx': '2', 'vu': '3', 'ts': '4',
            'rq': '5', 'po': '6', 'nm': '7', 'lk': '8', 'ji': '9'
        }
        return switcher.get(encoded_string, "")

    def decode_phone_number(self, contact_elements):
        """
        Decode phone numbers from JustDial contact elements

        Args:
            contact_elements: List of contact elements

        Returns:
            str: Decoded phone number
        """
        phone_digits = []

        for element in contact_elements:
            class_attr = element.get_attribute('class')
            if 'mobilesv' in class_attr:
                # Extract the encoded part after 'mobilesv-'
                encoded_part = class_attr.split('mobilesv-')[-1]
                decoded_digit = self.strings_to_number(encoded_part)
                if decoded_digit:
                    phone_digits.append(decoded_digit)

        return ''.join(phone_digits)

    def scroll_to_load_more(self, max_scrolls=10):
        """
        Scroll down to trigger infinite scroll loading with human-like behavior

        Args:
            max_scrolls (int): Maximum number of scroll attempts

        Returns:
            bool: True if new content was loaded
        """
        initial_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0

        while scroll_count < max_scrolls:
            # Random scroll distance (80-95% of page height) to appear more human
            scroll_percentage = random.uniform(0.8, 0.95)
            current_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_position = int(current_height * scroll_percentage)
            
            # Smooth scroll with random speed
            self.driver.execute_script(f"""
                window.scrollTo({{
                    top: {scroll_position},
                    behavior: 'smooth'
                }});
            """)
            
            # Random delay to simulate reading (2-4 seconds)
            time.sleep(random.uniform(2, 4))
            
            # Occasionally scroll back up a bit (like a human would)
            if random.random() < 0.3:
                scroll_back = random.randint(100, 300)
                self.driver.execute_script(f"window.scrollBy(0, -{scroll_back});")
                time.sleep(random.uniform(0.5, 1.5))
            
            # Scroll to actual bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Random wait for content to load (2-3 seconds)
            time.sleep(random.uniform(2, 3))

            # Check if new content was loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            if new_height == initial_height:
                break
            else:
                initial_height = new_height
                scroll_count += 1

        return scroll_count > 0

    def extract_business_data(self, store_element):
        """
        Extract data from a single business listing element

        Args:
            store_element: WebElement containing business data

        Returns:
            dict: Extracted business data
        """
        business_data = {
            'datestamp': datetime.now().date().isoformat(),
            'name': '',
            'address': '',
#            'phone': '',
#            'rating': '',
#            'website': ''
        }

        try:
            # Extract business name
            try:
                name_element = store_element.find_element(By.CLASS_NAME, 'lng_cont_name')
                business_data['name'] = name_element.text.strip()
            except NoSuchElementException:
                try:
                    # Alternative selector for business name
                    name_element = store_element.find_element(By.CSS_SELECTOR, '.fn.gray_btext a')
                    business_data['name'] = name_element.text.strip()
                except NoSuchElementException:
                    # Try more generic selectors
                    try:
                        name_element = store_element.find_element(By.CSS_SELECTOR, 'h2, h3, .heading, [class*="name"], [class*="title"]')
                        business_data['name'] = name_element.text.strip()
                    except NoSuchElementException:
                        business_data['name'] = 'N/A'

            # Extract address 
            try:
                address_element = store_element.find_element(By.CLASS_NAME, 'cont_sw_addr')
                business_data['address'] = address_element.text.strip()
            except NoSuchElementException:
                try:
                    # Alternative selector for address
                    address_element = store_element.find_element(By.CSS_SELECTOR, '.mrehover.gray_text')
                    business_data['address'] = address_element.text.strip()
                except NoSuchElementException:
                    try:
                        # Try more generic address selectors
                        address_element = store_element.find_element(By.CSS_SELECTOR, '[class*="address"], [class*="location"], .adr, address')
                        business_data['address'] = address_element.text.strip()
                    except NoSuchElementException:
                        business_data['address'] = 'N/A'

        except Exception as e:
            print(f"Error extracting data from business element: {e}")

        return business_data

    def scrape_justdial(self, url, n=50):
        """
        Scrape business listings from JustDial

        Args:
            url (str): JustDial URL to scrape
            n (int): Number of results to extract (default: 50)

        Returns:
            list: List of business data dictionaries
        """
        # Calculate number of scrolls needed (approximately 10 results per scroll)
        num_scrolls = max(1, n // 10)
        
        print(f"\nTarget: {n} results")
        print(f"Let the scraping begin...\n")
        
        try:
            # Navigate to the URL
            self.driver.get(url)
            time.sleep(3)

            # Handle any popups or overlays
            try:
                popup_close = self.driver.find_element(By.CSS_SELECTOR, '.close, .popup-close, [data-dismiss="modal"]')
                popup_close.click()
                time.sleep(1)
            except NoSuchElementException:
                pass

            results = []
            previous_count = 0
            scroll_count = 0

            # Scroll to load content
            while scroll_count < num_scrolls:
                try:
                    # Find all business listing elements
                    store_elements = self.driver.find_elements(By.CLASS_NAME, 'store-details')

                    if not store_elements:
                        # Alternative selectors
                        store_elements = self.driver.find_elements(By.CSS_SELECTOR, '.resultbox, .listing-card, .business-card')

                    current_count = len(store_elements)

                    # Extract data from new elements
                    for i in range(previous_count, current_count):
                        if len(results) >= n:
                            break
                            
                        business_data = self.extract_business_data(store_elements[i])
                        
                        # Only add valid entries (not empty, not N/A)
                        if business_data['name'] and business_data['name'] != 'N/A' and business_data['name'].strip():
                            results.append(business_data)
                            print(f"✓ [{len(results)}/{n}] {business_data['name']}")
                    
                    # Check if we have enough results
                    if len(results) >= n:
                        print(f"\n✓ Target reached: {len(results)} results extracted")
                        break
                    
                    # Occasionally hover over random elements to appear human
                    if current_count > 0 and random.random() < 0.4:
                        try:
                            random_element = random.choice(store_elements[:min(current_count, 10)])
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", random_element)
                            time.sleep(random.uniform(0.3, 0.8))
                        except:
                            pass

                    # Scroll for more content
                    self.scroll_to_load_more(max_scrolls=1)
                    scroll_count += 1
                    previous_count = current_count
                    time.sleep(random.uniform(1.5, 2.5))

                except Exception as e:
                    print(f"Error during scraping: {e}")
                    break

            print(f"\nCompleted: {len(results)} results extracted")
            return results

        except Exception as e:
            print(f"Fatal error: {e}")
            return []


    def save_to_csv(self, data, filename='data.csv'):
        """Save scraped data to CSV (.csv.gz), appending and de-duplicating."""
        if not data:
            return

        new_df = pd.DataFrame(data)
        new_df = new_df[['datestamp', 'name', 'address']]

        def split_address(addr):
            if pd.isna(addr):
                return '', ''
            text = str(addr).strip()
            if ',' in text:
                head, tail = text.rsplit(',', 1)
                return head.strip(), tail.strip()
            return text, ''

        addr_city = new_df['address'].apply(split_address)
        new_df['address'] = addr_city.apply(lambda x: x[0])
        new_df['city'] = addr_city.apply(lambda x: x[1])

        existing_df = None
        try:
            existing_df = pd.read_csv(filename + '.gz', encoding='utf-8')
        except FileNotFoundError:
            try:
                existing_df = pd.read_csv(filename, encoding='utf-8')
            except FileNotFoundError:
                existing_df = None
            except pd.errors.EmptyDataError:
                existing_df = None
        except pd.errors.EmptyDataError:
            existing_df = None

        if existing_df is not None:
            if 'datestamp' not in existing_df.columns:
                existing_df['datestamp'] = datetime.now().date().isoformat()
            if 'city' not in existing_df.columns:
                ec = existing_df['address'].apply(split_address)
                existing_df['address'] = ec.apply(lambda x: x[0])
                existing_df['city'] = ec.apply(lambda x: x[1])
            existing_df = existing_df[['datestamp', 'name', 'address', 'city']]
            # Backfill empty/invalid datestamps in existing data
            ds = existing_df['datestamp'].astype(str).str.strip()
            mask_empty = ds.eq('') | ds.eq('nan') | ds.isna()
            existing_df.loc[mask_empty, 'datestamp'] = datetime.now().date().isoformat()
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        # Clean and de-duplicate
        combined_df = combined_df[combined_df['name'].notna()]
        combined_df = combined_df[combined_df['name'].str.strip() != '']
        combined_df = combined_df[combined_df['name'] != 'N/A']
        combined_df['address'] = combined_df['address'].fillna('').astype(str).str.strip()
        combined_df['city'] = combined_df['city'].fillna('').astype(str).str.strip()

        # Normalize/backfill datestamp before sort
        combined_df['datestamp'] = combined_df['datestamp'].astype(str).str.strip()
        mask_empty_all = combined_df['datestamp'].eq('') | combined_df['datestamp'].eq('nan') | combined_df['datestamp'].isna()
        combined_df.loc[mask_empty_all, 'datestamp'] = datetime.now().date().isoformat()

        combined_df = combined_df.sort_values(by='datestamp', ascending=False)
        combined_df = combined_df.drop_duplicates(subset=['name', 'address', 'city'], keep='first')
        combined_df = combined_df.sort_values(by='name')
        combined_df = combined_df[['datestamp', 'name', 'address', 'city']]

        # Save gzipped CSV
        combined_df.to_csv(filename + '.gz', index=False, encoding='utf-8', compression='gzip')

    def close(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

def generate_filename_from_url(url):
    """
    Generate a filename from JustDial URL
    Example: https://www.justdial.com/Bangalore/Pg-Accommodations/nct-10934649
    Returns: Bangalore-Pg-Accommodations
    """
    try:
        # Parse the URL path
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        # Split by '/' and get the relevant parts
        parts = path.split('/')
        
        # Filter out empty parts and 'nct-' identifiers
        relevant_parts = []
        for part in parts:
            # Skip empty parts and nct identifiers
            if part and not part.startswith('nct-'):
                relevant_parts.append(part)
        
        # Join with hyphens
        if relevant_parts:
            filename = '-'.join(relevant_parts)
            # Clean up any special characters
            filename = re.sub(r'[^a-zA-Z0-9-]', '-', filename)
            # Remove multiple consecutive hyphens
            filename = re.sub(r'-+', '-', filename)
            return filename.strip('-')
        else:
            return 'justdial_data'
    except:
        return 'justdial_data'

def main():
    """Main function to run the scraper"""
    print('\n🌀 Infinity Scrool - JustDial Business Listings Scraper')
    print('An easy-to-use, reliable scraper to download results from any page on JustDial.com.\n')
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
📖 How to use:
  
  Basic usage (scrape 50 results):
    python infinity_scrool.py "https://www.justdial.com/Bangalore/Restaurants/"
  
  Get more results:
    python infinity_scrool.py "https://www.justdial.com/Bangalore/Pg-Accommodations/" -n 100
  
  Watch the magic happen (visible browser):
    python infinity_scrool.py "https://www.justdial.com/Bangalore/Hotels/" -n 200 --no-headless
  
  Custom output filename:
    python infinity_scrool.py "URL" -n 150 --output my-custom-name

💡 Tips:
  • Results are saved to a CSV file. Filename is determined automatically based on the URL.
  • Our bot knows how to work with infinite scroll pages.  
  • Scraper mimics human-like scrolling to play nicely with bot blockers.
  • Data is deduplicated and appended to existing files. Every time you run the program, you grow the dataset.

🦹‍♀️ PRO TIP: Use this tool judiciously. DO NOT OVERDO IT! 

With that said, happy and responsible scraping! ✨
'''
    )
    parser.add_argument('url', nargs='?', metavar='URL', help='JustDial URL to scrape (e.g., "https://www.justdial.com/Bangalore/Pg-Accommodations/")')
    parser.add_argument('-n', type=int, default=50, metavar='NUM', help='number of results to extract (default: 50)')
    parser.add_argument('--no-headless', action='store_true', help='show browser window while scraping')
    parser.add_argument('--output', default=None, metavar='FILENAME', help='custom output filename without extension (auto-generated if not provided)')

    args = parser.parse_args()

    # If no URL provided, print friendly help and exit gracefully
    if len(sys.argv) == 1:
        parser.print_help()
        return

    # Generate filename from URL if not provided
    if args.output is None:
        output_filename = generate_filename_from_url(args.url)
    else:
        output_filename = args.output

    scraper = JustDialScraper(headless=not args.no_headless)

    try:
        data = scraper.scrape_justdial(url=args.url, n=args.n)

        csv_filename = f'{output_filename}.csv.gz'
        # Pass base name without .gz; save_to_csv will add .gz
        scraper.save_to_csv(data, f'{output_filename}.csv')
        print(f"\n✓ Data saved to: {csv_filename}")

    except KeyboardInterrupt:
        print("\n\n✗ Scraping interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
