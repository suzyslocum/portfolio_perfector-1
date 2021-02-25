import pandas as pd
import fire
import questionary
import csv
import json
import os
import numpy as np
import requests
import sqlalchemy as sql
import alpaca_trade_api as tradeapi
from MCForecastTools import MCSimulation
from dotenv import load_dotenv
from pathlib import Path
import datetime
from fastquant import backtest,get_stock_data


# load the environment variables
load_dotenv()

# info = []

print('Congratulations on taking the first step toward planning your retirement')
# get user's current age
current_age = questionary.text("How old are you?").ask()
# get user's desired income and store it as a variable
yearly_retirement_income = questionary.text("What's your desired yearly income in retirement").ask()
# get user's desired retirement age and store it as a variable
retirement_age = questionary.text('What age would you like to retire?').ask()
# get user's current retirement savings 
current_savings = questionary.text('How much money do you currently have saved for retirement that you want to invest?').ask()
# calculate how much money the user needs to retire
retirement_goal = (100 - float(retirement_age))*float(yearly_retirement_income) - float(current_savings)

# determining allocation percentage, formatted as [.bonds,.stocks,.cryptocurrency]
if int(current_age) <= 30:
    allocation_pct = [0.0,0.7,0.3]
elif 30 < int(current_age) <= 40:
    allocation_pct = [0.2,0.6,0.2]
elif 40 < int(current_age) <= 50:
    allocation_pct = [0.4,0.4,0.2]
elif 50 < int(current_age) <= 60: 
    allocation_pct = [0.5,0.4,0.1]
else:
    allocation_pct = [0.7,0.2,0.1]

allocation = questionary.confirm(f"""Your recommended portfolio allocation percentage is {allocation_pct} ([%bonds,%stocks,%cryptocurrency]). 
    Would you like to accept this allocation or pick your own portfolio allocation?""").ask()
if allocation:
    portfolio_allocation = allocation_pct
else:
    custom_bond = questionary.text('What percentage of your portfolio would you like to invest in bonds?').ask()
    custom_stock =  questionary.text('What percentage of your portfolio would you like to invest in stocks?').ask()
    custom_crypto = questionary.text('What percentage of your portfolio would you like to invest in cryptocurrency?').ask()
    #set the variable for custom allocation
    portfolio_allocation = [custom_bond,custom_stock,custom_crypto]


# store client info in a list THIS IS USED FOR PRETTY MUCH EVERYTHING GOING FORWARD
info = [int(current_age),int(yearly_retirement_income),int(retirement_age),int(current_savings),int(retirement_goal),portfolio_allocation]

