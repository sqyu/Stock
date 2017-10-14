# -*- coding: utf-8 -*-

from __future__ import print_function
from bs4 import BeautifulSoup
import copy
import datetime
import earnings #
import locale
import numpy as np
import operator
import progressbar as pb
import pytz
import subprocess
import urllib
locale.setlocale(locale.LC_ALL, 'en_US')
statement_file = "statement"

def item_to_number(string):
    string = string.replace(",", "")
    if string == "N/A" or string == "$N/A": # Unknown
        return np.nan
    elif string.startswith("$"):            # Price
        return float(string.lstrip("$"))
    else:                                   # Quantity
        if "M" in string:                   # Larger than a million
            return int(float(string.rstrip("M")) * 1e6)
        else:
            return int(string)

def number_to_item(number, quantity = False):
    if np.isnan(number):
        return "N/A"
    elif quantity:
        if number >= 1e6:
            return locale.format("%.2f", number / 1e6, grouping = True) + "M"
        else:
            return locale.format("%d", number, grouping = True)
    else:
        return "$" + locale.format("%.2f", number, grouping = True)

def enter_int(prompt, wrong_prompt = "正整数を入力してください。\n"):    # Quantity
    input = raw_input(prompt).replace(",", "")
    while True:
        if input.upper() in ["N/A", "$N/A", "NA", "$NA"]:
            return np.nan
        try:
            input = int(input)
            if input < 0:
                input = raw_input(wrong_prompt)
                continue
            break
        except:
            if input != "" and input[-1] == "M":        # Larger than a million
                try:
                    input = int(float(input[:-1]) * 1e6)
                    break
                except:
                    input = raw_input(wrong_prompt)
            else:
                input = raw_input(wrong_prompt)
    return input

def enter_pos(prompt, wrong_prompt = "正数を入力してください。\n"):
    input = raw_input(prompt).replace(",", "")
    while True:
        if input.upper() in ["N/A", "$N/A", "NA", "$NA"]: # Unknown
            return np.nan
        try:
            input = float(input)
            if input < 0:
                input = raw_input(wrong_prompt)
                continue
            break
        except:
            input = raw_input(wrong_prompt)
    return input

def enter_num(prompt, wrong_prompt = "数字を入力してください。\n", nosign = False):
    # nosign: Return if there is no sign in the front of the input, used to indicate if the number is the change from CL to AH or it is CL
    input = raw_input(prompt).replace(",", "")
    if nosign and (input[0] == "+" or input[0] == "-"):
        nosign = False
    while True:
        if input.upper() in ["N/A", "$N/A", "NA", "$NA"]:
            return np.nan
        try:
            input = float(input)
            break
        except:
            input = raw_input(wrong_prompt)
    if nosign:
        return input, nosign
    else:
        return input


def format_gain(money):
    if money > -1e-3:
        return "+$" + "%.2f" % money
    else:
        return "-$" + "%.2f" % -money

def enter_date():
    date = raw_input("日付を(M)M/(D)D/YYのフォーマットで入力してください。\n今日または最終取引日の場合はTODAYを入力してください。\n")
    while True:
        if date.upper() == "TODAY":
            return "TODAY"
        try:
            date = datetime.datetime.strptime(date, '%m/%d/%y') # Test if a date
            return date.strftime("%m/%d/%Y") # Cast from 12/18/16 to 12/18/2016
        except ValueError:
            try:
                date = datetime.datetime.strptime(date, '%m/%d/%Y')
                return date.strftime("%m/%d/%Y")
            except ValueError:
                date = raw_input("フォーマットが正しくありません。(M)M/(D)D/YYで入力してください。\n")

