"""
Simple script to get a list of all game IDs in a given season and write them to a text
file.
"""

import time
import argparse

from selenium import webdriver
from selenium.webdriver.common.by import By

def get_game_ids(driver, year):
    # Regular season
    base_url = f'https://www.naturalstattrick.com/games.php?fromseason={year}{year+1}&'\
               f'thruseason={year}{year+1}&stype=2&sit=5v5&loc=B&team=All&rate=n'

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

    game_ids = list()

    for value in href_values:
        nst_game_id = int(value.split('game=')[1].split('&view')[0])
        print(nst_game_id)
        game_ids.append(nst_game_id)

        # For the playoffs, series reports links end in 0 while game report links end in 1
        # We only want the game reports so skip if value % 0 == 0
        #if nst_game_id % 10 == 0:
        #    continue

    return set(game_ids)


def main(year):

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    retries = 3
    while retries > 0:
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print(f"Getting game IDs, attempt {4 - retries}...")
            time.sleep(2)
            game_ids = get_game_ids(driver, year)

        except Exception as e:
            retries -= 1
            driver.quit()
            if retries == 0:
                raise e
        else:
            driver.quit()
            break

    print("Scrape complete")

    print(f"Found {len(game_ids)} unique game IDs.")

    with open(f'game_ids_{year}.txt', 'w') as f:
        for ids in game_ids:
            f.writelines(str(ids) + '\n')

    print("file write complete")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-y', '--year', default=2024, type=int,
                        help='Year corresponding to season for which to scrape games. '\
                             'E.g., 2024 corresponds to the 2024/2025 season')
    args = parser.parse_args()

    main(args.year)
