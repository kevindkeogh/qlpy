#!/usr/bin/env python3
'''
'''
import datetime
import dateutil.relativedelta
import dateutil.rrule as rrule
import numpy as np

class Schedule:
    '''
    Class to generate and hold interest rate swap accrual schedules. The class
    takes the effective and maturity dates, and a few optional parameters to
    enable exact schedule creation.
    Arguments:
        effective(datetime)     Effective date of schedule
        maturity(datetime)      Maturity of schedule
        backward(bool)          True/False to generate dates from end or start
                                [default:True][optional]
        second(datetime)        First date after effective date [optional]
        penultimate(datetime)   Last date before maturity date [optional]
        weeks(int)              Number of weeks for each reset [optional]
        months(int)             Number of months for each period [optional]

    Returns
        Schedule                Object that holds the accrual periods
                                2d numpy array (1st dimension is accrual
                                start dates, 2nd dimension is accrual end dates,
                                3rd dimension is payment dates, 4th dimension is
                                fixing dates)
    
    '''
    def __init__(self, effective, maturity, backward=True, second=None,
                 penultimate=None, weeks=None, months=None):
       self.effective = effective
       self.maturity = maturity
       self.backward = backward
       self.second = second
       self.penultimate = penultimate
       self.weeks = weeks
       self.months = months
       self._check_inputs()

       self.period_ends = self._gen_period_ends()

    def _check_inputs(self):
        '''
        Checking function for inputs to Schedule. Trys to catch common errors
        that will cause a failure to create a sensible schedule.
        '''
        if self.maturity == self.penultimate:
            raise Exception('Maturity and penultimate dates cannot be equal')
        if self.second == self.effective:
            raise Exception('Second and effective dates cannot be equal')
        if self.months is None and self.weeks is None:
            raise Exception('Must increment period by some amount of months or weeks')
        if self.months is not None and self.weeks is not None:
            raise Exception('Can\'t increment by both months and weeks')


    def _gen_period_ends(self):
        '''
        Generate the period end dates. Uses the dateutil module to generate
        a repeating rule to generate a list of dates.
        Returns:
            period_ends (np array)  Numpy 1d array of period end datetimes.
        '''
        if self.months is not None:
            period_type = rrule.MONTHLY
            period_length = self.months
        elif weeks is not None:
            period_type = rrule.WEEKLY
            period_length = self.weeks
        if self.second is not None:
            start = second
            period_ends = [effective]
        else:
            start = effective
            period_ends = []
        if self.backward:
            if self.penultimate is not None: # Backward from penultimate
                period_ends += list(rrule.rrule(period_type, 
                                                interval=period_length, 
                                                bymonthday=(self.penultimate.day, -1), #these 2
                                                bysetpos=1, #params allow for 31sts
                                                dtstart=start, 
                                                until=penultimate))[1:]
                if period_ends[-1] != penultimate:
                    raise Exception('Something happened, does the penultimate '
                                    'occur at the right interval?')
                period_ends = np.append(np.array(period_ends), np.array([maturity]))
                return period_ends
            else: # TODO: Backward from maturity
                pass
        else: # Forward from effective
            period_ends += list(rrule.rrule(period_type,
                                            interval=period_length,
                                            bymonthday=(self.effective.day, -1),
                                            bysetpos=1,
                                            dtstart=start,
                                            until=maturity))[1:]
            period_ends = np.array(period_ends)
            if period_ends[-1] != maturity:
               period_ends = np.append(period_ends, np.array([maturity]))
            return period_ends



if __name__ == '__main__':
    effective = datetime.datetime(2011, 11, 11)
    maturity = datetime.datetime(2012, 11, 11)
    penultimate = datetime.datetime(2012, 8, 11)
    sched = Schedule(effective, maturity, penultimate=penultimate, months=3)
    print(sched.period_ends)
