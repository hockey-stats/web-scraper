"""
Meant to be called as part of a workflow for scraping game tables. Should be called in the
step immediately preceding the actual scraper.

Script that will query the games table to check what IDs have been scraped already, compare
that to the games available on NST, and if a new one was found, set that game ID as an output
for the next scraping step.

If not, exit gracefully and end the workflow.
"""

import os
import time
import argparse

import duckdb
from selenium import webdriver
from selenium.webdriver.common.by import By

def check_for_new_games(driver, year):
    """
    Given a year, navigates to the 'Games' page of naturalstattrick.com for that season,
    and checks the list of game IDs against the `last_game_id`. If it
    finds one that hasn't been scraped, return that game ID. If no new game was found,
    return nothing.
    """
    # Regular season
    #base_url = f'https://www.naturalstattrick.com/games.php?fromseason={year}{year+1}&'\
    #           f'thruseason={year}{year+1}'

    # Playoffs
    #base_url = f'https://www.naturalstattrick.com/games.php?fromseason={year}{year+1}&'\
    #           f'thruseason={year}{year+1}&stype=3&sit=5v5&loc=B&team=All&rate=n'

    # Pre-season
    base_url = f'https://www.naturalstattrick.com/games.php?fromseason={year}{year+1}&'\
               f'thruseason={year}{year+1}&stype=1&sit=5v5&loc=B&team=All&rate=n'

    print(f"Accessing {base_url}")
    driver.get(base_url)

    time.sleep(2)

    report_elements = driver.find_elements(By.LINK_TEXT, "Limited Report")
    href_values = [element.get_dom_attribute('href') for element in report_elements]

    game_id = None
    found = False

    reported_ids = get_existing_game_ids()

    for value in href_values:
        nst_game_id = int(value.split('game=')[1].split('&view')[0])

        # For the playoffs, series reports links end in 0 while game report links end in 1
        # We only want the game reports so skip if value % 0 == 0
        #if nst_game_id % 10 == 0:
        #    continue

        if nst_game_id not in set(reported_ids):
            game_id = nst_game_id
            found = True
            break

    if not found:
        print("No new games found, exiting....")
        return None

    print(f"Found new game with ID {game_id}")
    return game_id


def get_existing_game_ids() -> set[int]:
    """
    Queries the database to get a set of all the game IDS already included.

    :return set[int]: Set of game report IDs.
    """
    ids = {}
    conn = duckdb.connect(database='md:', read_only=True)

    ids = set(conn.sql("SELECT DISTINCT gameID FROM preseason_skater_games").pl()['gameID'])
    conn.close()

    return ids


def main(year):
    """
    Checks that a new game ID exists for that year and sets it as an output for subsequent
    step in workflow.

    If no new game ID exists, exit gracefully.
    """

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    retries = 3
    while retries > 0:
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print(f"Getting game IDs, attempt {4 - retries}...")
            time.sleep(2)
            game_id = check_for_new_games(driver, year)

        except Exception as e:
            retries -= 1
            driver.quit()
            if retries == 0:
                raise e
        else:
            driver.quit()
            break

    print("Scrape complete")
    if not game_id:
        print("No new game found...")
        game_id = "NONE"

    print(f"New game found! ID is {game_id}")

    # Set new game ID as GitHub ouput
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as fh:
        print(f"game_id={game_id}", file=fh)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-y', '--year', default=2024, type=int,
                        help='Year corresponding to season for which to scrape games. '\
                             'E.g., 2024 corresponds to the 2024/2025 season')
    args = parser.parse_args()

    main(args.year)
