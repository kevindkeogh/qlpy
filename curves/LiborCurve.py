"""
This module uses the QuantLib quantitative finance library to bootstrap
interest rate curves. The purpose of this file is to bootstrap many
curves quickly, with a variety of conventions and rates. Please see
quantlib.org for all information related to the QuantLib library.
Send me an email, kevin dot d dot keogh at gmail dot com, with
any questions on the use of this script, and fork it to make any 
improvements!

TODO:   1. Put dicts in another file to import?
        2. Need to implmement dual-curve bootstrapping
        3. Virtually all the documentation needs to be re-written
        5. Add support for calculating futures convexity
        8. Add license. I can publish this on GitHub.
        9. holiday_calendar dict needs significant work. Might need 2 
        functions so as to specify the country -> calendar. >> I should 
        probably just simplify and specify both in the dict. <<
        10. Add FRAsInsts InstrumentCollector
"""
import QuantLib as qlib
import csv
import os

class LiborCurve:
    """
    The LiborCurve object is the primary result of this module. LiborCurve 
    objects take the curve name and date as inputs, and the conventions, 
    market data, and instruments csv's from the directory, and ultimately
    create the dates and discount factors from which the curves are built.

    The object is meant to be the only exposed object from this module, with
    one primary method -- discountfactor(). The module will build a curve based
    on the curve name, which needs to match exactly to the curve name in the
    market data, instruments, and conventions csv's.

    The curve can take deposit rates, futures, and swap rates in order to build
    the curve. FRAs are not yet implemented, and neither is dual-curve
    bootstrapping. These are both are currently on the to-do list.

    The LiborCurve has 1 main public methods -- .discountfactor(date) and a few
    exposed derived attributes

    Attributes:
        curve (str):            string of the curve name (must match exactly to
                                the name in the csvs used for curve data and 
                                conventions)
        date (qlib object):     quantlib object of the curve date.
        currency (str):         string of the currency of the curve being built
        instruments(list):      list of quantlib objects that are the instruments
                                that are ultimately used in the construction of the
                                LiborCurve.
        qlibcurve(qlib object): the QuantLib object that holds the C curve object.
        discount_factors (float): list of discount factors that were calculated for
                                each of the instruments that were used for curve
                                construction
        dates (str):            ISO dates for each of the maturity dates for each
                                instrument you've added to the curve.

    """
    def __init__(self, curve, curve_date):
        self.name = curve
        self.curve_date = curve_date

        self.day_count_fraction = {
            'Act360': qlib.Actual360(),
            'Act365Fixed': qlib.Actual365Fixed(),
            'ActAct': qlib.ActualActual(),
            'Bus252': qlib.Business252(),
            '30360': qlib.Thirty360()
        }

        # TODO: vastly increase the length of this dictionary
        self.holiday_calendar = {
        "NYSE": qlib.UnitedStates(qlib.UnitedStates.NYSE)
        }

        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'market_data/')

        # import csv's as dicts
        self.conventions = self.csv_dict_helper(self, 
                                                os.path.join(path, 'conventions.csv'))
        self.market_data = self.csv_dict_helper(self, 
                                                os.path.join(path, 
                                                'market_data.csv'),
                                                datatype=float)
        self.instrument_ids = self.csv_dict_helper(self,
                                                os.path.join(path, 'instruments.csv'))

        # add a few general conventions
        self.settlement_date = curve_date + qlib.Period(
            int(self.conventions['deposits_SpotLag']), qlib.Days)
        self.currency = self.conventions['general_Currency']
        self.calendar = self.holiday_calendar[
            self.conventions['general_HolidayCalendar']]

        # build curve
        self.build()

    def __iter__(self):
        for inst in self.instruments:
            yield inst

    def discount_factor(self, date):
        """
        Returns the discount factor for a specific date for the curve whose
        method you're calling. Uses the QuantLib curve to generate the exact
        discount factor needed for that date.

        Args:
            date (qlib object):     date for the discount factor you're 
                                    requesting

        Returns:
            discount factor(float): discount factor for that date you requested

        """
        return self.qlibcurve.discount(date)

    def csv_dict_helper(self, curve, filename, datatype=str):
        """
        Private function that is used to import csv's for use in construction.
        This function will create a dict based on key-value pairs where the key
        is the first column of the csv, and the value is based on the column
        matching the curve name. Therefore, it's important the curve name match
        exactly to the columns that are being imported.
        Args:
            curve (LiborCurve object):  LiborCurve object that we're building
            filename (str):             name of the file that we're using to
                                        download the data. Needs to be in the
                                        same directory as curvebuilder file.
            datatype(optional):         can be used to specify a datatype of the
                                        values in the returned dict. If none is
                                        specified, will return strings.

        Returns:
            result(dict):               dictionary of the first column of a csv
                                        and the column of the csv with the same
                                        name as the curve.
        """
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
                if row[col_num] == '':
                    result[key] = ''
                else:
                    result[key] = datatype(row[col_num])
        return result

    def build(self):
        """
        Currently a private method that handles the actual curve construction.
        Applied here in case I ever want to make the LiborCurve object lazy,
        and require that some method be called before the curve is actually
        built.
        """

        # InstrumentCollector objects
        self.instruments = DepositsInsts(self)
        self.instruments += FuturesInsts(self)
        self.instruments += FRAsInsts(self)
        self.instruments += SwapsInsts(self)

        self.qlibcurve = qlib.PiecewiseCubicZero(
            self.settlement_date,
            self.instruments,
            self.day_count_fraction[self.conventions['deposits_DCF']])

        self.dates = []
        self.discount_factors = []
        
        for date in self.qlibcurve.dates():
            self.dates.append(date.ISO())
            self.discount_factors.append(self.qlibcurve.discount(date))

