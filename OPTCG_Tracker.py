import telebot, time, random, requests, pandas as pd, numpy as np
from datetime import datetime as dt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from currency_converter import CurrencyConverter
from time import sleep

options = Options()
service = Service(executable_path="/usr/local/bin/geckodriver")  # -- Crontab requires geckodriver path

API_KEY = "<NOTION-API-KEY?"
DB_ID = "<NOTION-DB-ID>"
headers = {"Authorization" : "Bearer " + API_KEY, 
           "Content-Type" : "application/json", 
           "Notion-Version" : "2022-06-28"}



class Scraper():
    def __init__(self):
        self.START = time.time()
        self.bot = telebot.TeleBot('<TELEGRAMBOT-KEY>')
        self.cardInfo = {}   # -- PageID: {Name: , setName:}
        self.END = None
        self.cardList_Retriever()  # Automatically runs when Class Defined

    def botMessenger(self, STATUS):
        self.bot.send_message('', STATUS)  # Hardcoded to my chatID
        
    def hyperlink_formatter(self, string, setName):
        s = string.split(') ')
        temp = (s[1][:-3], s[1][-3:]) if s[1][-2] == 'V' else (s[1], '')  # Seperate out the V and CardName if applicable
        if (setName == 'The-Best') and (s[0][1:4] == 'DON'):
            return f"{s[0][1:]} {temp[0]}{temp[1]}".replace(' ', '-')        
        else:
            return f"{temp[0]} {s[0][1:]}{temp[1]}".replace(' ', '-')
        
    def cardList_Retriever(self):
        DB_filter = {"filter": {"property": "Type", "select": {"equals": "OP Cards"}}}
        res = requests.post(f'https://api.notion.com/v1/databases/{DB_ID}/query', headers=headers, json=DB_filter).json()   # -- Query NotionDB, filter to just return 'OP Cards'
        for row in res['results']:
            pageID = row['id']
            self.cardInfo[pageID] = {}
            self.cardInfo[pageID]['setName'] = row['properties']['ID']['rich_text'][0]['plain_text'] 
            self.cardInfo[pageID]['Name'] = self.hyperlink_formatter(row['properties']['Name']['title'][0]['plain_text'], self.cardInfo[pageID]['setName'])
        self.botMessenger('STARTING CARDMARKET SCRAPER')
    
    
    def cardList_Scraper(self):
fi        URL = 'https://www.cardmarket.com/en/OnePiece/Products/Singles/{}/{}'
        errorCount = 0
        
        for KEY, VALS in self.cardInfo.items():
            try:
                tempURL = URL.format(VALS['setName'], VALS['Name'])  # Format with cardName & setName
                driver.get(tempURL)
                sleep(random.uniform(0.5, 1))
                info = driver.find_elements(By.XPATH, '/html/body/main/div[3]/section[2]/div/div[2]/div[1]/div/div[1]/div/div[2]')
                sleep(random.uniform(0.5, 3))

                avg_30 = [i.text for i in info][0].split('\n')[17] # Retrieve 30-day average Euro Price
                avg_30 = float((avg_30[:-2]).replace(',','.'))  # Convert text to Float
                avg_30 = np.round(CurrencyConverter(decimal=False).convert(avg_30, 'EUR', 'GBP'), 2)  # Convert to GBP
                self.cardInfo[KEY]['Price'] = avg_30

            except Exception as e:
                self.cardInfo[KEY]['Price'] = np.nan
                errorCount += 1
        driver.quit()
        self.botMessenger(f'Prices scraped with {errorCount} errors')
        
        
    
    def notionIngestion(self):
        i, errorCount=0, 0  # Helps to optimise Insertion (~30 seconds)
        try:
            for KEY, VALS in self.cardInfo.items():
                data = {"properties": {"Price": {"number": VALS['Price']}}}
                if VALS['Price'] != np.nan:
                    if i == 3:
                        i=0
                        sleep(0.5)
                    requests.patch(f'https://api.notion.com/v1/pages/{KEY}', headers=headers, json=data)  # Given PageID write specific price
                    i+=1
                    print(VALS['Name'] + " price updated")
        except:
            errorCount += 1
        self.END = time.time()
        self.botMessenger(f'Notion Prices Updated with {errorCount} errors [Duration: {np.round(self.END-self.START, 2)}s]')







scraper = Scraper()
try:
    scraper.cardList_Scraper()
    scraper.notionIngestion()
except Exception as e:
    scraper.botMessenger(f'An Error has occurred ... {e}')

