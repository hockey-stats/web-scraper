"""
Script that uses Selenium to scrape game-by-game statistics from NaturalStatTrick.com, and uses
this to update a DB that stores such data. 

The tables that are to be added will be determined by what already does or does not exist in the
DB.
"""

import os
import time
import argparse
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By


def get_game_tables(driver, year, games_in_db):
    """
    Given a year, navigates to the 'Games' page of NST for that season, and download game
    data for any game not already included in DB.
    :param ChromeDriver driver: ChromeDriver object that will do the scraping.
    :param int year: Year corresponding to the season.
    :param set(int) games_in_db: Set of gameIDs already in DB, which need not be scraped.
    """
    base_url = f'https://www.naturalstattrick.com/games.php?fromseason={year}{year+1}&'\
               f'thruseason={year}{year+1}'
    driver.get(base_url)
    time.sleep(2)
    report_elements = driver.find_elements_by(By.LINK_TEXT, "Limited Report")
    href_values = [element.get_dom_attributes('href') for element in report_elements]
    reports_to_add = set()
    for value in href_values:
        nst_game_id = value.split('game=')[1].split('&view')[0]
        if nst_game_id not in games_in_db:
            reports_to_add.append('https://www.naturalstattrick.com/' + value)

    for report_url in reports_to_add:
        driver.get(report_url)
        time.sleep(2)
        report_title = driver.find_element(By.XPATH, '//div[1]/div[5]/div/center/h1').text
        away_team, home_team = report_title.split(' @ ')

        #TODO Map the team full names to the acronyms, i.e. Buffalo Sabres -> BUF

        # Navigate to each table in the game report and click the sections to have the download
        # buttons appear. Find the tables by using element IDs, where 
        #   "{team}stlb" -> Individual stats for team, and
        #   "{team}oilb" -> On-ice stats for team
        # Thus, the following clicks on the banner to expand the table for the away team's
        # individual table:

        driver.find_element(By.ID, f"{away_team}stlb").click()

        # Now that the table is expanded, can find and click on the download button
        # First get the table, and then the button as a child of that table
        table = driver.find_element(By.ID, 'tbBUFst5v5_wrapper')
        button = table.find_element(By.CLASS_NAME, 'dt-button.buttons-csv.buttons-html5')
        
        # This downloads the file to ~/Downloads (i.e. /root/Downloads in the container)
        # by default.
        # TODO Update download directory (maybe).
        button.click()

        # TODO From here, need to repeat these steps for 5v4 and 4v5, and then do the same
        # for the other tables (individual and on-ice stats for each team)

        # To switch the table from 5v5 to 5v4 or 4v5, first find the element for the full 
        # section by navigating to the grandparent of the table:
        full_section = table.find_element(By.XPATH, '../..')

        # The game-state buttons can then be found as children to this element
        labels = full_section.find_elements(By.XPATH, './label')

        # 'labels' should corredpond to a list of 5 webdriver objects correspoding to
        # ['All', 'EV', '5v5', '5v4 PP', '4v5 PK'].
        # With these we can just do something like:
        for label in labels:
            if label.text in {'5v4 PP', '4v5 PK'}:
                # Have to click the label like this, instead of 'click()'
                driver.execute_script('arguments[0].click()', label)

                # Now download the CSV as before
                table_name = f'tb{team}stpp' if label.text == '5v4 PP' else f'tb{team}stpk'
                table = driver.find_element(By.ID, f'{table_name}_wrapper')
                button = table.find_element(By.CLASS_NAME, 'dt-button.buttons-csv.buttons-html5')
                button.click()

        # TODO: Add logic for other 3 table sections


def main(year):
    """
    Main function which initializes and runs the scraper.
    :param int year: Year corresponding to the season for which data should be scraped, e.g.
                 '2024' would mean the 2024/2025 season.
    """
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    retries = 3
    while retries > 0:
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print(f"Getting game tables, attempt {4 - retries}...")
            time.sleep(2)
            games_in_db = set(range(20001, 21312))