def read_from_nasdaq(date, name):
    r = urllib.urlopen('http://www.nasdaq.com/symbol/' + name + '/historical').read()
    tables = BeautifulSoup(r).findAll("table")
    part = [s for s in tables if date in s.prettify()]
    if len(part) != 1:
        print("Something is wrong in extracting the part of table for " + name + ".\n")
        return []
    row = [s for s in part[0].find('tbody').find_all('tr') if date in s.prettify()]
    if len(row) != 1:
        print("Something is wrong in extracting the row of table for " + date.replace("16:00", "today") + ".\n")
        return []
    cols = row[0].find_all('td')
    cols = [ele.text.strip() for ele in cols]
    return cols

def search_from_table(part, keyword, price = True): # Helper function for last_txn_date and read_today(). part = uncleaned part of table containing the amount in search. If price = T then look for $, otherwise pick the last element (correctness not assured).
    if price:
        return [ele.text.strip() for ele in [s for s in part.find('tbody').find_all('tr') if keyword in s.prettify()][0].find_all('td') if "$" in ele.text][0]
    else:
        return [s for s in part.find('tbody').find_all('tr') if keyword in s.prettify()][0].find_all('td')[-1].text

def last_txn_date(name):
    r = urllib.urlopen('http://www.nasdaq.com/symbol/' + name).read()
    tables = BeautifulSoup(r).findAll("table")
    part = [s for s in tables if "Date of Open Price" in s.prettify() and "Date of Close Price" in s.prettify()][0]
    today_date = search_from_table(part, "Date of Open Price", False)
    if today_date != search_from_table(part, "Date of Close Price", False):
        print("NASDAQ Date of Open Price and Date of Close Price for " + name + " do not match.\n")
        assert False
    return datetime.datetime.strptime(today_date, "%b. %d, %Y").strftime("%m/%d/%Y"), r # r returned and is reused (if applicable) so that we would not need to access the page again

def read_today_from_nasdaq(date_last_txn, name): # USE THIS!! To obtain numbers for today or last market day ONLY AFTER AFTER-HOURS TRADING ENDS AT 8PM (after today's data is shown as "16:00" in "historical")
    date_now_in_NYC = datetime.datetime.now(tz=pytz.timezone('US/Eastern')).strftime("%m/%d/%Y")
    if date_now_in_NYC == date_last_txn: # If the last txn date is today in NYC, the data are listed as "16:00" in NASDAQ
        cols = read_from_nasdaq("16:00", name)
    else:
        cols = read_from_nasdaq(date_last_txn, name)
    cols[0] = date_last_txn
    return cols

#def read_today_from_nasdaq_before_after_hours_ends(name): # DO NOT USE!! To obtain numbers for today ONLY BEFORE AFTER-HOURS TRADING ENDS at 8PM (when today's data is not shown in "historical"). # THIS WORKS FOR STOCKS LISTED IN NASDAQ ONLY!!
#    try:
#        today_date, r = last_txn_date(name)
#        tables = BeautifulSoup(r).findAll("table")
#        part = [s for s in tables if "Today's High /Low" in s.prettify() and "Share Volume" in s.prettify() and "NASDAQ Official Open Price" in s.prettify() and "NASDAQ Official Close Price" in s.prettify()][0]
#        hl = map(float, search_from_table(part, "Today's High /Low").replace("$", "").replace(u"\xa0", "").split("/"))
#        op = float(search_from_table(part, "NASDAQ Official Open Price").replace("$", "").replace(u"\xa0", ""))
#        cl = float(search_from_table(part, "NASDAQ Official Close Price").replace("$", "").replace(u"\xa0", ""))
#        v = search_from_table(part, "Share Volume", False).lstrip().rstrip()
#    except:
#        print("Error occurred while extracting today's data for " + name)
#    return [today_date] + map(str, [op] + hl + [cl, v])


#prev_day = ""
#print("前日のデータを入力してください。\n")
#while True:
#    new_line = raw_input()
#    if not new_line:
#        break
#    prev_day += new_line + "\n"
prev_day = "".join(open(statement_file, "r+").readlines()).split("\n\n")[-1]
print("前日のデータは次のとおりです。\n")
print(prev_day + "\n")

