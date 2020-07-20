from selenium import webdriver

from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import pandas as pd
import time

def get_standings(url):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument("--window-size=1920, 1200")
    driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)

    driver.get(url+'results')
    delay = 10
    try:
        myElem = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CLASS_NAME, 'bfy-table')))
    except TimeoutException:
        print('timeout ')
    time.sleep(1)

    standings = driver.page_source
    soup = BeautifulSoup(standings, 'html.parser')
    standings_table = soup.findAll('table', class_="bfy-table")
    print(standings_table)
    df = pd.read_html(driver.find_elements_by_class_name("bfy-table")[0].get_attribute('outerHTML'))[0]
    df.drop('Unnamed: 1', axis=1, inplace=True)

    driver.quit()
    return df


