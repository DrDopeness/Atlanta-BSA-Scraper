import re
import time
import os
import csv
import pandas as pd
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from webdriver_manager.chrome import ChromeDriverManager

# Define constants
BASE_URL = "https://www.silvercometdistrictbsa.org/"
EVENTS_PAGE = BASE_URL + "events-1"
TARGET_DOMAINS = [
    "https://www.silvercometdistrictbsa.org/events/",
    "https://forms.tentaroo.com/"
]
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
EXCLUDED_KEYWORDS = ['IOLS', 'MERIT BADGE', 'NYLT', 'CLOSED']

# Regex patterns
DATE_PATTERN = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}"
TIME_PATTERN = r"\b\d{1,2}:\d{2}\s?(?:AM|PM)\b"
ADDRESS_PATTERN = r"\d{1,5}\s+\w+(?:\s\w+)*,?\s+\w+(?:\s\w+)*,?\s+[A-Z]{2}\s+\d{5}"

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def fetch_events_page(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)
        scroll_pause_time = 2
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    except Exception as e:
        print("Warning: Page body not fully loaded.", e)
    return driver.page_source

def parse_links(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        for domain in TARGET_DOMAINS:
            if href.startswith(domain):
                links.append(href)
                break
    return list(set(links))

def scrape_silvercomet_event(driver, url):
    driver.get(url)
    time.sleep(3)
    page_html = driver.page_source
    soup = BeautifulSoup(page_html, 'html.parser')

    event_name_tag = soup.find('h1')
    event_name = event_name_tag.get_text(strip=True) if event_name_tag else ""
    description_tag = soup.find('p')
    description = description_tag.get_text(strip=True) if description_tag else ""

    raw_dates = re.findall(DATE_PATTERN, page_html)
    parsed_dates = []
    for date_str in set(raw_dates):
        try:
            parsed_date = datetime.strptime(date_str, "%B %d, %Y")
            parsed_dates.append(parsed_date)
        except Exception:
            continue

    parsed_dates.sort()
    if parsed_dates:
        start_date = parsed_dates[0]
        end_date = parsed_dates[-1]
    else:
        start_date = end_date = None

    raw_times = re.findall(TIME_PATTERN, page_html)
    times = sorted(set(raw_times))

    earliest_time = times[0] if times else ""
    latest_time = times[-1] if times else ""

    addresses = re.findall(ADDRESS_PATTERN, page_html)

    return {
        "Event Name": event_name,
        "Start Date": start_date.strftime("%m-%d-%Y") if start_date else "",
        "End Date": end_date.strftime("%m-%d-%Y") if end_date else "",
        "Earliest Time": earliest_time,
        "Latest Time": latest_time,
        "Address": ", ".join(set(addresses)),
        "Website": url,
        "Description": description
    }

def authenticate_google_calendar():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_google_calendar_events(service):
    now = datetime.now(timezone.utc).isoformat()
    four_months_later = (datetime.now(timezone.utc) + timedelta(weeks=16)).isoformat()
    events_result = service.events().list(
        calendarId='primary', timeMin=now, timeMax=four_months_later,
        singleEvents=True, orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    event_list = []
    for event in events:
        event_name = event.get('summary', 'No Title')
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        location = event.get('location', 'No Location')
        description = event.get('description', '')

        if 'dateTime' in event['start']:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            start_date = start_dt.strftime('%m-%d-%Y')
            end_date = end_dt.strftime('%m-%d-%Y')
            earliest_time = start_dt.strftime('%I:%M %p')
            latest_time = end_dt.strftime('%I:%M %p')
        else:
            start_date = start
            end_date = end
            earliest_time = 'All Day'
            latest_time = 'All Day'

        event_list.append({
            "Event Name": event_name,
            "Start Date": start_date,
            "End Date": end_date,
            "Earliest Time": earliest_time,
            "Latest Time": latest_time,
            "Address": location,
            "Website": "",
            "Description": description
        })

    return event_list

def scrape_atlanta_area_events(driver):
    url = "https://www.atlantabsa.org/calendar"
    driver.get(url)
    events = []
    today = datetime.now()
    base_year = today.year

    for month in range(4):
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'agenda-event')))
        except Exception:
            continue

        event_rows = driver.find_elements(By.CLASS_NAME, 'agenda-event')

        for event in event_rows:
            try:
                date_time = event.find_element(By.CLASS_NAME, 'date').text.strip()
                if '\n' in date_time:
                    date, time_ = date_time.split('\n')
                else:
                    date, time_ = date_time, 'All-day'

                year_match = re.search(r'(\d{4})', date)
                event_year = int(year_match.group(1)) if year_match else base_year
                date = re.sub(r',? \d{4}', '', date).strip()

                title = event.find_element(By.TAG_NAME, 'h5').text.strip()
                link_element = event.find_element(By.TAG_NAME, 'a')
                link = link_element.get_attribute('href') if link_element else 'N/A'

                parsed_date = datetime.strptime(date + f' {event_year}', '%b %d %Y')
                formatted_date = parsed_date.strftime('%m-%d-%Y')

                if month == 0 and parsed_date.day < today.day:
                    continue

                if any(keyword in title.upper() for keyword in EXCLUDED_KEYWORDS):
                    continue

                earliest_time = latest_time = time_.lower() if time_.lower() != 'all-day' else 'All-day'

                events.append({
                    "Event Name": title,
                    "Start Date": formatted_date,
                    "End Date": formatted_date,
                    "Earliest Time": earliest_time,
                    "Latest Time": latest_time,
                    "Address": '',
                    "Website": link,
                    "Description": ''
                })
            except Exception:
                continue

        try:
            next_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.fc-next-button')))
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(3)
            if today.month + month + 1 > 12:
                base_year += 1
        except Exception:
            break

    return events

def main():
    driver = setup_driver()
    try:
        # Scrape all sources
        html_content = fetch_events_page(driver, EVENTS_PAGE)
        links = parse_links(html_content)
        silvercomet_events = [scrape_silvercomet_event(driver, link) for link in links]

        service = authenticate_google_calendar()
        google_calendar_events = get_google_calendar_events(service)

        atlanta_area_events = scrape_atlanta_area_events(driver)

        combined_events = silvercomet_events + google_calendar_events + atlanta_area_events

        unique_events = []
        seen = set()
        today = datetime.now()
        four_months_later = today + timedelta(weeks=16)

        for event in combined_events:
            try:
                start_date = datetime.strptime(event['Start Date'], "%m-%d-%Y")
            except Exception:
                continue

            if start_date < today or start_date > four_months_later:
                continue

            identifier = (event['Event Name'], event['Start Date'])
            if identifier not in seen:
                seen.add(identifier)
                unique_events.append(event)

        df = pd.DataFrame(unique_events)
        df = df.sort_values(by="Start Date")
        print(df)

        df.to_csv("merged_event_details.csv", index=False)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
