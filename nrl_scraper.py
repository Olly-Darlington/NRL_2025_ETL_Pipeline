"""
NRL.com Stats Scraper

Scrapes team and player statistics from nrl.com for a given season, 2025 in this case.

nrl.com/stats/ is a JavaScript (React) app. The stats tables are fetched
and rendered client-side after the page loads, therefore the best way to 
extract the data is to drive a real headless browser (Chrome via Selenium) 
to let the page's own JavaScript populate the table, then scrape the rendered HTML.

Required Libraries;
selenium, beautifulsoup4, pandas, webdriver-manager

Chrome/Chromium is also required. webdriver-manager will download
a matching driver automatically.

URL STRUCTURE;
Team stats:   https://www.nrl.com/stats/teams/?competition=111&season=2025&stat=<STAT_ID>
Player stats: https://www.nrl.com/stats/players/?competition=111&season=2025&stat=<STAT_ID>

- competition=111  -> NRL Telstra Premiership
- season=2025      -> season year
- stat=<id>        -> which statistic table to show (tries, tackles, etc.)

stat IDs:
Each stat category (tries, run metres, tackle efficiency, etc.) has its own
numeric ID. stat=76 is the ID you linked to. NRL doesn't publish a lookup
table, so manually reading each URL after selecting each stat from selection 
dropdown i deemed the quickest way to discover all the IDs. The IDs are
also not numerically sequential, so iterating through a range of numbers is not reliable.
"""


# Module loading
import time
from pathlib import Path
from dataclasses import dataclass

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

# Config environment

BASE_URL = "https://www.nrl.com/stats/{scope}/"
COMPETITION = 111          # Men's Telstra Premiership (Womens Premiership= 161, Mens State of Origin= 116, Womens State of Origin = 156)
SEASON = 2025
ROUNDS = range(1, 28)      # NRL regular season is 27 rounds, 24 games minumum
OUTPUT_DIR = Path("nrl_data")

# List desired stat IDs as {"label": id}.
STAT_IDS = {
    "Points": 76,
    "Tries": 38,
    "Goals": 1000034,
    "Linebreaks": 30,
    "PCMs": 1000112,
    "Tackle Breaks": 29,
    "Half Breaks": 1000021,
    "Try Assists": 35,
    "Offloads": 28,
    "Line Break Assists": 31,
    "Kick Metres": 32,
    "All Kicks": 33,
    "Tackles": 3,
    "Missed Tackles": 4,
    "Interceptions": 1000004,
    "All Runs": 1000038,
    "Run Metres": 1000037,
    "Kick Return Meteres": 78,
    "Errors": 37,
    "Penalties": 1000026,
    "Handelling Errors": 1000079,
    "Ineffective Tackles": 1000003,
    "Set Restarts": 1000319,
    "Ruck Infringements": 1000283,
}

TABLE_TIMEOUT = 20  # seconds to wait for the stats table to render

# Browser setup

def make_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")

    # opts.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    # opening Chrome, going to chrome://version, and checking "Executable Path".

    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    # webdriver-manager auto-downloads a matching chromedriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


# Core scraping helpers

def build_url(scope: str, stat_id: int | None = None):
    """scope is 'teams' or 'players'."""
    url = BASE_URL.format(scope=scope)
    url += f"?competition={COMPETITION}&season={SEASON}&stat={stat_id}"


def wait_for_table(driver, timeout: int = TABLE_TIMEOUT):
    """
    Waits until a stats table with actual rows has rendered.
    NRL's table usually lives inside a container with a class containing
    'stats-table' or similar; the script falls back to 'any <table> with >1 rows'
    """
    def table_has_rows(drv):
        tables = drv.find_elements(By.TAG_NAME, "table")
        for t in tables:
            rows = t.find_elements(By.TAG_NAME, "tr")
            if len(rows) > 1:
                return t
        return False

    try:
        WebDriverWait(driver, timeout).until(table_has_rows)
    except TimeoutException:
        return None
    return True


def scrape_table(driver) -> pd.DataFrame | None:
    # Parse the first substantial <table> on the rendered page into a DataFrame.
    soup = BeautifulSoup(driver.page_source, "html.parser")

    tables = soup.find_all("table")
    best_table = None
    best_len = 0
    for t in tables:
        rows = t.find_all("tr")
        if len(rows) > best_len:
            best_len = len(rows)
            best_table = t

    if best_table is None or best_len <= 1:
        return None

    headers = [th.get_text(strip=True) for th in best_table.find_all("th")]

    data_rows = []
    for tr in best_table.find_all("tr"):
        cells = tr.find_all("td")
        if not cells:
            continue
        row = [c.get_text(strip=True) for c in cells]
        data_rows.append(row)

    if not headers:
        # Some NRL layouts put the first row of <td>s as a pseudo-header;
        # fall back to generic column names.
        max_cols = max(len(r) for r in data_rows)
        headers = [f"col_{i}" for i in range(max_cols)]

    # Normalise row lengths to header length
    fixed_rows = []
    for r in data_rows:
        if len(r) < len(headers):
            r = r + [""] * (len(headers) - len(r))
        elif len(r) > len(headers):
            r = r[: len(headers)]
        fixed_rows.append(r)

    df = pd.DataFrame(fixed_rows, columns=headers)
    return df