class InstrumentCollector:
    """
    The InstrumentCollector is the meta-class that is used as a template
    for collecting instruments of all other types. Given that there are
    several overlapping aspects, and magic method overlap, it's useful to
    have a meta-class.

    The class has no pre-defined attributes, but does have two methods, as
    well as re-defining several magic methods for list concatenation.
    """
    def __init__(self):
        self.bus_day_convention = {
            'Modified Following': qlib.ModifiedFollowing,
            'Following': qlib.Following,
            'Preceding': qlib.Preceding,
            'Modified Preceding': qlib.ModifiedPreceding,
            'Unadjusted': qlib.Unadjusted
        }

    def __iter__(self):
        for inst in self.instruments:
            yield inst

    def __add__(self, other):
        return self.instruments + other.instruments

    def __len__(self):
        return len(self.instruments)

    def get_instruments(self, curve, filter_string):
        """
        The get_instruments function serves to return a list of tuples,
        where each item holds the qlib period object and the associated
        rate for each item. These tuples are iterated through when
        gathering the rate helpers.

        Args:
            curve (LiborCurve object):  curve that is being built
            filter_string(string):      string of the type of rate helper
                                        that is needed to build the curve,
                                        typically 'deposits' or 'swaps'

        Returns:
            instruments (list):         list of tuples (period, rate), where
                                        the period is a qlib Period object and
                                        the rate is a floating number
        """
        instruments = []

        # filter instruments for instruments
        insts = [key for key, value in curve.instrument_ids.items() 
            if filter_string in key and 
            value.upper() == 'TRUE']

        # create list of tuples (qlib.Period, qlib.SimpleQuote)
        for inst in insts:
            period = self.period_function(inst)
            rate = qlib.SimpleQuote(curve.market_data[inst])
            instruments.append((period, rate))
        return instruments

    def period_function(self, string):
        """
        period_function parses a string (something like 'deposits_ON' or
        'swaps_10YR') and returns the length (in the examples, 1 and 10)
        and the period (in the examples, days and years). It then returns
        the QuantLib object for each.

        Args:
            string (str):           string of instrument, eg. 'deposits_ON'

        Returns
            Period (qlib object):   Object-equivalent of the period in the
                                    input string
        """

        units = {
        'ON': qlib.Period(1, qlib.Days),
        'TN': qlib.Period(2, qlib.Days),
        'SN': qlib.Period(3, qlib.Days),
        'W' : qlib.Weeks,
        'WK': qlib.Weeks,
        'M' : qlib.Months,
        'MO': qlib.Months,
        'Y' : qlib.Years,
        'YR': qlib.Years
        }

        inst = string.split('_')[1]
        digits = ''.join([s for s in inst if s.isdigit()])
        period = ''.join([s for s in inst if s.isalpha()])

        if digits == '':
            return units[period]
        else:
            return qlib.Period(int(digits), units[period])