# date = pytz.timezone("Japan").localize(datetime.datetime.now()).astimezone(pytz.timezone("US/Eastern"))
# date = date.strftime("%m").lstrip("0") + "/" + date.strftime("%d").lstrip("0")
date = enter_date()
prev_stocks = prev_day.split("HOLD")[1].split("BUY")[0].lstrip("_").rstrip("_").lstrip().rstrip().split("\n") #HOLD from previous day
prev_names = [line.split(" ")[0] for line in prev_stocks]
prev_quantities = [int(line.split(" ")[1]) for line in prev_stocks]
prev_details = [{item.split(": ")[0]: item_to_number(item.split(": ")[1]) for item in line.split("(")[1].split(")")[0].split(", ")} for line in prev_stocks]
prev_buys = prev_day.split("BUY")[1].split("SELL")[0].lstrip("_").rstrip("_").lstrip().rstrip() # String
prev_sells = prev_day.split("SELL")[1].split("COMMENTS")[0].lstrip("_").rstrip("_").lstrip().rstrip()
if prev_buys: # Need to add BUY from previous day (later, after adjustments for day trades)
    prev_buys = [(line.split(" ")[0], item_to_number(line.split(" ")[1]), item_to_number(line.split(" ")[3]), line.split("(")[1].split(")")[0]) for line in prev_buys.split("\n")]
    prev_buy_names = [item[0] for item in prev_buys]
    if prev_sells:
        for line in prev_sells.split("\n"):
            prev_sell_name, prev_sell_quant = line.split(" ")[0:2]
            if prev_sell_name in prev_buy_names: # If day trade on previous day
                tuple = prev_buys[prev_buy_names.index(prev_sell_name)]
                prev_buys[prev_buy_names.index(prev_sell_name)] = (tuple[0], tuple[1] - item_to_number(prev_sell_quant), tuple[2], tuple[3]) # Subtract quantity bought
                if prev_buys[prev_buy_names.index(prev_sell_name)][1] < 0: # If for a day traded stock more stocks were sold than bought, then equivalent to pure selling, not buying, AND "HOLD" INDICATES THE EXACT AMT AFTER CLOSING; WHILE if not more than bought, the exact amt after closing is hold + buy - sell.
                    prev_buys.pop(prev_buy_names.index(prev_sell_name))
                    prev_buy_names.remove(prev_sell_name)
    del prev_buy_names, prev_sells
    for buy in prev_buys:
        if buy[0] in prev_names:
            prev_quantities[prev_names.index(buy[0])] += buy[1]
        else:
            prev_names.append(buy[0])
            prev_quantities.append(buy[1])
            prev_details.append({item.split(": ")[0]: item_to_number(item.split(": ")[1]) for item in buy[3].split(", ")})
else:
    prev_buys = []


new_investment = 0 #enter_pos("今日はご入金がありますか？無い場合は0を入力してください。\n")
if raw_input("時間外取引のデータがない場合はここでNAを入力してください。\n").upper() in ["NA", "N/A"]:
    no_AH_data = True
else:
    no_AH_data = False

print("現在お持ちの株は次の通りです。\n" + "\n".join([item[0] + " " + str(item[1]) + "株" for item in zip(prev_names, prev_quantities)]))


new_names = copy.deepcopy(prev_names)
new_quantities = copy.deepcopy(prev_quantities)