def scrape_one(driver, scope: str, stat_label: str, stat_id: int,
                round_num: int | None) -> pd.DataFrame | None:
    url = build_url(scope, stat_id)
    driver.get(url)

    ok = wait_for_table(driver)
    if not ok:
        print(f"  [!] No table rendered for {url}")
        return None

    # Small extra pause lets any post-render sorting/animation settle
    time.sleep(0.5)

    df = scrape_table(driver)
    if df is None or df.empty:
        print(f"  [!] Table empty for {url}")
        return None

    df.insert(0, "season", SEASON)
    df.insert(1, "stat_category", stat_label)
    df.insert(2, "stat_id", stat_id)
    df["source_url"] = url
    return df

# Orchestration


def scrape_season(scope: str, include_rounds: bool = True) -> dict[str, pd.DataFrame]:
    """
    scope: 'teams' or 'players'
    Returns dict of {stat_label: combined DataFrame season total}
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    driver = make_driver(headless=True)
    results = {}

    try:
        for stat_label, stat_id in STAT_IDS.items():
            print(f"\n=== {scope.upper()} | {stat_label} (stat={stat_id}) ===")
            frames = []

            print(" - season total")
            df_season = scrape_one(driver, scope, stat_label, stat_id, round_num=None)
            if df_season is not None:
                frames.append(df_season)

            if frames:
                combined = pd.concat(frames, ignore_index=True)
                results[stat_label] = combined
                out_path = OUTPUT_DIR / f"{scope}_{stat_label}_{SEASON}.csv"
                combined.to_csv(out_path, index=False)
                print(f" -> saved {out_path} ({len(combined)} rows)")
    finally:
        driver.quit()

    return results


if __name__ == "__main__":

    # Step 1: scrape team stats (season totals + round-by-round)
    team_results = scrape_season(scope="teams", include_rounds=False)

    # Step 2: scrape player stats (season totals + round-by-round)
    player_results = scrape_season(scope="players", include_rounds=False)

    # Comment out Steps one or two in turn to return only team or player stats.
    # If script hangs on one partucular stat, comment the ID out and attempt to run in the nrl_scraper_individualstat.py script on an indvidual basis.

    print("\nDone. CSVs written to:", OUTPUT_DIR.resolve())"""
NRL.com Stats Scraper

Scrapes team and player statistics from nrl.com for a given season,
both for the season as a whole and on a round-by-round basis.

nrl.com/stats/ is a JavaScript (React) app. The stats tables are fetched
and rendered client-side after the page loads, therefore the best way to 
extract the data is to drive a real headless browser (Chrome via Selenium) 
to let the page's own JavaScript populate the table, then scrape the rendered HTML.

Required Libraries;
selenium, beautifulsoup4, pandas, webdriver-manager

Chrome/Chromium is also required. webdriver-manager will download
a matching chromedriver automatically.

URL STRUCTURE;
Team stats:   https://www.nrl.com/stats/teams/?competition=111&season=2025&stat=<STAT_ID>
Player stats: https://www.nrl.com/stats/players/?competition=111&season=2025&stat=<STAT_ID>

- competition=111  -> NRL Telstra Premiership
- season=2025      -> season year
- stat=<id>        -> which statistic table to show (tries, tackles, etc.)

