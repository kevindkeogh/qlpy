"""
This module uses the QuantLib quantitative finance library to bootstrap
interest rate curves. The purpose of this file is to bootstrap many
curves quickly, with a variety of conventions and rates. Please see
quantlib.org for all information related to the QuantLib library.
Please see Kevin Keogh, kevin dot d dot keogh at gmail dot com, with
any questions on the use and operation of this script.
"""
import QuantLib as qlib
# import pandas
import csv

class Curve:
    """
    The Curve object is the primary result of this file. Curve objects
    import the curve name and date, import the conventions, market 
    data, and instruments csv's from the directory, and ultimately
    create the discount factors from which the curves are built.
    """
    def __init__(self, curve, curve_date):
        self.name = curve
        self.curve_date = curve_date

        # TODO: vastly increase the length of this dictionary
        self.holiday_calendar = {
        "NYSE": qlib.UnitedStates(qlib.UnitedStates.NYSE)
        }

        # import csv's as dicts
        self.conventions = self.csv_dict_helper(self, 'conventions.csv')
        self.market_data = self.csv_dict_helper(self, 'market_data.csv')
        self.instruments = self.csv_dict_helper(self, 'instruments.csv')

        # add a few general conventions
        self.settlement_date = curve_date + qlib.Period(
            int(self.conventions['deposits_SpotLag']), qlib.Days)
        self.currency = self.conventions['general_Currency']
        self.calendar = self.holiday_calendar[
            self.conventions['general_HolidayCalendar']]

        # InstrumentCollector objects
        self.deposits = DepositsInsts(self)
        # self.futures = FuturesInsts(self)
        # self.fras = FRAsInsts(self)
        # self.swaps = SwapsInsts(self)

        # Helper objects
        # self.outputs = Outputs()

    def csv_dict_helper(self, curve, filename):
        result = {}

        with open(filename) as infile:
            reader = csv.reader(infile)
            first_row = next(reader)
            col_num = first_row.index(curve.name)
            # special case, since we had to import the
            # first row to get the headers
            result[first_row[0]] = first_row[col_num]
            for row in reader:
                key = row[0]
                result[key] = row[col_num]
        return result

class InstrumentCollector:
    def __init__(self):

        self.bus_day_convention = {
            'Modified Following': qlib.ModifiedFollowing,
            'Following': qlib.Following,
            'Preceding': qlib.Preceding,
            'Modified Preceding': qlib.ModifiedPreceding,
            'Unadjusted': qlib.Unadjusted
        }

        self.day_count_fraction = {
            'Act360': qlib.Actual360(),
            'Act365Fixed': qlib.Actual365Fixed(),
            'ActAct': qlib.ActualActual(),
            'Bus252': qlib.Business252(),
            '30360': qlib.Thirty360()
        }

    def __iter__(self):
        for inst in self.instruments:
            yield inst

    def get_instruments(self, curve, filter_string):
        """
        get_instruments takes the curve object, the instruments DataFrame
        and market_data DataFrame and returns a list of tuples, where each
        list element is the (instrument period (as a QuantLib object),
        instrument rate (as a QuantLib object)). The function takes the
        all instruments listed in the instruments file and filters for
        those that include the filter word in the name. Note that futures
        follow a different procedure, where they are determined by number,
        as opposed to a specific True/False flag, and the instruments
        argument is actually the conventions DataFrame.

        Args:
            curve (Curve): Curve-class object
            instruments (DataFrame): pandas DataFrame of the
                                    'instruments.csv' or 'conventions.csv'
            market_data (DataFrame): pandas DataFrame of the
                                    'market_data.csv'
            filter_string (str): Word to filter the instruments by
                                 (typically 'deposits' or 'swaps')

        Returns:
            instruments_output (list): list of tuples of QuantLib periods
                                       and QuantLib quote objects. The list
                                       only contains elements that are True
                                       in the instruments DataFrame or, if
                                       futures, the convention-determined
                                       number of futures
        """
        instruments = []

        # filter instruments for instruments
        insts = [key for key, value in curve.instruments.items() 
            if filter_string in key and 
            value.upper() == 'TRUE']

        # create list of tuples (qlib.Period, qlib.SimpleQuote)
        for inst in insts:
            period = self.period_function(inst)
            rate = qlib.SimpleQuote(float(curve.market_data[inst]))
            instruments.append((period, rate))
        return instruments

    def period_function(self, string):
        """
        period_function parses a string (something like 'deposits_ON' or
        'swaps_10YR') and returns the length (in the examples, 1 and 10)
        and the period (in the examples, days and years). It then returns
        the QuantLib object for each.

        Args:
            string (str): string of instrument, eg. 'deposits_ON'

        Returns
            object: QuantLib Period object
        """
        delimiter = '_'
        index = string.find(delimiter)
        string = string[index + 1:]
        length = len(string)
        period_type = string[-2:]

        # determine period length (e.g. number of years)
        if period_type == 'ON':
            period_length = 1
        elif period_type == 'TN':
            period_length = 2
        elif period_type == 'SN':
            period_length = 3
        else:
            period_length = string[:length-2]

        # determine period type (e.g. years) and return object
        if period_type == 'YR':
            return qlib.Period(int(period_length), qlib.Years)
        elif period_type == 'MO':
            return qlib.Period(int(period_length), qlib.Months)
        elif period_type == 'WK':
            return qlib.Period(int(period_length), qlib.Weeks)
        elif    period_type == 'ON' or \
                period_type == 'TN' or \
                period_type == 'SN':
            return qlib.Period(int(period_length), qlib.Days)

class DepositsInsts(InstrumentCollector):
    
    def __init__(self, curve):
        super(DepositsInsts, self).__init__()

        self._inst_ids = self.get_instruments(
            curve, 'deposits')
        self.instruments = self.get_deposits_rate_helpers(
            self._inst_ids, curve)

    def get_deposits_rate_helpers(self, instruments, curve):
        """
        get_deposits_rate_helpers takes the Curve object, and loops through
        the elements deposits_instruments attribute list to create a list
        of DepositRateHelpers QuantLib objects. These objects use several
        of the conventions that are assigned to the Curve object (besides
        the deposits_instruments), namely the date, settlement days,
        calendar, business day convention, and day-count-fraction. Note
        that the End of Month parameter has been permanently set to False,
        as I am not aware of any deposit rate instruments that only pays
        EOM.

        Args:
            curve (object): Curve-class object

        Returns:
            deposit_rate_helpers (list): list of QuantLib DepositRateHelper
                                         objects.
        """
        return [qlib.DepositRateHelper(
            qlib.QuoteHandle(rate),
            period,
            int(curve.conventions['deposits_SpotLag']),
            curve.calendar,
            self.bus_day_convention[curve.conventions['deposits_Adjustment']],
            False,  # end of month
            self.day_count_fraction[curve.conventions['deposits_DCF']]) 
            for period, rate in instruments]



today = qlib.Date(31, 12, 2014)
usd = Curve('USD_3M', today)

print(usd.deposits)

# for inst in usd.deposits:
#     print(inst)
# # for inst in usd.deposits:
# #     print(inst)