if True:
    print("\n本日購入した株の銘柄を入力してください。\n") # Enter buys first to allow day trades (buy new and sell)
    buys = []
    new_name = raw_input("銘柄を入力してください。\n").upper()
    while True:
        if new_name:
            new_quant = enter_int("買った" + new_name + "の株数を入力してください。\n", "株数を正整数で入力してください。\n")
            if new_quant == 0:
                new_name = raw_input("０株を無視しました。\n引き続き銘柄を入力してください。\n").upper()
                continue
            new_price = enter_pos("買った" + new_name + "の価格を入力してください。\n", "株価を正数で入力してください。\n")
            buys.append((new_name, new_quant, new_price)) # (AMZN, 1, 800)
            if new_name in new_names:
                new_quantities[new_names.index(new_name)] += new_quant
            else:
                new_names.append(new_name)
                new_quantities.append(new_quant)
        else:
            break
        new_name = raw_input("\n引き続き銘柄を入力してください。\n").upper()
    buy_names = [item[0] for item in buys]
    print("\n購入:\n" + "\n".join([buy[0] + " " + number_to_item(buy[1], True) + "株" + " " + number_to_item(buy[2]) + "ドル" for buy in buys]))
    print("\n\n本日売出した株の銘柄を入力してください。\n")
    solds = []
    new_name = raw_input("銘柄を入力してください。\n").upper()
    while True:
        if new_name:
            if not new_name in new_names:
                print(new_name + "はお持ちしておりません。正しい銘柄を入力してください。\n")
            else:
                new_quant = enter_int("売った" + new_name + "の株数を入力してください。\n", "株数を正整数で入力してください。\n")
                if new_quant == 0:
                    new_name = raw_input("０株を無視しました。\n引き続き銘柄を入力してください。\n").upper()
                    break
                if new_quant > new_quantities[new_names.index(new_name)]:
                    print("現在お持ちの" + new_name + "は" + number_to_item(new_quantities[new_names.index(new_name)], True) + "株です。正しい株数を入力してください。\n")
                else:
                    new_price = enter_pos("売った" + new_name + "の価格を入力してください。\n", "株価を正数で入力してください。\n")
                    solds.append((new_name, new_quant, new_price)) # (AMZN, 1, 900)
                    new_quantities[new_names.index(new_name)] -= new_quant
        else:
            break
        new_name = raw_input("\n引き続き銘柄を入力してください。\n").upper()
    sell_names = [item[0] for item in solds]
    print("\n\n売出:\n" + "\n".join([sold[0] + " " + number_to_item(sold[1], True) + "株" + " " + number_to_item(sold[2]) + "ドル" for sold in solds]))
    day_trade_names = set(buy_names) & set(sell_names)
    if day_trade_names:
        print("\n\n日計り取引：" + " ".join(day_trade_names) + "\n")

hold_names = copy.deepcopy(prev_names) # for printing purpose: "HOLD"
hold_quantities = copy.deepcopy(prev_quantities)
for sell in solds:
    if sell[0] in day_trade_names and sell[0] in prev_names: # If day trade but not previously held, hold = 0
        hold_quantities[hold_names.index(sell[0])] -= np.max(0, sell[1] - buys[buy_names.index(sell[0])][1])    # If in a day trade more shares are sold than bought, hold = prev close + buy - sell; otherwise, hold = prev close. ##### BUG WHEN ALL SOLD!!!
    elif not sell[0] in day_trade_names: # If not day trade
        hold_quantities[hold_names.index(sell[0])] -= sell[1]
hold_names = [hold_names[i] for i in range(len(hold_quantities)) if hold_quantities[i] > 0] # Remove stocks with zero shares
hold_quantities = [q for q in hold_quantities if q > 0]
assert(len(hold_names) == len(hold_quantities))

lists_of_values = {}
print("NASDAQからデータ読み込み中…")
widgets = [pb.AnimatedMarker(), " ", pb.Timer(), "  ", pb.Percentage(), pb.Bar(), " ", pb.ETA()]
pbar = pb.ProgressBar(maxval = len(new_names), widgets = widgets).start()
if date != "TODAY":
    for i, name in enumerate(new_names):
        pbar.update(i + 1)
        lists_of_values[name] = read_from_nasdaq(date, name.lower())
