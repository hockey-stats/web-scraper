"""
Meant to be called as part of a workflow for scraping game tables. Should be called in the
step immediately preceding the actual scraper.

Script that will take the game ID of the last game reported on from the GitHub Org variable,
and check the available finished games on NST to see if there are any more recent games
available.

If so, pass the first found new game ID to the scraping script.

If not, exit gracefully and end the workflow.
"""

import os
import time
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By

def check_for_new_games(driver, year, last_game_id):
    """
    Given a year, navigates to the 'Games' page of naturalstattrick.com for that season,
    and checks the list of game IDs against the `last_game_id`. If it
    finds one that hasn't been scraped, return that game ID. If no new game was found,
    return nothing.
    """
    base_url = f'https://www.naturalstattrick.com/games.php?fromseason={year}{year+1}&'\
               f'thruseason={year}{year+1}'
    print(f"Accessing {base_url}")
    driver.get(base_url)

    time.sleep(2)

    report_elements = driver.find_elements(By.LINK_TEXT, "Limited Report")
    href_values = [element.get_dom_attribute('href') for element in report_elements]

    game_id = None
    found = False
    for value in href_values:
        nst_game_id = int(value.split('game=')[1].split('&view')[0])
        if nst_game_id > last_game_id:
            game_id = nst_game_id
            found = True
            break

    if not found:
        print("No new games found, exiting....")
        return None

    print(f"Found new game with ID {game_id}")
    return game_id


def main(year, last_game_id):
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
            game_id = check_for_new_games(driver, year, last_game_id)

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
    parser.add_argument('-g', '--last_game_id', required=True, type=int,
                        help='The NST Game ID of the last game reported on.')
    args = parser.parse_args()

    main(args.year, args.last_game_id)