class DepositsInsts(InstrumentCollector):
    """
    DepositsInsts is an InstrumentCollector for deposits instruments. The
    primary utility is the get_rate_helpers function, which turns the
    instrument rates into qlib rate helpers, which are subsequently used to
    build the curve.

    The class only requires the curve that is being built, which already has
    the associated data required to create the rate helpers.

    Attributes:
        _inst_ids (PRIVATE, list):  list of the names of the deposit rates to
                                    be included in the curve construction
        instruments (list):         list of the rate helpers for each instrument
                                    to be included in the curve
    """
    
    def __init__(self, curve):
        super(DepositsInsts, self).__init__()

        self._inst_ids = self.get_instruments(
            curve, 'deposits')
        self.instruments = self.get_rate_helpers(curve)

    def get_rate_helpers(self, curve):
        """
        get_rate_helpers takes the LiborCurve object, and loops 
        through the list of tuples in _inst_ids to create a list of 
        DepositRateHelpers QuantLib objects. These objects use
        several of the conventions that are assigned to the Curve object
        in the conventions dict. Note that the End of Month parameter 
        has been permanently set to False, as I am not aware of any
        deposit rate instruments that only pays EOM.

        Args:
            curve (LiborCurve object):      curve that you're building

        Returns:
            deposit_rate_helpers (list):    list of qlib DepositRateHelper
                                            objects.
        """
        return [qlib.DepositRateHelper(
                qlib.QuoteHandle(rate),
                period,
                int(curve.conventions['deposits_SpotLag']),
                curve.calendar,
                self.bus_day_convention[curve.conventions['deposits_Adjustment']],
                False,  # end of month
                curve.day_count_fraction[curve.conventions['deposits_DCF']]) 
                for period, rate in self._inst_ids]