else:
    date = last_txn_date("AMZN")[0] # Get today's date
    print("今日の日付は" + date + "です。\n")
    for i, name in enumerate(new_names):
        pbar.update(i + 1)
        lists_of_values[name] = read_today_from_nasdaq(date, name.lower())
        #lists_of_values[name] = read_today_from_nasdaq_before_after_hours_ends(name)
        #date = lists_of_values[name][0]
pbar.finish()
print("\n")

new_details = []
new_lines = {}
for name, quantity in zip(new_names, new_quantities): # new_names still contains stocks that are completely sold (quantity = 0) because we need its information for that day
    detail = {}
    values = lists_of_values[name]
    if (not no_AH_data) or (values == []):
        print("\n" + name + "のデータを入力してください。\n")
    if no_AH_data:
        detail["AH"] = np.nan
    else:
        detail["AH"] = enter_pos("After-hours price　時間外取引価格:\n")
    if values == []: ## If not able to read the table from NASDAQ
        if np.isnan(detail["AH"]):
            detail["Cl"] = enter_pos("Closing price 終値:\n") ####
        else:
            change_ah = enter_num("Change from closing to after-hours price　時間外取引価格マイナス終値（±つき）または終値（±なし）:\n", nosign = True)
            if type(change_ah) != type(0.0) and len(change_ah) == 2: # nosign = T, so there is no sign in the input, so it is the absolute closing price. Now force it to become the change from Cl to AH.
                if change_ah[0] != 0: # If no sign but the input is 0, then I meant to type +0 since the closing price cannot be 0. Ignore if that's the case.
                    change_ah = detail["AH"] - change_ah[0]
                else:
                    change_ah = 0.0 # Have to have this step otherwise change_ah = (0.0, T), not a float
            while change_ah > detail["AH"]:
                change_ah = enter_num("終値が負数になりました。もう一度時間外取引の価格の変化を入力してください。\n")
            detail["Cl"] = detail["AH"] - change_ah ####
        detail["Op"] = enter_pos("Opening price　始値:\n")
        detail["Hi"] = enter_pos("High　高値:\n")
        if detail["Hi"] < detail["Cl"] or detail["Hi"] < detail["Op"]:
            detail["Hi"] = enter_pos("入力した高値は始値や終値より低いです。やり直してください。警告を無視するには高値をもう一度入力してください。\n")
        detail["Lo"] = enter_pos("Lo　安値:\n")
        if detail["Lo"] > detail["Cl"] or detail["Lo"] > detail["Op"]:
            detail["Lo"] = enter_pos("入力した安値は始値や終値より高いです。やり直してください。警告を無視するには安値をもう一度入力してください。\n")
        detail["V"] = enter_int("Volume　出来高:\n")
    else: # If able to read from NASDAQ
        detail["Op"] = float(values[1])
        detail["Hi"] = float(values[2])
        detail["Lo"] = float(values[3])
        detail["Cl"] = float(values[4])
        detail["V"] = int(values[5].replace(",", ""))
    line = name + " QUANTITY *PRICE(Op: " + number_to_item(detail["Op"]) + ", Cl: " + number_to_item(detail["Cl"]) + ", AH: " + number_to_item(detail["AH"]) + ", Hi: " + number_to_item(detail["Hi"]) + ", Lo: " + number_to_item(detail["Lo"]) + ", V: " + number_to_item(detail["V"], True) + ")"
    if name in day_trade_names:
        line += " (Day Trade)"
    if (not no_AH_data) or (values == []): # If had to input data, print a preview
        print(line.replace("QUANTITY", number_to_item(quantity, True)).replace("PRICE", " "))
    new_details.append(detail)
    new_lines[name] = line + "\n"

prev_closing_total = item_to_number([line for line in prev_day.split("\n") if line.startswith("Closing:")][0].split(" ")[1])
prev_close_prices = [item["Cl"] for item in prev_details]
prev_estimated_cash = prev_closing_total - sum([q*p for (q,p) in zip(prev_quantities, prev_close_prices)])

