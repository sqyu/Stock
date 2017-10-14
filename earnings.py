# -*- coding: utf-8 -*-

from __future__ import print_function
from bs4 import BeautifulSoup
import copy
import datetime
import locale
import numpy as np
import progressbar as pb
import pytz
import urllib
locale.setlocale(locale.LC_ALL, 'en_US')


def search_earning(name):
    url = "http://www.nasdaq.com/earnings/report/" + name
    r = urllib.urlopen(url).read()
    return BeautifulSoup(r)

def extract_content(soup):
    return soup.find_all('span', attrs={'id':'two_column_main_content_reportdata'})[0].text

def extract_date_and_time(soup):
    return extract_content(soup).split("earnings on")[1].split(".")[0].lstrip().rstrip()

def print_table(table):
    col_width = [max(len(x) for x in col) for col in zip(*table)]
    for line in table:
        print ("| " + " | ".join("{:{}}".format(x, col_width[i]) for i, x in enumerate(line)) + " |")

def extract_history(soup):
    tables = soup.find_all("table")
    data = [t for t in tables if "DateReported" in t.text][0]
    rows = data.find_all("tr")
    if len(rows) != 5:
        print("The number of rows in the data table is not 5. Please check.\n\n")
        print(rows)
        assert False
    header = [t.prettify().replace("\n <br/>\n ", " ").replace("<th>","").replace("</th>","").lstrip().rstrip() for t in rows[0].find_all("th")]
    rows = [[t.text for t in r.find_all("td")] for r in rows[1:]] # data stored here
    print_table([header] + rows)
    return header, rows

def market_cap(string):
    if string.upper() == "N/A":
        return 0.0
    elif string.endswith("M"):
        return float(string[:-1]) * 1e6
    elif string.endswith("B"):
        return float(string[:-1]) * 1e9
    else:
        return float(string)

def print_earnings_for_day(date):
    try:
        date = datetime.datetime.strptime(date, "%m/%d/%Y").strftime("%Y-%b-%d")
    except:
        date = datetime.datetime.strptime(date, "%m/%d/%y").strftime("%Y-%b-%d")
    url = "http://www.nasdaq.com/earnings/earnings-calendar.aspx?date=" + date
    r = urllib.urlopen(url).read()
    soup = BeautifulSoup(r)
    tables = soup.find_all("table")
    table = [t for t in tables if "Company Name" in t.prettify()][0]
    rows = [row.find_all("a") for row in table.find_all("tr")]
    names_cap_time = []
    for row in rows[1:]:
        if len(row) == 2: # If it has time (pre-market or after-hours)
            names_cap_time.append((row[1].text.split("Market Cap")[0].lstrip().rstrip(), row[1].find_all("b")[0].text.split("$")[1], -1*("premarket" in str(row[0])) + 1*("after-hours" in str(row[0])))) # Name, market cap, pre-market (-1) or after-hours (+1)
        else:
            names_cap_time.append((row[0].text.split("Market Cap")[0].lstrip().rstrip(), row[0].find_all("b")[0].text.split("$")[1], 0))
    sorted_names_and_time = sorted(names_cap_time, key=lambda x:market_cap(x[1]), reverse = True) # Sort by Market cap
    pre_market_table = [[i[0],i[1]] for i in sorted_names_and_time if i[2] == -1]
    if pre_market_table:
        print("Pre-market:\n")
        print_table(pre_market_table)
        #f = '{:<' + str(max([len(i[0]) for i in sorted_names_and_time]) + 2) + "}{:<5}"
        #print("\n".join([f.format(i[0], i[1]) for i in sorted_names_and_time if i[2] == -1]))
    after_hours_table = [[i[0],i[1]] for i in sorted_names_and_time if i[2] == 1]
    if after_hours_table:
        print("\nAfter-hours:\n")
        print_table(after_hours_table)
    time_unknown_table = [[i[0],i[1]] for i in sorted_names_and_time if i[2] == 0]
    if time_unknown_table:
        print("\nTime unknown:\n")
        print_table(time_unknown_table)

if __name__ == "__main__":
    print("Welcome.")
    while True:
        input = raw_input("\nEnter 1 to find the date for a specific stock,\n2 to read the content about the upcoming earnings report for that stock,\n3 to see the historical data for that stock,\n4 to see all for that stock,\nor 5 to search for a specific date.\nEnter 0 to quit.\n")
        try:
            if input == "0" or input.upper() == "QUIT":
                print("See you!\n")
                quit()
            elif input == "1":
                print("\n" + extract_date_and_time(search_earning(raw_input("Please enter the ticker symbol.\n").lower())))
            elif input == "2":
                print("\n" + extract_content(search_earning(raw_input("Please enter the ticker symbol.\n").lower())))
            elif input == "3":
                extract_history(search_earning(raw_input("Please enter the ticker symbol.\n").lower()))
            elif input == "4":
                soup = search_earning(raw_input("Please enter the ticker symbol.\n").lower())
                print("\n" + extract_content(soup) + "\n")
                extract_history(soup)
            elif input == "5":
                print_earnings_for_day(raw_input("Please enter the date mm/dd/(YY)YY.\n"))
            else:
                print("Invalid input.\n")
        except Exception:
            print("\nUnable to extract information.\n")


#from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

#driver = webdriver.Chrome('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
#binary = FirefoxBinary(r'/Applications/Firefox 2.app/Contents/MacOS/firefox-bin')
#driver = webdriver.Firefox(firefox_binary=binary)


#from bs4 import BeautifulSoup
#import requests
#url = 'http://www.nasdaq.com/symbol/amzn/historical'

#session = requests.Session()
#session.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36'}
#response = session.get(url)
#soup = BeautifulSoup(response.content)

#data = {'ddlTimeFrame': '18m', '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'}).get('value', ''), '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'}).get('value', ''),  '__VIEWSTATEENCRYPTED': soup.find('input', {'name': '__VIEWSTATEENCRYPTED'}).get('value', ''), '__EVENTVALIDATION': soup.find('input', {'name': '__EVENTVALIDATION'}).get('value', ''), 'themepreference': "blackg", 'quotepreference': "realtime"}

#response = session.post(url, data=data)
#soup = BeautifulSoup(response.content)
