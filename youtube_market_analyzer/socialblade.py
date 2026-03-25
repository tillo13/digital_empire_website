#!/usr/bin/env python3
"""
Social Blade Data Scraper
-------------------------
Extracts YouTube channel statistics from Social Blade
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import re
import json
from datetime import datetime

# Digital Empire Channels
CHANNELS = {
    'Dexter Playz': 'UCKvnz_vFpGajDcaKOZbZPLA',
    'Red Ninja': 'UCBKTcgFjkSBuWap77myBAeQ',
    # Add more channels as needed
}

def setup_driver():
    """Set up Chrome driver with options"""
    chrome_options = Options()
    # chrome_options.add_argument('--headless')  # Uncomment to run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    
    return webdriver.Chrome(options=chrome_options)

def parse_number(text):
    """Convert text like '1.42M' or '270,291,640' to integer"""
    if not text:
        return 0
    
    # Remove commas
    text = text.replace(',', '')
    
    # Handle K, M, B suffixes
    multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}
    
    for suffix, multiplier in multipliers.items():
        if suffix in text.upper():
            number = float(text.upper().replace(suffix, '').strip())
            return int(number * multiplier)
    
    # Try to parse as regular number
    try:
        return int(float(text))
    except:
        return 0

def scrape_channel(driver, channel_name, channel_id):
    """Scrape data for a single channel"""
    print(f"\n{'='*60}")
    print(f"Scraping: {channel_name}")
    print('='*60)
    
    url = f"https://socialblade.com/youtube/channel/{channel_id}"
    driver.get(url)
    
    # Wait for page to load
    time.sleep(3)
    
    data = {
        'channel_name': channel_name,
        'channel_id': channel_id,
        'current_stats': {},
        'daily_data': [],
        'monthly_data': []
    }
    
    try:
        # Wait for main content to load
        wait = WebDriverWait(driver, 10)
        
        # Get current statistics
        print("📊 Extracting current statistics...")
        
        # Find subscriber count
        try:
            # Look for the main subscriber display
            sub_elements = driver.find_elements(By.XPATH, "//p[contains(text(), 'subscribers')]")
            for elem in sub_elements:
                text = elem.text
                # Extract number before 'subscribers'
                match = re.search(r'([\d.]+[KMB]?)\s*subscribers', text, re.IGNORECASE)
                if match:
                    data['current_stats']['subscribers'] = parse_number(match.group(1))
                    print(f"✅ Subscribers: {match.group(1)}")
                    break
        except:
            pass
        
        # Find view count
        try:
            view_elements = driver.find_elements(By.XPATH, "//p[contains(text(), 'views')]")
            for elem in view_elements:
                text = elem.text
                match = re.search(r'([\d,]+|[\d.]+[KMB]?)\s*views', text, re.IGNORECASE)
                if match:
                    data['current_stats']['views'] = parse_number(match.group(1))
                    print(f"✅ Views: {match.group(1)}")
                    break
        except:
            pass
        
        # Find video count
        try:
            video_elements = driver.find_elements(By.XPATH, "//p[contains(text(), 'videos')]")
            for elem in video_elements:
                text = elem.text
                match = re.search(r'([\d,]+)\s*videos', text, re.IGNORECASE)
                if match:
                    data['current_stats']['videos'] = parse_number(match.group(1))
                    print(f"✅ Videos: {match.group(1)}")
                    break
        except:
            pass
        
        # Get daily statistics table
        print("\n📅 Extracting daily statistics...")
        try:
            # Find the table with daily data
            tables = driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                # Check if this is the daily stats table
                headers = table.find_elements(By.TAG_NAME, "th")
                if any("Date" in h.text for h in headers):
                    rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header
                    
                    for row in rows[:30]:  # Get last 30 days
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 4:
                            date_text = cells[0].text.strip()
                            subs_text = cells[1].text.strip()
                            views_text = cells[2].text.strip()
                            videos_text = cells[3].text.strip()
                            
                            # Parse date
                            try:
                                # Convert date format
                                date_obj = datetime.strptime(date_text, "%a%Y-%m-%d")
                                date_str = date_obj.strftime("%Y-%m-%d")
                            except:
                                date_str = date_text
                            
                            daily_entry = {
                                'date': date_str,
                                'subscribers': parse_number(subs_text) if subs_text != '--' else None,
                                'views': parse_number(views_text),
                                'videos': parse_number(videos_text)
                            }
                            
                            data['daily_data'].append(daily_entry)
                    
                    print(f"✅ Found {len(data['daily_data'])} days of data")
                    break
        except Exception as e:
            print(f"❌ Error extracting daily data: {e}")
        
        # Get monthly statistics if available
        print("\n📈 Looking for monthly statistics...")
        try:
            # Click on monthly tab if exists
            monthly_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Monthly')]")
            monthly_button.click()
            time.sleep(2)
            
            # Extract monthly data
            # (Similar logic to daily data extraction)
            
        except:
            print("ℹ️  Monthly view not found or not accessible")
        
    except Exception as e:
        print(f"❌ Error scraping channel: {e}")
    
    return data

def main():
    """Main function to scrape all channels"""
    print("🚀 Starting Social Blade scraper...")
    
    driver = setup_driver()
    all_data = {}
    
    try:
        for channel_name, channel_id in CHANNELS.items():
            data = scrape_channel(driver, channel_name, channel_id)
            all_data[channel_name] = data
            
            # Wait between channels to avoid rate limiting
            time.sleep(3)
        
        # Save data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"socialblade_data_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        print(f"\n✅ Data saved to {filename}")
        
        # Print summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        for channel, data in all_data.items():
            stats = data.get('current_stats', {})
            print(f"\n{channel}:")
            print(f"  Subscribers: {stats.get('subscribers', 'N/A'):,}")
            print(f"  Views: {stats.get('views', 'N/A'):,}")
            print(f"  Videos: {stats.get('videos', 'N/A')}")
            print(f"  Daily data points: {len(data.get('daily_data', []))}")
        
    finally:
        print("\nClosing browser...")
        driver.quit()

if __name__ == "__main__":
    main()