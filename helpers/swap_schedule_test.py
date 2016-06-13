from swap_schedule import Schedule
import datetime

effective = datetime.datetime(2015, 12, 31)
maturity = datetime.datetime(2055, 12, 31)
simple = Schedule(effective, maturity, 3)

second = datetime.datetime(2016, 1, 31)
penultimate = datetime.datetime(2055, 10, 31)

adjusted = Schedule(effective, maturity, 3,
                    second=second,
                    penultimate=penultimate,
                    fixing_lag=0,
                    period_adjustment='following',
                    payment_adjustment='modified following')
