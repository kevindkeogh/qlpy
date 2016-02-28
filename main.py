# standard library
import os, sys
import sqlite3
import QuantLib as ql

# qlpy stuff
import helpers.curve as curve
import helpers.db_handler as db_handler 


def main():
    # check connect to market data db and, if not, create it with dummy data
    if os.path.isfile('market_data.db'):
        conn = sqlite3.connect('market_data.db')
    else:
        conn = db_handler.create_db('market_data.db')

    # set selects to return dicts
    conn.row_factory = db_handler.dict_factory


    os.system('cls' if os.name == 'nt' else 'clear')
    # Sample use
    print('This sample will demonstrate how to build the USD 3M LIBOR curve')
    print('Enter the date you are trying to build the curve as of')
    day = int(input('Enter the day (##): '))
    month = int(input('Enter the month (##): '))
    year = int(input('Enter the year (####): '))    

    now_date = ql.Date(day, month, year)
    ql.Settings.instance().evaluationDate = now_date

    print('Building...')
    usd = curve.LiborCurve('USD_3M', now_date, conn)
    print('-'*70)
    print('The curve is now built')

    export = input('Export discount factors? (y/n) ')
    if export.lower() == 'y':
        usd.export()
        print('Curve has been exported to the outputs folder')
        print('-'*70)

    print_dfs = input('Print discount factors? (y/n) ')
    if print_dfs.lower() == 'y':
        for date in enumerate(usd.dates):
            print(date[1], usd.discount_factors[date[0]])
        print('-'*70)

    print_df = input('Print discount factor for specific date? (y/n) ')
    if print_df.lower() == 'y':
        day = int(input('Day? (##) '))
        month = int(input('Month? (##) '))
        year = int(input('Year? (##) '))
        random_date = ql.Date(day, month, year)
        df = usd.discount_factor(random_date)
        print(df)

if __name__ == '__main__':
    main()