header = ['current_age','yearly_retirement_income','retirement_age','current_savings','retirement_goal','portfolio_allocation']
output_path = Path("data/info.csv")
with open(output_path,'w',newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(header)
    csvwriter.writerow(info)


# Set response URLs
btc_url = "https://api.alternative.me/v2/ticker/Bitcoin/?convert=USD"

# Using the Python requests library, make an API call to access the current price of BTC
btc_response = requests.get(btc_url).json()

# Navigate the BTC response object to access the current price of BTC
btc_price = btc_response['data']['1']['quotes']['USD']['price']

alpaca_api_key = os.getenv('ALPACA_API_KEY')
alpaca_secret_key = os.getenv('ALPACA_SECRET_KEY')

# Create the Alpaca tradeapi.REST object
alpaca = tradeapi.REST(alpaca_api_key,alpaca_secret_key,api_version='v2') 

# Set the tickers to be used
tickers = ['AGG','QQQ']

# Set timeframe to 1D 
timeframe = '1D'

# Format current date as ISO format
# Set both the start and end date at the date of your prior weekday 
# This will give you the closing price of the previous trading day
start_date = pd.Timestamp('2016-02-19',tz='America/New_York').isoformat() # TODO update date
end_date = pd.Timestamp('2021-02-19',tz='America/New_York').isoformat() # TODO to update date

age = info['current_age']

info.loc[:,'portfolio_allocation'] = info.loc[:,'portfolio_allocation'].str.replace("'","")
portfolio_allocation = str(info['portfolio_allocation'])

# Calculate the % of the portfolio that will be allocated to bonds
if portfolio_allocation == '0    [0.0, 0.7, 0.3]' or '0    [0.2,0.6,0.2]' or '0    [0.4,0.4,0.2]' or '0    [0.5,0.4,0.1]' or '0    [0.7,0.2,0.1]':
    percent_bonds = portfolio_allocation[7:9]
else:
    percent_bonds = portfolio_allocation[6:8]

# Calculate the % of the portfolio that will be allocated to stocks 
if portfolio_allocation == '0    [0.0, 0.7, 0.3]' or '0    [0.2,0.6,0.2]' or '0    [0.4,0.4,0.2]' or '0    [0.5,0.4,0.1]' or '0    [0.7,0.2,0.1]':
    percent_stocks = portfolio_allocation[12:14]
else:
    percent_stocks = portfolio_allocation[10:12]

# Calculate the % of the portfolio that will be allocated to crypto
if portfolio_allocation == '0    [0.0, 0.7, 0.3]' or '0    [0.2,0.6,0.2]' or '0    [0.4,0.4,0.2]' or '0    [0.5,0.4,0.1]' or '0    [0.7,0.2,0.1]':
    percent_crypto = portfolio_allocation[17:19]
else:
    percent_crypto = portfolio_allocation[14:16]

stock_amt = float(percent_stocks)*info['current_savings']

btc_amt = float(percent_crypto)*(info['current_savings'])

bond_amt = float(percent_bonds)*(info['current_savings'])


if float(stock_amt) > 0:
    stock_weight = (float(stock_amt)+float(bond_amt))/float(stock_amt)
else:
    stock_weight = 0

if float(bond_amt) > 0:
    bond_weight = (float(bond_amt)+float(stock_amt))/float(bond_amt)
else:
    bond_weight = 0

portfolio_weights = [bond_weight,stock_weight]

MC_sim = (MCSimulation(portfolio_data=prices_df,weights=portfolio_weights,num_simulation=100,num_trading_days=252*30))

MC_sim.calc_cumulative_return()

cumulative_returns = MC_sim.summarize_cumulative_return()

mean_return = cumulative_returns['mean']

std_dev = cumulative_returns['std']

qqq_close = prices_df['QQQ']['close']

stock_daily_returns = qqq_close.pct_change().dropna()

stock_cumulative_returns = (1 + stock_daily_returns).cumprod()

stock_std_dev = stock_cumulative_returns.std()

annualized_stock_std_dev = stock_std_dev * np.sqrt(252)

avg_annual_stock_returns = stock_daily_returns.mean()*252

stock_sharpe_ratio = avg_annual_stock_returns/annualized_stock_std_dev

agg_close = prices_df['AGG']['close']

bond_daily_returns = agg_close.pct_change().dropna()

bond_cumulative_returns = (1 + bond_daily_returns).cumprod()

bond_std_dev = bond_cumulative_returns.std()

annualized_bond_std_dev = bond_std_dev * np.sqrt(252)

avg_annual_bond_returns = bond_daily_returns.mean()*252

bond_sharpe_ratio = avg_annual_bond_returns/annualized_bond_std_dev

portfolio_sharpe_ratio = (stock_weight*stock_sharpe_ratio)+(bond_weight*bond_sharpe_ratio)

btc_owned = btc_price/btc_amt






# database_connection_string = 'sqlite:///'

# engine = sql.create_engine(database_connection_string)

# engine.table_names()

# user_data_df = pd.DataFrame([current_age,yearly_retirement_income,retirement_age,current_savings,retirement_goal,portfolio_allocation])
# user_data_df.to_sql('info',engine)