"""
Script that uses Selenium to scrape a table of every result in a team's schedule from baseball
reference.

Saves the output as a CSV file.
"""

import os
import time
import argparse
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By


def get_team_table(driver: webdriver, year: int, teams: list[str]) -> None:
    """
    For each team in the division, open the baseball-reference page and scrape scoring
    data for each game.
    """
    # Store the data in lists
    teams_col = []
    game_num = []
    runs_for = []
    runs_against = []

    for team in teams:
        url = f'https://www.baseball-reference.com/teams/{team}/{year}-schedule-scores.shtml'
        print(f"Accessing {url}...")
        driver.get(url)
        time.sleep(3)

        table = driver.find_element(By.ID, 'all_team_schedule').find_element(By.TAG_NAME, 'table')

        # First row is headers, take from first row onwards
        rows = table.find_elements(By.TAG_NAME, 'tr')[1:]

        # Maintain count of consecutive empty rows, once streak hits 3 then we've got everything
        # we need from completed games, so exit loop
        empty_streak = 0

        game_number = 1
        for row in rows:
            if empty_streak > 2:
                break

            cells = row.find_elements(By.TAG_NAME, 'td')

            # Rows containing data for completed games will have 21 cells
            if len(cells) < 21:
                empty_streak += 1
                continue

            empty_streak = 0
            teams_col.append(team)
            game_num.append(game_number)
            runs_for.append(cells[6].text)
            runs_against.append(cells[7].text)

            game_number += 1

    # Load data into a DataFrame and write to a csv
    df = pd.DataFrame({
        'team': teams_col,
        'game_number': game_num,
        'runs_for': runs_for,
        'runs_against': runs_against
    })

    df.to_csv('team_records.csv', index=False)


def main(year: int, division: int):
    """
    Given a year and division marker, scrape game-by-game runs for/against for each team in that
    division.

    :param year: _description_
    :param division: _description_
    :raises e: _description_
    """

    teams = {
        0: ['TOR', 'BOS', 'NYY', 'TBR', 'BAL'],
        1: ['SEA', 'HOU', 'LAA', 'TEX', 'ATH'],
        2: ['CLE', 'DET', 'KCR', 'MIN', 'CHW'],
        3: ['MIA', 'WSN', 'ATL', 'NYM', 'PHI'],
        4: ['SDP', 'COL', 'SFG', 'LAD', 'ARI'],
        5: ['STL', 'MIL', 'CHC', 'CIN', 'PIT']
    }

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-dev-shm-usage')

    retries = 3
    while retries > 0:
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.command_executor.set_timeout(250)
            print(f"Getting game tables, attempt {4 - retries}...")
            time.sleep(2)

            get_team_table(driver, year, teams[division])
        except Exception as e:
            retries -= 1
            driver.quit()
            if retries == 0:
                raise e
        else:
            driver.quit()
            break

    print("Scrape complete")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-y', '--year', default=datetime.now().year, type=int,
                        help='Year corresponding to season for which to scrape games.')
    parser.add_argument('-d', '--division', required=True, type=int,
                       help='Integer between 0 and 6, corresponding to each division.')
    args = parser.parse_args()

    main(year=args.year, division=args.division)