new_close_prices = [item["Cl"] for item in new_details]
new_proceeds_from_sells = sum([sold[1] * sold[2] for sold in solds])
new_cost_for_buys = sum([buy[1] * buy[2] for buy in buys])
new_close_prices = [item["Cl"] for item in new_details]
new_ah_prices = [item["AH"] for item in new_details]
new_estimated_cash = prev_estimated_cash + new_proceeds_from_sells - new_cost_for_buys
new_estimated_closing_total = new_estimated_cash + sum([q*p for (q,p) in zip(new_quantities, new_close_prices)])
new_estimated_closing_gain = new_estimated_closing_total - prev_closing_total
if not np.nan in new_ah_prices:
    new_estimated_ah_total = new_estimated_cash + sum([q*p for (q,p) in zip(new_quantities, new_ah_prices)])
    new_estimated_ah_gain = new_estimated_ah_total - new_estimated_closing_total


if True:
    date = datetime.datetime.strptime(date, '%m/%d/%Y')
    date = date.strftime("%m").lstrip("0") + "/" + date.strftime("%d").lstrip("0") + "/" + date.strftime("%Y")
    printouts = "\n\n" + date + "\nNew Investment: $"
    if abs(new_investment) < 1e-3:
        printouts += "0"
    else:
        printouts += "%.2f" % new_investment
    printouts += "\n__________HOLD__________\n"
    printouts += "".join([new_lines[n].replace("QUANTITY", number_to_item(q, True)).replace("PRICE", " ") for n,q in zip(hold_names, hold_quantities)])
    printouts += "__________BUY__________\n"
    printouts += "".join([new_lines[buy[0]].replace("QUANTITY", number_to_item(buy[1], True)).replace("PRICE", " " + number_to_item(buy[2]) + " ") for buy in buys])
    printouts += "__________SELL__________\n"
    printouts += "".join([new_lines[sold[0]].replace("QUANTITY", number_to_item(sold[1], True)).replace("PRICE", " " + number_to_item(sold[2]) + " ") for sold in solds])
    printouts += "_________COMMENTS__________\n______________________________\n"
    #if prev_estimated_cash < 0:
    #   print("Closing: $\nNet Gain: +$\nAH: $ (+$)\n")
    #   print("BAD ESTIMATION") # Disabled after introduction of robinhood good
    #else:
    printouts += "Closing: $%.2f\n" % new_estimated_closing_total
    printouts += "Net Gain: " + format_gain(new_estimated_closing_gain) + "\n"
    if not np.nan in new_ah_prices:
        printouts += "AH: $%.2f" % new_estimated_ah_total + " (" + format_gain(new_estimated_ah_gain) + ")"
    else:
        printouts += "AH: $ (+$)"
    print(printouts)
    open(statement_file, "a").write(printouts)
    if raw_input("To see earnings alerts, enter Y.\n").upper() in ["Y", "YES"]:
        print("Earnings Alerts:\n")
        stocks_of_interest = set(hold_names + [buy[0] for buy in buys] + [sold[0] for sold in solds])
        dates = {}
        no_dates = []
        pbar = pb.ProgressBar(maxval = len(stocks_of_interest), widgets = widgets).start()
        for i, name in enumerate(stocks_of_interest):
            try:
                dates[name] = earnings.extract_date_and_time(earnings.search_earning(name))
            except:
                no_dates.append(name)
            pbar.update(i+1)
        pbar.finish()
        sorted_names_and_dates = sorted(sorted(dates.items(), key=operator.itemgetter(0)), key=lambda x:datetime.datetime.strptime(x[1].split(" ")[0], "%m/%d/%Y").strftime("%Y%m%d")) # sort by name first and then by date
        for item in sorted_names_and_dates:
            print(item[0] + ": " + item[1])
        print("\nUnable to obtain earnings dates for " + ", ".join(no_dates) + ".\n")
    subprocess.Popen("open " + statement_file, shell=True)


