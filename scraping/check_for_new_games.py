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
from datetime import datetime

import duckdb
from selenium import webdriver
from selenium.webdriver.common.by import By

def check_for_new_games(driver, year, modulo):
    """
    Given a year, navigates to the 'Games' page of naturalstattrick.com for that season,
    and checks the list of game IDs against the `last_game_id`. If it
    finds one that hasn't been scraped, return that game ID. If no new game was found,
    return nothing.
    """
    # Regular season
    base_url = f'https://www.naturalstattrick.com/games.php?fromseason={year}{year+1}&'\
               f'thruseason={year}{year+1}6&stype=2&sit=5v5&loc=B&team=All&rate=n'

    # Playoffs
    #base_url = f'https://www.naturalstattrick.com/games.php?fromseason={year}{year+1}&'\
    #           f'thruseason={year}{year+1}&stype=3&sit=5v5&loc=B&team=All&rate=n'

    # Pre-season
    #base_url = f'https://www.naturalstattrick.com/games.php?fromseason={year}{year+1}&'\
    #           f'thruseason={year}{year+1}&stype=1&sit=5v5&loc=B&team=All&rate=n'

    print(f"Accessing {base_url}")
    driver.get(base_url)

    time.sleep(2)

    report_elements = driver.find_elements(By.LINK_TEXT, "Limited Report")
    href_values = [element.get_dom_attribute('href') for element in report_elements]

    game_id = None
    found = False

    reported_ids = get_existing_game_ids(year)

    for value in href_values:
        nst_game_id = int(value.split('game=')[1].split('&view')[0])

        # For the playoffs, series reports links end in 0 while game report links end in 1
        # We only want the game reports so skip if value % 0 == 0
        #if nst_game_id % 10 == 0:
        #    continue

        if modulo >= 0 and nst_game_id % 5 != modulo:
            continue

        if nst_game_id not in set(reported_ids):
            game_id = nst_game_id
            found = True
            break

    if not found:
        print("No new games found, exiting....")
        return None

    print(f"Found new game with ID {game_id}")
    return game_id


def get_existing_game_ids(year: int) -> set[int]:
    """
    Queries the database to get a set of all the game IDS already included.

    :param int year: Season for which to check DB.
    :return set[int]: Set of game report IDs.
    """
    ids = {}
    conn = duckdb.connect(database='md:', read_only=True)

    ids = set(conn.sql(f"SELECT DISTINCT gameID FROM skater_games WHERE season = {year}").pl()['gameID'])
    conn.close()

    return ids


def main(year, modulo):
    """
    Checks that a new game ID exists for that year and sets it as an output for subsequent
    step in workflow.

    If no new game ID exists, exit gracefully.

    If modulo is provided, this will only scrape gameIDs where gameID % 5 == modulo.
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
            game_id = check_for_new_games(driver, year, modulo)

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
    parser.add_argument('-y', '--year', type=int,
                        default=datetime.now().year - 1 if datetime.now().month < 10 \
                                else datetime.now().year,
                        help='Year corresponding to season for which to scrape games. '\
                             'E.g., 2024 corresponds to the 2024/2025 season')
    parser.add_argument('-m', '--modulo', default=-1, type=int,
                        help='If set, only return new games where gameID % 5 == args.modulo'\
                             ' (used for scaling scraping horizontally.)')
    args = parser.parse_args()

    main(args.year, args.modulo)