NOTE ON stat IDs
----------------
Each stat category (tries, run metres, tackle efficiency, etc.) has its own
numeric ID. stat=76 is the ID you linked to. NRL doesn't publish a lookup
table, so manually reading each URL after selecting each stat from selection dropdown i deemed the quickest way to discover all the IDs.
"""

import time
from pathlib import Path
from dataclasses import dataclass

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

BASE_URL = "https://www.nrl.com/stats/{scope}/"
COMPETITION = 111          # Men's Telstra Premiership (Womens Premiership= 161, Mens State of Origin= 116, Womens State of Origin = 156)
SEASON = 2025
ROUNDS = range(1, 28)      # NRL regular season is 27 rounds, 24 games minumum
OUTPUT_DIR = Path("nrl_data")

# List desired stat IDs as {"label": id}.
STAT_IDS = {
    "Points": 76,
    "Tries": 38,
    "Goals": 1000034,
    "Linebreaks": 30,
    "PCMs": 1000112,
    "Tackle Breaks": 29,
    "Half Breaks": 1000021,
    "Try Assists": 35,
    "Offloads": 28,
    "Line Break Assists": 31,
    "Kick Metres": 32,
    "All Kicks": 33,
    "Tackles": 3,
    "Missed Tackles": 4,
    "Interceptions": 1000004,
    "All Runs": 1000038,
    "Run Metres": 1000037,
    "Kick Return Meteres": 78,
    "Errors": 37,
    "Penalties": 1000026,
    "Handelling Errors": 1000079,
    "Ineffective Tackles": 1000003,
    "Set Restarts": 1000319,
    "Ruck Infringements": 1000283,
}

TABLE_TIMEOUT = 20  # seconds to wait for the stats table to render


# --------------------------------------------------------------------------
# Browser setup
# --------------------------------------------------------------------------

def make_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")

    # opts.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    # opening Chrome, going to chrome://version, and checking "Executable Path".

    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    # webdriver-manager auto-downloads a matching chromedriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


# --------------------------------------------------------------------------
# Core scraping helpers
# --------------------------------------------------------------------------

def build_url(scope: str, stat_id: int, round_num: int | None = None) -> str:
    """scope is 'teams' or 'players'."""
    url = BASE_URL.format(scope=scope)
    url += f"?competition={COMPETITION}&season={SEASON}&stat={stat_id}"
    # Dependancy to scrape round by round - must be conducted during the season as an automation as the website does not retain this data after the round has passed.
    if round_num is not None:
        url += f"&round={round_num}"
    return url


def wait_for_table(driver, timeout: int = TABLE_TIMEOUT):
    """
    Waits until a stats table with actual rows has rendered.
    NRL's table usually lives inside a container with a class containing
    'stats-table' or similar; the script falls back to 'any <table> with >1 rows'
    """
    def table_has_rows(drv):
        tables = drv.find_elements(By.TAG_NAME, "table")
        for t in tables:
            rows = t.find_elements(By.TAG_NAME, "tr")
            if len(rows) > 1:
                return t
        return False

    try:
        WebDriverWait(driver, timeout).until(table_has_rows)
    except TimeoutException:
        return None
    return True


def scrape_table(driver) -> pd.DataFrame | None:
    # Parse the first substantial <table> on the rendered page into a DataFrame.
    soup = BeautifulSoup(driver.page_source, "html.parser")

    tables = soup.find_all("table")
    best_table = None
    best_len = 0
    for t in tables:
        rows = t.find_all("tr")
        if len(rows) > best_len:
            best_len = len(rows)
            best_table = t

    if best_table is None or best_len <= 1:
        return None

    headers = [th.get_text(strip=True) for th in best_table.find_all("th")]

    data_rows = []
    for tr in best_table.find_all("tr"):
        cells = tr.find_all("td")
        if not cells:
            continue
        row = [c.get_text(strip=True) for c in cells]
        data_rows.append(row)

    if not headers:
        # Some NRL layouts put the first row of <td>s as a pseudo-header;
        # fall back to generic column names.
        max_cols = max(len(r) for r in data_rows)
        headers = [f"col_{i}" for i in range(max_cols)]

    # Normalise row lengths to header length
    fixed_rows = []
    for r in data_rows:
        if len(r) < len(headers):
            r = r + [""] * (len(headers) - len(r))
        elif len(r) > len(headers):
            r = r[: len(headers)]
        fixed_rows.append(r)

    df = pd.DataFrame(fixed_rows, columns=headers)
    return df


def scrape_one(driver, scope: str, stat_label: str, stat_id: int,
                round_num: int | None) -> pd.DataFrame | None:
    url = build_url(scope, stat_id, round_num)
    driver.get(url)

    ok = wait_for_table(driver)
    if not ok:
        print(f"  [!] No table rendered for {url}")
        return None

    # Small extra pause lets any post-render sorting/animation settle
    time.sleep(0.5)

    df = scrape_table(driver)
    if df is None or df.empty:
        print(f"  [!] Table empty for {url}")
        return None

    df.insert(0, "season", SEASON)
    # df.insert(1, "round", round_num if round_num is not None else "season_total") # uncomment if scraping round-by-round stats
    df.insert(1, "stat_category", stat_label) # adjust index if round-by-round stats are included
    df.insert(2, "stat_id", stat_id)
    df["source_url"] = url
    return df


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def scrape_season(scope: str, include_rounds: bool = True) -> dict[str, pd.DataFrame]:
    """
    scope: 'teams' or 'players'
    Returns dict of {stat_label: combined DataFrame (season total + all rounds)}
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    driver = make_driver(headless=True)
    results = {}

    try:
        for stat_label, stat_id in STAT_IDS.items():
            print(f"\n=== {scope.upper()} | {stat_label} (stat={stat_id}) ===")
            frames = []

            print(" - season total")
            df_season = scrape_one(driver, scope, stat_label, stat_id, round_num=None)
            if df_season is not None:
                frames.append(df_season)

            if frames:
                combined = pd.concat(frames, ignore_index=True)
                results[stat_label] = combined
                out_path = OUTPUT_DIR / f"{scope}_{stat_label}_{SEASON}.csv"
                combined.to_csv(out_path, index=False)
                print(f" -> saved {out_path} ({len(combined)} rows)")
    finally:
        driver.quit()

    return results


if __name__ == "__main__":

    # Step 1: scrape team stats (season totals + round-by-round)
    team_results = scrape_season(scope="teams", include_rounds=False)

    # Step 2: scrape player stats (season totals + round-by-round)
    player_results = scrape_season(scope="players", include_rounds=False)

    # Comment out Steps one or two in turn to return only team or player stats.
    # If script hangs on one partucular stat, comment the ID out and attempt to run in the nrl_scraper_individualstat.py script on an indvidual basis.

    print("\nDone. CSVs written to:", OUTPUT_DIR.resolve())
