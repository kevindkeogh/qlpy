from scipy.optimize import brentq
from scipy.optimize import brent
import scipy.interpolate
import numpy as np
import datetime
import time
import dateutil.relativedelta

def get_df(curve, dates):
    return scipy.interpolate.splev(dates, curve)

def func(new_df, arg_dict):
    curve_dates = np.append(arg_dict['dates'], arg_dict['maturity'])
    curve_dfs = np.append(arg_dict['dfs'], np.array([new_df]))
    interp = scipy.interpolate.splrep(curve_dates, curve_dfs)
    fixed_dfs = get_df(interp, arg_dict['fixed_dates'])
    fixed_leg = sum(get_df(interp, arg_dict['fixed_dates']) * arg_dict['fixed_payments'])
    float_leg = 0
    for i in range(len(arg_dict['float_dates'])):
        period_end = datetime.datetime.fromtimestamp(arg_dict['float_dates'][i]) + datetime.timedelta(days=90)
        df = get_df(interp, arg_dict['float_dates'][i]) / get_df(interp, period_end.timestamp()) 
        first_df = get_df(interp, arg_dict['float_dates'][i])
        second_df = get_df(interp, period_end.timestamp())
        rate = ((df-1) / (90/360))
        print('rate: {rate}'.format(**locals()))
        float_leg += rate * 1000 * get_df(interp, period_end.timestamp()) * 90/360
    print('fixed leg: {fixed_leg}, float leg: {float_leg}, df: {df}'.format(**locals()))
    swap_value = fixed_leg - float_leg
    
    return abs(swap_value) 

new_dict = {}
new_dict['maturity'] = np.array([datetime.datetime(2012, 11, 11).timestamp()])
new_dict['fixed_payments'] = np.array([2.9, 2.9])
new_dict['fixed_dates'] = np.array([datetime.datetime(2012, 5, 11).timestamp(), 
                                    datetime.datetime(2012, 11, 11).timestamp()])
new_dict['float_dates'] = np.array([datetime.datetime(2011, 11, 11).timestamp(), 
                                    datetime.datetime(2012, 2, 11).timestamp(), 
                                    datetime.datetime(2012, 5, 11).timestamp(), 
                                    datetime.datetime(2012, 8, 11).timestamp()])
new_dict['dates'] = np.array([datetime.datetime(2011, 11, 11).timestamp(), 
                              datetime.datetime(2011, 11, 28).timestamp(), 
                              datetime.datetime(2011, 12, 14).timestamp()])
new_dict['dfs'] = np.array([1, 0.99990306, 0.99977688])

xmin = brent(func, brack=(0, 1.5), args=(new_dict,))
new_dict['dates'] = np.append(new_dict['dates'], new_dict['maturity'])
new_dict['dfs'] = np.append(new_dict['dfs'], np.array([xmin]))

new_dict['maturity'] = np.array([datetime.datetime(2013, 11, 11).timestamp()])
new_dict['fixed_payments'] = np.array([3.0, 3.0, 3.0, 3.0])
new_dict['fixed_dates'] = np.append(new_dict['fixed_dates'], np.array([datetime.datetime(2013, 5, 11).timestamp(), 
                                                                       datetime.datetime(2013, 11, 11).timestamp()]))
new_dict['float_dates'] = np.append(new_dict['float_dates'], np.array([datetime.datetime(2012, 11, 11).timestamp(), 
                                                                       datetime.datetime(2013, 2, 11).timestamp(), 
                                                                       datetime.datetime(2013, 5, 11).timestamp(), 
                                                                       datetime.datetime(2013, 8, 11).timestamp()]))
xmin = brent(func, brack=(0, 1.5), args=(new_dict,))

# proper use
maturity = datetime.datetime(2012, 11, 11)
effective = datetime.datetime(2011, 11, 11)
period_ends = _gen_dates_list_backward(effective, maturity, months=3)
print(period_ends)
print(len(period_ends))
