# Atlanta-BSA-Scraper
# Scrape Events BSA - Project README

This project scrapes event information from three different sources:
- Silver Comet District Website
- Google Calendar
- Atlanta Area Council Website

The script merges, deduplicates, and outputs a single CSV file containing upcoming events.

---

## Setup Instructions

### 1. Install Python

If you don't already have Python installed, download and install it from:
- [https://www.python.org/downloads/](https://www.python.org/downloads/)

Make sure to install **Python 3.8 or later** and select the option to **"Add Python to PATH"** during installation.

Verify your installation with:
```bash
python --version
```

---

### 2. Install Required Libraries

Run the following command in your terminal or command prompt:

```bash
pip install pandas selenium beautifulsoup4 google-api-python-client google-auth google-auth-oauthlib webdriver-manager
```

This installs:
- `pandas`
- `selenium`
- `beautifulsoup4`
- `google-api-python-client`, `google-auth`, `google-auth-oauthlib`
- `webdriver-manager`

---

### 3. Google Calendar Setup

To access your Google Calendar, you must authorize the script via OAuth:

#### Step-by-Step to Get `credentials.json`:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one.
3. Enable the **Google Calendar API**.
4. Go to **APIs & Services > Credentials**.
5. Click **Create Credentials > OAuth Client ID**.
6. Choose **Desktop App**, name it, then click **Create**.
7. Click **Download JSON** — save it as `credentials.json` in your script directory.

#### First-Time Token Generation:

- When you run the script, a browser window will open.
- Log into your Google account and authorize access.
- A file called `token.json` will be created — this stores your session.
- On future runs, the script will reuse `token.json` for access.

If you want to reset your connection, delete `token.json` and re-run the script.

---

## Running the Script

Run the script with:

```bash
python ScrapeEventsBSA.py
```

The script outputs a CSV file `merged_event_details.csv` containing:
- Event Name
- Start Date
- End Date
- Earliest Time
- Latest Time
- Address
- Website
- Description

---

## Features

- Filters events to **today through 4 months ahead**.
- **Removes duplicate events** (same Event Name + Start Date).
- **Excludes past events**.
- Sorts the final CSV by Start Date ascending.

---

## Troubleshooting

- Ensure you have the latest **Google Chrome** installed.
- If ChromeDriver issues arise, update with:
```bash
pip install --upgrade webdriver-manager
```
- For Google auth issues, delete `token.json` and rerun the script.

---

## License

This project is private and intended for use by the event scraping project owners only.