class FRAsInsts(InstrumentCollector):
    """
    FRAsInsts is an InstrumentCollector for FRA instruments. The
    primary utility is the get_rate_helpers function, which turns the
    instrument rates into qlib rate helpers, which are subsequently used to
    build the curve.

    The class only requires the curve that is being built, which already has
    the associated data required to create the rate helpers.

    Attributes:
        _inst_ids (PRIVATE, list):  list of the names of the FRA rates to
                                    be included in the curve construction
        instruments (list):         list of the rate helpers for each instrument
                                    to be included in the curve
    """
    
    def __init__(self, curve):
        super(FRAsInsts, self).__init__()

        self._inst_ids = self.get_instruments(curve)
        self.instruments = self.get_rate_helpers(curve)

    def get_instruments(self, curve):
        """
        The get_instruments function serves to return a list of tuples,
        where each item holds the qlib period object and the associated
        rate for each item. These tuples are iterated through when
        gathering the rate helpers.

        Args:
            curve (LiborCurve object):  curve that is being built
            filter_string(string):      string of the type of rate helper
                                        that is needed to build the curve,
                                        typically 'deposits' or 'swaps'

        Returns:
            instruments (list):         list of tuples (start_month, end_month,
                                        rate), where the start_month and end_month
                                        are integers representing the time from the
                                        curve date where that FRA would be, and
                                        the rate is a simple qlib quote object
        """
        instruments = []

        # filter instruments for instruments
        insts = [key for key, value in curve.instrument_ids.items() 
            if 'fras' in key and 
            value.upper() == 'TRUE']

        # create list of tuples (qlib.Period, qlib.SimpleQuote)
        for inst in insts:
            inst_period = inst.split('_')[1]
            start_month = int(inst_period.split('x')[0])
            end_month = int(inst_period.split('x')[1])
            rate = qlib.SimpleQuote(curve.market_data[inst])
            instruments.append((start_month, end_month, rate))
        return instruments

    def get_rate_helpers(self, curve):
        """
        get_rate_helpers takes the LiborCurve object, and loops 
        through the list of tuples in _inst_ids to create a list of 
        FraRateHelpers QuantLib objects. These objects use
        several of the conventions that are assigned to the Curve object
        in the conventions dict. Note that the End of Month parameter 
        has been permanently set to False, as I am not aware of any
        fra rate instruments that only pays EOM.

        Args:
            curve (LiborCurve object):      curve that you're building

        Returns:
            deposit_rate_helpers (list):    list of qlib FraRateHelper
                                            objects.
        """
        return [qlib.FraRateHelper(
                qlib.QuoteHandle(rate),
                start_month,
                end_month,
                int(curve.conventions['fras_SpotLag']),
                curve.calendar,
                self.bus_day_convention[curve.conventions['fras_Adjustment']],
                False, # end of month,
                curve.day_count_fraction[curve.conventions['fras_DCF']])
                for start_month, end_month, rate in self._inst_ids]

class FuturesInsts(InstrumentCollector):
    """
    FuturesInsts is an InstrumentCollector for futures instruments. The
    primary utility is the get_rate_helpers function, which turns the
    instrument rates into qlib rate helpers, which are subsequently used to
    build the curve.

    The class only requires the curve that is being built, which already has
    the associated data required to create the rate helpers.

    Attributes:
        _inst_ids (PRIVATE, list):  list of the names of the deposit rates to
                                    be included in the curve construction
        instruments (list):         list of the rate helpers for each instrument
                                    to be included in the curve
    """
    
    def __init__(self, curve):
        super(FuturesInsts, self).__init__()

        self._inst_ids = self.get_instruments(curve)
        self.instruments = self.get_rate_helpers(curve)

    def get_instruments(self, curve):
        """
        The FuturesInsts object overwrites the meta-class get_instruments function,
        as futures isntruments and dates are derived differently than deposits, FRAs,
        and swaps. The number of futures, adjusted for the removal of the first future
        in the case that it is shorter than the DaysToExclude parameter. The function
        returns a list of tuples, where each item is a Period and rate.

        Args:
            curve (LiborCurve object):  curve that you're building

        Returns:
            futures (list):             list of tuples, each tuple containing a qlib
                                        Period object and a floating point rate
        """
        futures = [(qlib.IMM.nextDate(curve.curve_date),
                    qlib.SimpleQuote(curve.market_data['futures_1']))]
        for future in range(int(curve.conventions['futures_NumberOfFutures']) - 1):
            period = qlib.IMM.nextDate(futures[future][0])
            quote = qlib.SimpleQuote(curve.market_data['futures_' + str(future + 2)])
            futures.append((period, quote))
        if (futures[0][0] - curve.curve_date) > \
                int(curve.conventions['futures_DaysToExclude']):
            return futures[:-1]
        else:
            return futures[1:]

    def get_rate_helpers(self, curve):
        """
        get_deposits_rate_helpers takes the LiborCurve object, and loops 
        through the list of tuples in _inst_ids to create a list of 
        FuturesRateHelper QuantLib objects. This object uses the conventions
        dict, along with the periods/rates from the get_instruments method. Note
        that the End of Month parameter has been permanently set to False,
        as I am not aware of any future instruments that only pay EOM. Further
        note that convexity has been hard-coded to zero, but will be implemented
        at a later date.

        Args:
            curve (LiborCurve object):      curve that you're building

        Returns:
            deposit_rate_helpers (list):    list of qlib FuturesRateHelper
                                            objects.
        """
        return [qlib.FuturesRateHelper(
                qlib.QuoteHandle(rate),
                period,
                int(curve.conventions['futures_Tenor']),
                curve.calendar,
                self.bus_day_convention[curve.conventions['futures_Adjustment']],
                False, # End of month
                curve.day_count_fraction[curve.conventions['futures_DCF']],
                qlib.QuoteHandle(qlib.SimpleQuote(0.0)))
                for period, rate in self._inst_ids]

