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
from selenium import webdriver
from selenium.webdriver.common.by import By

from util.team_maps import nst_team_mapping


def get_game_tables(driver, year, game_id):
    """
    Given a game_id, navigates to the page for that game and scrape the requisite tables.
    :param ChromeDriver driver: ChromeDriver object that will do the scraping.
    :param int year: Year for which to check
    :param int game_id: Game ID for which to scrape data.
    """

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

        time.sleep(6)

        download_filepath = '/github/home/Downloads/*csv'

        # Find the files
        search = glob.glob(download_filepath)
        print(f"search results: {search}")

        # Rename and move the downloaded table
        source = glob.glob(download_filepath)[0]
        dest = f'tables/{yy}-{mm}-{dd}_{game_id}_{team}_{state}_{table}.csv'
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
            source = glob.glob(download_filepath)[0]
            dest = f'tables/{yy}-{mm}-{dd}_{game_id}_{team}_{state}_goalies.csv'
            shutil.move(source, dest)
            print(f'Moving file {source} -> {dest}')


def main(year, game_id):
    """
    Main function which initializes and runs the scraper.
    """

    # Create a directory to store the tables, if it doesn't already exist
    if not os.path.isdir('tables/'):
        os.mkdir('tables/')

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    chrome_prefs = {"download.default_directory": "./tables"}
    chrome_options.experimental_options["prefs"] = chrome_prefs
    retries = 3
    while retries > 0:
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print(f"Getting game tables, attempt {4 - retries}...")
            time.sleep(2)

            get_game_tables(driver, year, game_id)
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
    parser.add_argument('-y', '--year', default=2024, type=int,
                        help='Year corresponding to season for which to scrape games. '\
                             'E.g., 2024 corresponds to the 2024/2025 season')
    parser.add_argument('-g', '--game_id',
                        help='Game ID in naturalstattrick for which to scrape game data.')
    args = parser.parse_args()

    main(year=args.year, game_id=args.game_id)
