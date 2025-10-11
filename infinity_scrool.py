import sys
import time
import argparse
import csv
import json
import re
import random
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
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, self.timeout)

            # Execute script to avoid detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
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

    def scrape_single_batch(self, url, batch_size=50, max_scrolls=5, inspect_structure=False, min_scrolls=5):
        """
        Scrape a single batch of items from JustDial with deeper scrolling

        Args:
            url (str): JustDial URL to scrape
            batch_size (int): Number of items to scrape in this batch (default: 50)
            max_scrolls (int): Maximum scroll attempts for infinite scroll (default: 5)
            inspect_structure (bool): Inspect page structure if no listings found
            min_scrolls (int): Minimum scrolls to perform for depth (default: 5)

        Returns:
            list: List of business data dictionaries
        """
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

            batch_data = []
            previous_count = 0
            scroll_count = 0

            # Scroll to load more content - push for minimum scrolls for depth
            while scroll_count < max_scrolls:
                # Find all business listing elements
                try:
                    # Primary selector for business listings
                    store_elements = self.driver.find_elements(By.CLASS_NAME, 'store-details')

                    if not store_elements:
                        # Alternative selectors
                        store_elements = self.driver.find_elements(By.CSS_SELECTOR, '.resultbox, .listing-card, .business-card')
                    
                    # If still no elements found, try to inspect the page structure
                    if not store_elements and inspect_structure and previous_count == 0:
                        self.inspect_page_structure()
                        # Try very generic selector as last resort
                        store_elements = self.driver.find_elements(By.XPATH, "//*[contains(@class, 'store') or contains(@class, 'listing') or contains(@class, 'result') or contains(@class, 'card')]")

                    current_count = len(store_elements)

                    # Extract data from new elements
                    for i in range(previous_count, current_count):
                        business_data = self.extract_business_data(store_elements[i])
                        
                        # Only add valid entries (not empty, not N/A)
                        if business_data['name'] and business_data['name'] != 'N/A' and business_data['name'].strip():
                            batch_data.append(business_data)
                            print(f"✓ Successfully extracted: {business_data['name']}")
                    
                    # Occasionally hover over random elements to appear human
                    if current_count > 0 and random.random() < 0.4:
                        try:
                            random_element = random.choice(store_elements[:min(current_count, 10)])
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", random_element)
                            time.sleep(random.uniform(0.3, 0.8))
                        except:
                            pass

                    # Always try to scroll to get more depth (min_scrolls), even if we have enough items
                    if scroll_count < min_scrolls:
                        # Scroll regardless of current count
                        self.scroll_to_load_more(max_scrolls=1)
                        scroll_count += 1
                        previous_count = current_count
                        time.sleep(random.uniform(1.5, 2.5))  # Random wait for content to load
                    elif len(batch_data) >= batch_size:
                        # We've done minimum scrolls and have enough items
                        break
                    else:
                        # Try to scroll for more content
                        if current_count == previous_count or not self.scroll_to_load_more(max_scrolls=1):
                            break
                        scroll_count += 1
                        previous_count = current_count

                except Exception as e:
                    break

            print(f"  ({scroll_count} scrolls completed, {len(batch_data)} items extracted)")
            return batch_data

        except Exception as e:
            return []

    def scrape_justdial(self, url, num_batches=10, max_scrolls=5, inspect_structure=False, batch_size=50, pause_between_batches=5, min_scrolls=5):
        """
        Main scraping function to extract business data from JustDial with batch processing

        Args:
            url (str): JustDial URL to scrape
            num_batches (int): Number of batches to scrape (default: 10)
            max_scrolls (int): Maximum scroll attempts for infinite scroll (default: 5)
            inspect_structure (bool): Inspect page structure if no listings found
            batch_size (int): Number of items to scrape per batch (default: 50)
            pause_between_batches (int): Seconds to pause between batches (default: 5)
            min_scrolls (int): Minimum scrolls per batch for depth (default: 5)

        Returns:
            list: List of business data dictionaries
        """
        all_business_data = []
        
        for batch_num in range(num_batches):
            print(f"\n--- Batch {batch_num + 1}/{num_batches} ---")
            
            # Scrape this batch with deeper scrolling
            batch_data = self.scrape_single_batch(url, batch_size, max_scrolls, inspect_structure, min_scrolls)
            all_business_data.extend(batch_data)
            
            # Pause before next batch (except for the last batch)
            if batch_num < num_batches - 1:
                print(f"\nPausing for {pause_between_batches} seconds before next batch...")
                time.sleep(pause_between_batches)
        
        return all_business_data

    def save_to_csv(self, data, filename='justdial_data.csv'):
        """Save scraped data to CSV file, appending to existing data and removing duplicates"""
        if not data:
            return

        new_df = pd.DataFrame(data)
        # Ensure only name, address, datestamp columns
        new_df = new_df[['datestamp', 'name', 'address']]
        # Try to read existing CSV file
        try:
            existing_df = pd.read_csv(filename, encoding='utf-8')
            
            # Ensure existing data has datestamp column
            if 'datestamp' not in existing_df.columns:
                existing_df['datestamp'] = datetime.now().date().isoformat()
            
            # Ensure existing data has the correct columns in the correct order
            existing_df = existing_df[['datestamp', 'name', 'address']]

            # Combine existing and new data
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            
        except FileNotFoundError:
            combined_df = new_df
        except pd.errors.EmptyDataError:
            combined_df = new_df
 
        # Remove invalid entries (empty, N/A, or whitespace-only names)
        combined_df = combined_df[combined_df['name'].notna()]
        combined_df = combined_df[combined_df['name'].str.strip() != '']
        combined_df = combined_df[combined_df['name'] != 'N/A']
        
        # Remove duplicates based on name and address, keeping the latest datestamp
        combined_df = combined_df.sort_values(by='datestamp', ascending=False)
        combined_df = combined_df.drop_duplicates(subset=['name', 'address'], keep='first')
        
        # Sort by name for better readability
        combined_df = combined_df.sort_values(by='name')
        
        # Ensure column order is correct before saving
        combined_df = combined_df[['datestamp', 'name', 'address']]
        
        # Save to CSV
        combined_df.to_csv(filename, index=False, encoding='utf-8')

    def save_to_json(self, data, filename='justdial_data.json'):
        """Save scraped data to JSON file, appending to existing data and removing duplicates"""
        if not data:
            return
        # Try to read existing JSON file
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                combined_data = existing_data + data
        except (FileNotFoundError, json.JSONDecodeError):
            combined_data = data

        # Remove duplicates using pandas, keeping latest datestamp
        df = pd.DataFrame(combined_data)
        # Remove invalid entries
        df = df[df['name'].notna()]
        df = df[df['name'].str.strip() != '']
        df = df[df['name'] != 'N/A']
        df = df.sort_values(by='datestamp', ascending=False)
        df = df.drop_duplicates(subset=['name', 'address'], keep='first')
        df = df.sort_values(by='name')
        # Convert back to list of dicts
        unique_data = df.to_dict('records')
        # Save to JSON

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(unique_data, f, ensure_ascii=False, indent=2)

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
    parser = argparse.ArgumentParser(description='Scrape business listings from JustDial')
    parser.add_argument('url', help='JustDial URL to scrape')
    parser.add_argument('-n', '--num-batches', type=int, default=2, help='Number of batches to scrape (default: 2)')
    parser.add_argument('--no-headless', action='store_true', help='Run with visible browser (headless is default)')
    parser.add_argument('--output', default=None, help='Output filename (without extension). If not provided, generated from URL')
    parser.add_argument('--format', choices=['csv', 'json', 'both'], default='csv', help='Output format')
    parser.add_argument('--max-scrolls', type=int, default=5, help='Maximum scroll attempts (default: 5)')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of items to scrape per batch (default: 50)')
    parser.add_argument('--min-scrolls', type=int, default=5, help='Minimum scrolls per batch for depth (default: 5)')
    parser.add_argument('--pause', type=int, default=5, help='Seconds to pause between batches (default: 5)')

    args = parser.parse_args()

    # Generate filename from URL if not provided
    if args.output is None:
        output_filename = generate_filename_from_url(args.url)
    else:
        output_filename = args.output

    # Initialize scraper (headless by default, unless --no-headless is specified)
    scraper = JustDialScraper(headless=not args.no_headless)

    try:
        # Scrape data
        data = scraper.scrape_justdial(
            url=args.url,
            num_batches=args.num_batches,
            max_scrolls=args.max_scrolls,
            batch_size=args.batch_size,
            pause_between_batches=args.pause,
            min_scrolls=args.min_scrolls
        )

        # Save data
        if args.format in ['csv', 'both']:
            csv_filename = f'{output_filename}.csv'
            scraper.save_to_csv(data, csv_filename)
            print(f"\n✓ Data saved to: {csv_filename}")

        if args.format in ['json', 'both']:
            json_filename = f'{output_filename}.json'
            scraper.save_to_json(data, json_filename)
            print(f"✓ Data saved to: {json_filename}")

    except KeyboardInterrupt:
        pass
    except Exception as e:
        pass
    finally:
        scraper.close()

if __name__ == "__main__":
    # Example usage:
    # python justdial_scraper.py "https://www.justdial.com/Bangalore/Pg-Accommodations/"

    # For direct execution without command line arguments
    if len(sys.argv) == 1:
        scraper = JustDialScraper(headless=True)
        try:
            url = "https://www.justdial.com/Bangalore/Pg-Accommodations/"
            data = scraper.scrape_justdial(url, num_batches=2, batch_size=50, pause_between_batches=5, min_scrolls=5)
            filename = generate_filename_from_url(url)
            scraper.save_to_csv(data, f'{filename}.csv')
            print(f"\n✓ Data saved to: {filename}.csv")
        finally:
            scraper.close()
    else:
        main()
