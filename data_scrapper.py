import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd

# Chrome driver is essential in order to run, the link's been highlited in notebook
# chrome_driver_path = '/opt/homebrew/bin/chromedriver'


class EconomicCalendarScrapper:
    URL = os.getenv("URL")

    def __init__(self, chrome_driver_path: str,
                 ): 



        service = Service(chrome_driver_path)
        options = webdriver.ChromeOptions()

        # Additional arguments to address "DevToolsActivePort" error
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-data-dir=/tmp/chrome-data")

        print("Opening Chrome...")
        self.driver = webdriver.Chrome(service=service, options=options)
        print("Chrome is ready!")
        pass

    
    def gather_economical_events(self, start_date: str, end_date: str) -> list: # date format : M/D/Y
        self.start_date = start_date
        self.end_date = end_date

        self._load_url_()
        self._cookie_signup_popup_handler_()
        self._filter_date_interval_()
        self._adjust_timezone_()
        self._maximum_scroll_to_load_()
        
        data_gathered = self._gathering_page_data_()
        
        return data_gathered


    def _load_url_(self):
        print("Opening URL...")
        self.driver.get(self.URL)

        # Wait for page to load initial elements
        time.sleep(5)
        print("URL is been opened!")
        pass


    def _cookie_signup_popup_handler_(self):
        # Handle cookie/privacy consent pop-up
        try:
            cookie_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            cookie_button.click()
            print("Cookie consent accepted.")
        except Exception as e:
            print("Cookie consent button not found or already accepted:", e)

        # Attempt to close sign-up pop-up by sending the ESCAPE key
        try:
            body = self.driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            print("Sent ESCAPE key to close sign-up pop-up.")
        except Exception as e:
            print("Failed to send ESCAPE key:", e)




    def _filter_date_interval_(self):
        # desired_start_date = "09/01/2023"
        # desired_end_date = "09/30/2023"

        # Click the calendar toggle button to open date picker
        try:
            date_picker_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "datePickerToggleBtn"))
            )
            date_picker_btn.click()
            print("Opened date picker.")
        except Exception as e:
            print("Failed to open date picker:", e)

        # Wait for the date input fields to become visible
        try:
            WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.ID, "startDate"))
            )
            WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.ID, "endDate"))
            )
            print("Date input fields are visible.")
        except Exception as e:
            print("Date input fields did not become visible:", e)

        try:
            start_date_element = self.driver.find_element(By.ID, "startDate")
            end_date_element = self.driver.find_element(By.ID, "endDate")
            
            # Clear existing dates and input new ones
            start_date_element.clear()
            end_date_element.clear()

            start_date_element.send_keys(self.start_date)
            print(f"Set start date to {self.start_date}.")
            
            end_date_element.send_keys(self.end_date)
            print(f"Set end date to {self.end_date}.")
        except Exception as e:
            print("Error setting dates:", e)

        # Click the Apply button to update the calendar
        try:
            apply_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "applyBtn"))
            )
            apply_btn.click()
            print("Clicked Apply button.")
        except Exception as e:
            print("Failed to click Apply button:", e)

        # Wait for the calendar to refresh after applying dates
        time.sleep(5)


    def _adjust_timezone_(self):
        # Open timezone dropdown by clicking the arrow next to current time
        try:
            dropDownArrow = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#economicCurrentTime .dropDownArrowGray"))
            )
            dropDownArrow.click()
            print("Clicked timezone dropdown arrow.")
        except Exception as e:
            print("Failed to click timezone dropdown arrow:", e)

        # Wait for the timezone popup to become visible
        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "economicCurrentTimePop"))
            )
            print("Timezone popup is visible.")
        except Exception as e:
            print("Timezone popup did not become visible:", e)

        # Set timezone to Tehran (+3:30)
        try:
            tehran_tz = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "liTz19"))
            )
            tehran_tz.click()
            print("Timezone set to Tehran.")
        except Exception as e:
            print("Failed to set timezone to Tehran:", e)

        # Wait a moment for timezone change to take effect
        time.sleep(2)


    def _maximum_scroll_to_load_(self):
        # Scroll down repeatedly to load more data
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Wait for new data to load
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break  # No more new data loaded
            last_height = new_height


    def _gathering_page_data_(self) -> list:
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        calendar_table = soup.find('table', {'id': 'economicCalendarData'})
        if not calendar_table:
            print("Calendar table not found.")
            self.driver.quit()
            exit()

        # Extract rows from the table body
        rows = calendar_table.find('tbody').find_all('tr')
        data = []
        current_day = None  # Variable to hold the current day header

        for row in rows:
            # Check if the row is a day header
            day_cell = row.find("td", class_="theDay")
            if day_cell:
                current_day = day_cell.text.strip()
                continue  # Skip further processing for header rows

            cols = row.find_all('td')
            if len(cols) < 7:
                continue

            try:
                time_event = cols[0].text.strip()

                # Combine current day with event time
                datetime_combined = f"{current_day} {time_event}" if current_day else time_event

                currency_elem = cols[1].find('span', {'class': 'flagCur'})
                currency = currency_elem['title'].strip() if currency_elem else cols[1].text.strip()
                importance = cols[2].text.strip()
                event_link = cols[3].find('a')
                event = event_link.text.strip() if event_link else cols[3].text.strip()
                actual = cols[4].text.strip()
                forecast = cols[5].text.strip()
                previous = cols[6].text.strip()
                
                data.append({
                    'Datetime': datetime_combined,  # Combined day and time
                    'Currency': currency,
                    'Importance': importance,
                    'Event': event,
                    'Actual': actual,
                    'Forecast': forecast,
                    'Previous': previous
                })
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        return data

    def save_data_to_csv(self, path: str, data: list):
        df = pd.DataFrame(data)
        file_name = f'economic_calendar_{self.start_date}_to_{self.end_date}.csv'
        df.to_csv(path + file_name, index=False, encoding='utf-8-sig')
        print(f"Data extracted and saved to '{file_name}'.")

