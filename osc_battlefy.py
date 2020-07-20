from selenium import webdriver

from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import pandas as pd
import time

def get_standings():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument("--window-size=1920, 1200")
    driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)

    url = 'https://battlefy.com/btw-esports/copa-doomhammer-15/5f0244805522b8665292fa31/stage/5f0b421326cc57765b462bf1/'

    driver.get(url+'results')
    delay = 15
    try:
        myElem = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CLASS_NAME, 'bfy-table')))
    except TimeoutException:
        print('timeout ')
    time.sleep(1)

    standings = driver.page_source
    soup = BeautifulSoup(standings, 'html.parser')
    standings_table = soup.findAll('table', class_="bfy-table")
    print(standings_table)
    dfs = pd.read_html(driver.find_elements_by_class_name("bfy-table")[0].get_attribute('outerHTML'))

    for df in dfs:
        print(df.head())

    driver.quit()
    return dfs[0].head()


