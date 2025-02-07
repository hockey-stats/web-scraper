"""
Script that uses Selenium to scrape game-by-game statistics from NaturalStatTrick.com, and uses
this to update a DB that stores such data. 

The tables that are to be added will be determined by what already does or does not exist in the
DB.
"""

import os
import time
import glob
import shutil
import argparse
import itertools
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By

from util.team_maps import nst_team_mapping


def get_game_tables(driver, year, finished_games):
    """
    Given a year, navigates to the 'Games' page of NST for that season, and download game
    data for the first game not already reported on.
    :param ChromeDriver driver: ChromeDriver object that will do the scraping.
    :param int year: Year corresponding to the season.
    :param set(int) finished_games: Set of gameIDs already reported, which need not be scraped.
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
        if nst_game_id not in finished_games:
            game_id = nst_game_id
            found = True

    if not found:
        print("No new games found, exiting....")
        return

    print(f"Scraping game with ID {game_id}")
    
    report_url = f'https://naturalstattrick.com/game.php?season={year}{year+1}&'\
                 f'game={game_id}&view=limited'
    print(f"Accessing {report_url}")
    driver.get(report_url)
    time.sleep(2)
    report_title = driver.find_element(By.XPATH, '//div[1]/div[5]/div/center/h1').text
    away_team, home_team = report_title.split(' @ ')

    # Get the game data and store values for adding to the filename
    game_date = driver.find_element(By.XPATH, '//div[1]/div[5]/div/center/h2').text
    print(game_date.split('\n'))
    yy, mm, dd = game_date.split('\n')[0].split('-')

    # Map the team full names to the acronyms, i.e. Buffalo Sabres -> BUF
    away_team = nst_team_mapping[away_team]
    home_team = nst_team_mapping[home_team]
    # NOTE Some team acronyms are slightly different in NST than Moneypuck, e.g.
    # NJ instead of NJD. Make sure all of these cases are handled when updating DB.

    # Navigate to each table in the game report and click the sections to have the download
    # buttons appear. Find the tables by using element IDs, where
    #   "{team}stlb" -> Individual stats for team, and
    #   "{team}oilb" -> On-ice stats for team

    # We achieve each combination of team, state, and table by using itertools.product
    teams = [away_team, home_team]
    game_states = ['all', 'ev', 'pp', 'pk']
    tables = ['st', 'oi']
    for team, table, state in itertools.product(teams, tables, game_states):

        # Refresh the page after each iteration to avoid issues
        driver.get(report_url)
        time.sleep(2)

        # Find and click the label to expand the table
        table_label = driver.find_element(By.ID, f"{team}{table}lb")
        driver.execute_script('arguments[0].click()', table_label)

        # Get the element representing the entire section of the table as a sibling
        # element to the label
        table_section = table_label.find_element(By.XPATH, '../div[1]')
        state_labels = table_section.find_elements(By.XPATH, './label')

        for state_label in state_labels:
            # Text of the state labels will look like:
            #   ['All', 'EV', '5v5', '5v4 PP', '4v5 PK']
            if state in state_label.text.lower():
            # Click the one corresponding to this iteration
                driver.execute_script('arguments[0].click()', state_label)
                time.sleep(1)
                break

        # Now that the correct table for the state is active, click the download button
        table_id = f'tb{team}{table}{state}_wrapper'
        print(table_id)
        table_element = driver.find_element(By.ID, table_id)
        dl_button = table_element.find_element(By.CLASS_NAME,
                                               'dt-button.buttons-csv.buttons-html5')
        print("Downloading..")
        driver.execute_script('arguments[0].click()', dl_button)
        time.sleep(4)

        # Rename and move the downloaded table
        source = glob.glob('/root/Downloads/*csv')[0]
        dest = f'tables/{game_id}_{team}_{state}_{table}.csv'
        shutil.move(source, dest)
        print(f'Moving file {source} -> {dest}')

        # If we're gathering inidivudal stats, also grab goalie table
        if table == 'st':
            table_parent = table_element.find_element(By.XPATH, '..')
            goalie_table = table_parent.find_element(By.ID, f'tb{team}stgall_wrapper')
            dl_button = goalie_table.find_element(By.CLASS_NAME,
                                                  'dt-button.buttons-csv.buttons-html5')
            print("Downloading goalie chart...")
            dl_button.click()
            time.sleep(4)

            # Rename and move table
            source = glob.glob('/root/Downloads/*csv')[0]
            dest = f'tables/{yy}-{mm}-{dd}_{game_id}_{team}_{state}_goalies.csv'
            shutil.move(source, dest)
            print(f'Moving file {source} -> {dest}')


def main(year):
    """
    Main function which initializes and runs the scraper.
    :param int year: Year corresponding to the season for which data should be scraped, e.g.
                 '2024' would mean the 2024/2025 season.
    """

    # Create a directory to store the tables, if it doesn't already exist
    if not os.path.isdir('tables/'):
        os.mkdir('tables/')

    if not os.path.isfile(f"finished_game_ids_{year}.txt"):
        raise FileNotFoundError(f"No 'finished_game_ids_{year}.txt' file, aborting...")

    with open(f"finished_game_ids_{year}.txt", 'r', encoding='utf-8') as f:
        finished_games = set([x.strip() for x in f.readlines()])

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    retries = 3
    while retries > 0:
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print(f"Getting game tables, attempt {4 - retries}...")
            time.sleep(2)

            get_game_tables(driver, year, finished_games)
        except Exception as e:
            raise e
            retries -= 1
            driver.quit()
        else:
            driver.quit()
            break

    print("Scrape complete")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-y', '--year', default=2024, type=int,
                        help='Year corresponding to season for which to scrape games. '\
                             'E.g., 2024 corresponds to the 2024/2025 season')
    args = parser.parse_args()

    main(args.year)