class SwapsInsts(InstrumentCollector):
    """
    SwapsInsts is an InstrumentCollector for swaps instruments. The
    primary utility is the get_rate_helpers function, which turns the
    instrument rates into qlib rate helpers, which are subsequently used to
    build the curve.

    The class only requires the curve that is being built, which already has
    the associated data required to create the rate helpers.

    Note that there are only a limited number of currencies that can be supported
    by these ratehelpers. Further development would be needed to add Ibor indices
    to the library, so that they could be used for ratehelper construction.

    Attributes:
        _inst_ids (PRIVATE, list):  list of the names of the swap rates to
                                    be included in the curve construction
        instruments (list):         list of the rate helpers for each instrument
                                    to be included in the curve
    """
    def __init__(self, curve):
        super(SwapsInsts, self).__init__()

        self.swap_freq = {
        'Once'      : qlib.Once,
        'Annual'    : qlib.Annual,
        'Semiannual': qlib.Semiannual,
        'Quarterly' : qlib.Quarterly,
        'Monthly'   : qlib.Monthly,
        'Daily'     : qlib.Daily
        }

        self.ibor_indices = {
        'AUD': qlib.AUDLibor,
        'CAD': qlib.CADLibor,
        'CHF': qlib.CHFLibor,
        'DKK': qlib.DKKLibor,
        'EUR': qlib.Euribor,
        'GBP': qlib.GBPLibor,
        'JPY': qlib.JPYLibor,
        'NZD': qlib.NZDLibor,
        'SEK': qlib.SEKLibor,
        'TRL': qlib.TRLibor,
        'USD': qlib.USDLibor
        }

        self._inst_ids = self.get_instruments(curve, 'swaps')
        self.instruments = self.get_rate_helpers(curve)

    def get_rate_helpers(self, curve):
        """
        get_rate_helpers takes the LiborCurve object, and loops 
        through the list of tuples in _inst_ids to create a list of 
        SwapRateHelpers QuantLib objects. These objects use
        several of the conventions that are assigned to the Curve object
        in the conventions dict.

        Args:
            curve (LiborCurve object):  curve that you're building

        Returns:
            swap_rate_helpers (list):   list of qlib SwapRateHelper
                                        objects.
        """
        return [qlib.SwapRateHelper(
            qlib.QuoteHandle(rate),
            period,
            curve.calendar,
            self.swap_freq[curve.conventions['swaps_FixedFreq']],
            self.bus_day_convention[curve.conventions['swaps_FixedAdjustment']],
            curve.day_count_fraction[curve.conventions['swaps_FixedLegDCF']],
            self.ibor_indices[curve.currency](self.period_function(curve.name)))
            for period, rate in self._inst_ids]

def main():
    # Sample use
    qlib.Settings.instance().evaluationDate = qlib.Date(31,12,2014)
    today = qlib.Date(31, 12, 2014)

    usd = LiborCurve('USD_3M', today)

    for date in enumerate(usd.dates):
        print(date[1], usd.discount_factors[date[0]])

    randomdate = qlib.Date(12,2,2018)

    df = usd.discount_factor(randomdate)

    print(df)

if __name__ == '__main__':
    main()
