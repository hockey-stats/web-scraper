import os
import time
import glob
import shutil
import argparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

"""
Script that uses selenium to navigate to various web pages holding team tables and download them.
"""


def get_nst_table(driver, year):
    base_url = f'http://naturalstattrick.com/teamtable.php?fromseason={year}{year+1}&thruseason={year}{year+1}'\
               f'&stype=2&sit=sva&score=all&rate=y&team=all&loc=B&gpf=410&fd=&td='
    driver.get(base_url)
    dl_button =  driver.find_elements_by_xpath('/html/body/div[1]/div[5]/div/div/input[23]')[0]
    dl_button.click()


def get_eh_table(driver, year):
    driver.get('https://evolving-hockey.com/login/')
    #driver.find_element_by_id('user_login').send_keys(config.eh_username)
    #driver.find_element_by_id('user_pass').send_keys(config.eh_password)
    driver.find_element_by_id('user_pass').send_keys(Keys.ENTER)
    base_url = f'https://evolving-hockey.com/stats/team_standard/?_inputs_&std_tm_str=%225v5%22&std_tm_span=%22Regular%22&'\
               f'std_tm_type=%22Rates%22&std_tm_group=%22Season%22&std_tm_table=%22On-Ice%22&std_tm_team=%22All%22&std_tm_range'\
               f'=%22Seasons%22&std_tm_adj=%22Score%20%26%20Venue%22&dir_ttbl=%22Stats%22&std_tm_season=%22{year}{year+1}%22'
    driver.get(base_url)
    time.sleep(2)
    dl_button = driver.find_element_by_id('std_tm_download_ui').find_element_by_xpath('./*')
    dl_button.click()


def get_mp_table(driver, year):
    driver.get('https://moneypuck.com/data.htm')
    dl_button = driver.find_element_by_xpath(f'//a[@href="moneypuck/playerData/seasonSummary/{year}/regular/teams.csv"]')
    dl_button.click()


def organize_tables():
    map_pairs = [('teams.csv', 'mp_team_table.csv')]
#    map_pairs = [('*EH*.csv', 'eh_team_table.csv'),
#                 ('*Natural*.csv', 'nst_team_table.csv'),
#                 ('teams.csv', 'mp_team_table.csv')]
    if not os.path.isdir('/tables/'):
        os.mkdir('/tables')

    for exp, dest in map_pairs:
        source = glob.glob(f'./{exp}')[0]
        dest = f'/tables/{dest}'
        shutil.move(source, dest)
        print(f'{source} -> {dest}')


def main(year):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    retries = 3
    while retries > 0:
        try:
            driver = webdriver.Chrome(chrome_options=chrome_options)
            print('Getting MP table...')
            time.sleep(2)
            get_mp_table(driver, year)
            time.sleep(2)
        except:
            print(f"Scraper failed, {retries} tries left....")
            retries -= 1
            driver.quit()
        else:
            print('Organizing tables....')
            organize_tables()
        finally:
            print("Shutting down scraper...")
            driver.quit()
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-y', '--year', default=datetime.now().year)
    args = parser.parse_args()

    main(year=args.year)
