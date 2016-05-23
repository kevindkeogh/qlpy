#!/usr/bin/env python3
'''
'''
import datetime
import dateutil.relativedelta
import dateutil.rrule as rrule
import numpy as np

class Schedule:
    '''
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

       self.period_ends = self._gen_period_ends()

    def _gen_period_ends(self):
        '''
        Generate 
        '''
        if self.maturity == self.penultimate:
            raise Exception('Maturity and penultimate dates cannot be equal')
        if self.second == self.effective:
            raise Exception('Second and effective dates cannot be equal')
        if self.months is None and self.weeks is None:
            raise Exception('Must increment period by some amount of months or weeks')
        if self.months is not None and self.weeks is not None:
            raise Exception('Can\'t increment by both months and weeks')
        if self.months is not None:
            period_type = rrule.MONTHLY
            period_length = self.months
        elif weeks is not None:
            period_type = rrule.WEEKLY
            period_length = self.weeks
        if self.backward:
            if self.penultimate is not None:
                if self.second is not None:
                    start = second
                    period_ends = [effective]
                else:
                    start = effective
                    period_ends = []
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

effective = datetime.datetime(2011, 11, 11)
maturity = datetime.datetime(2012, 11, 11)
penultimate = datetime.datetime(2012, 8, 11)
sched = Schedule(effective, maturity, penultimate=penultimate, months=3)
print(sched.period_ends)
