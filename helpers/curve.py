"""
This module uses the QuantLib quantitative finance library to bootstrap
interest rate curves. The purpose of this file is to bootstrap many
curves quickly, with a variety of conventions and rates. Please see
quantlib.org for all information related to the QuantLib library.
Send me an email, kevin dot d dot keogh at gmail dot com, with
any questions on the use of this script, and fork it to make any 
improvements!

TODO:   1. Put dicts in another file to import?
        5. Add support for calculating futures convexity
        9. holiday_calendar dict needs significant work. Might need 2 
        functions so as to specify the country -> calendar. >> I should 
        probably just simplify and specify both in the dict. <<

"""
import QuantLib as ql
import csv, os
import itertools

class Curve:
    """
    The Curve object is the primary result of this module. Curve 
    objects take the curve name and date as inputs, and the conventions, 
    market data, and instruments csv's from the directory, and ultimately
    create the dates and discount factors from which the curves are built.

    The object is meant to be the only exposed object from this module, with
    one primary method -- discountfactor(). The module will build a curve based
    on the curve name, which needs to match exactly to the curve name in the
    market data, instruments, and conventions csv's.

    The curve can take deposit rates, futures, swap rates, and ois swap rates
    in order to build the curve. Dual-curve bootstrapping is not yet implemented.

    The Curve has 1 main public method -- .discount_factor(date) and a few
    exposed derived attributes

    Attributes:
        curve (str):            string of the curve name (must match exactly to
                                the name in the csvs used for curve data and 
                                conventions)
        date (ql.object):     QuantLib object of the curve date.
        currency (str):         string of the currency of the curve being built
        instruments(list):      list of quantlib objects that are the instruments
                                that are ultimately used in the construction of the
                                LiborCurve.
        qlcurve(ql object): the QuantLib object that holds the Curve object.
        discount_factors (float): list of discount factors that were calculated for
                                each of the instruments that were used for curve
                                construction
        dates (str):            ISO dates for each of the maturity dates for each
                                instrument you've added to the curve.

    """
    def __init__(self, curve, curve_date, conn):
        self.name = curve
        self.curve_date = curve_date
        self.conn = conn

        self.day_count_fraction = {
            'Act360': ql.Actual360(),
            'Act365Fixed': ql.Actual365Fixed(),
            'ActAct': ql.ActualActual(),
            'Bus252': ql.Business252(),
            '30360': ql.Thirty360()
        }

        # TODO: vastly increase the length of this dictionary
        self.holiday_calendar = {
        "NYSE": ql.UnitedStates(ql.UnitedStates.NYSE)
        }

        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data/')

        # get data
        cursor = conn.cursor()
        sql_statement = ('SELECT * FROM conventions '
                         'where curve_name is "{curve}"').format(**locals())
        cursor.execute(sql_statement)
        self.conventions = cursor.fetchone()
        if self.conventions is None:
            raise ValueError('No conventions exist for {self.name}'.format(**locals()))
        
        sql_statement = ('SELECT * FROM rates_data '
<<<<<<< Updated upstream
                         'where curve_name is "{curve}"').format(**locals())
        cursor.execute(sql_statement)
        self.market_data = cursor.fetchone()
=======
                         'WHERE curve_name IS "{self.name}" '
                         'AND date IS "{self.iso_date}"').format(**locals())
        cursor.execute(sql_statement)
        self.rates_data = cursor.fetchone()
        if self.rates_data is None:
            raise ValueError('No data available for {self.name} on {self.iso_date}'.format(**locals()))
>>>>>>> Stashed changes

        sql_statement = ('SELECT * FROM instruments '
                         'where curve_name is "{curve}"').format(**locals())
        cursor.execute(sql_statement)        
        self.instrument_ids = cursor.fetchone()
        if self.instrument_ids is None:
            raise ValueError('No instruments specified for {self.name}'.format(**locals()))
        
        # add a few general conventions
        self.settlement_date = curve_date + ql.Period(
            int(self.conventions['deposits_SpotLag']), ql.Days)
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
            date (ql.object):     date for the discount factor you're 
                                    requesting

        Returns:
            discount factor(float): discount factor for that date you requested

        """
        return self.qlcurve.discount(date)

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

    def dict_gen(self, curs):
        ''' 
        From Python Essential Reference by David Beazley
        '''
        field_names = [d[0].lower() for d in curs.description]
        while True:
            rows = curs.fetchmany()
            if not rows: return
            for row in rows:
                yield dict(itertools.izip(field_names, row))

    def export(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs/')
        with open(path + self.name + '.csv', 'w', newline='') as output:
            outfile = csv.writer(output, delimiter=',')
            data = [['',self.name]]
            for date in enumerate(self.dates):
                data.append((date[1], self.discount_factors[date[0]]))
            outfile.writerows(data)
        output.close()

class LiborCurve(Curve):
    """
    LiborCurve implementation of the Curve object. Used for generating
    Libor (and similar) curves. The curve can be dual-bootstrapped, using
    a convention that enables it. In order to dual-bootstrap, there must
    be an associated 'CCY_OIS' curve, which will be built first, then used to
    discount the swaps. 

    Note: Not to be used for overnight indices.
    """
    def __init__(self, curve, curve_date, conn):
        super(LiborCurve, self).__init__(curve, curve_date, conn)

    def build(self):
        """
        Currently a private method that handles the actual curve construction.
        Applied here in case I ever want to make the LiborCurve object lazy,
        and require that some method be called before the curve is actually
        built.
        """

        if self.conventions['general_RequiresOIS'].lower() == 'true':
            self.ois_curvename = self.conventions['general_Currency'] + "_OIS"
            self.ois_curve = OISCurve(self.ois_curvename, self.curve_date, self.conn)

        # InstrumentCollector objects
        self.instruments = DepositsInsts(self)
        self.instruments += FuturesInsts(self)
        self.instruments += FRAsInsts(self)
        self.instruments += SwapsInsts(self)
        
        self.qlcurve = ql.PiecewiseCubicZero(
                                self.settlement_date,
                                self.instruments,
                                self.day_count_fraction[self.conventions['deposits_DCF']])

        self.dates = []
        self.discount_factors = []

        for date in self.qlcurve.dates():
            self.dates.append(date.ISO())
            self.discount_factors.append(self.qlcurve.discount(date))

class OISCurve(Curve):
    """
    OISCurve implementation of the Curve object. Used for generating OIS
    indices (currently only USD, EUR, and GBP). 

    Note: Not to be used for LIBOR (and similar) indices.
    """

    def __init__(self, curve, curve_date, conn):
        super(OISCurve, self).__init__(curve, curve_date, conn)

    def build(self):
        """
        Currently a private method that handles the actual curve construction.
        Applied here in case I ever want to make the OISCurve object lazy,
        and require that some method be called before the curve is actually
        built.
        """

        # InstrumentCollector objects
        self.instruments = DepositsInsts(self) # Should only take 1 O/N rate
        self.instruments += OISSwapsInsts(self)

        self.qlcurve = ql.PiecewiseCubicZero(
            self.settlement_date,
            self.instruments,
            self.day_count_fraction[self.conventions['deposits_DCF']])

        self.dates = []
        self.discount_factors = []

        for date in self.qlcurve.dates():
            self.dates.append(date.ISO())
            self.discount_factors.append(self.qlcurve.discount(date))

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
            'Modified Following': ql.ModifiedFollowing,
            'Following': ql.Following,
            'Preceding': ql.Preceding,
            'Modified Preceding': ql.ModifiedPreceding,
            'Unadjusted': ql.Unadjusted
        }

    def __iter__(self):
        for inst in self.instruments:
            yield inst

    def __add__(self, other):
        return self.instruments + other.instruments

    def __len__(self):
        return len(self.instruments)

    def get_instruments(self, curve):
        """
        The get_instruments function serves to return a list of tuples,
        where each item holds the ql.period object and the associated
        rate for each item. These tuples are iterated through when
        gathering the rate helpers.

        Args:
            curve (LiborCurve object):  curve that is being built
            filter_string(string):      string of the type of rate helper
                                        that is needed to build the curve,
                                        typically 'deposits' or 'swaps'

        Returns:
            instruments (list):         list of tuples (period, rate), where
                                        the period is a ql.Period object and
                                        the rate is a floating number
        """
<<<<<<< Updated upstream
        instruments = []

        # filter instruments for instruments
        insts = [key for key, value in curve.instrument_ids.items() 
            if filter_string in key and 
            value.upper() == 'TRUE']

        # create list of tuples (ql.Period, ql.SimpleQuote)
        for inst in insts:
            period = self.period_function(inst)
            rate = ql.SimpleQuote(float(curve.market_data[inst]))
            instruments.append((period, rate))
        return instruments
=======
        sql_stmt = ('SELECT INSTRUMENT_CONVENTIONS.intrument_type, ' 
                           'RATES_DATA.rate, '
                           'INSTRUMENT_CONVENTIONS.instrument_maturity '
                      'FROM CURVE_INSTRUMENTS '
                        'JOIN RATES_DATA ON CURVE_INSTRUMENTS.instrument_name'
                          ' = RATES_DATA.instrument_name AND '
                        'JOIN INSTRUMENT_CONVENTIONS ON CURVE_INSTRUMENTS.instrument_name'
                          ' = INSTRUMENT_CONVENTIONS.instrument_name '
                      'WHERE CURVE_INSTRUMENTS.curve_name = {self.curve_name} AND '
                        'RATES_DATA.date = {self.iso_date}').format(**locals())
        
        cursor.execute(sql_stmt) 
       
        insts = {}
 
        for row in cursor:
            try:
                insts[row['instrument_type']]row['instrument_maturity'] = row['rate']
            except KeyError:
                insts[row['instrument_type']] = {}
                insts[row['instrument_type']]row['instrument_maturity'] = row['rate']
        
        return insts
>>>>>>> Stashed changes

    def period_function(self, string):
        """
        period_function parses a string (something like 'deposits_ON' or
        'swaps_10YR') and returns the length (in the examples, 1 and 10)
        and the period (in the examples, days and years). It then returns
        the QuantLib object for each.

        Args:
            string (str):           string of instrument, eg. 'deposits_ON'

        Returns
            Period (ql.object):   Object-equivalent of the period in the
                                    input string
        """

        units = {
        'ON': ql.Period(1, ql.Days),
        'TN': ql.Period(2, ql.Days),
        'SN': ql.Period(3, ql.Days),
        'W' : ql.Weeks,
        'WK': ql.Weeks,
        'M' : ql.Months,
        'MO': ql.Months,
        'Y' : ql.Years,
        'YR': ql.Years
        }

        inst = string.split('_')[1]
        digits = ''.join([s for s in inst if s.isdigit()])
        period = ''.join([s for s in inst if s.isalpha()])

        if digits == '':
            return units[period]
        else:
            return ql.Period(int(digits), units[period])

class DepositsInsts(InstrumentCollector):
    """
    DepositsInsts is an InstrumentCollector for deposits instruments. The
    primary utility is the get_rate_helpers function, which turns the
    instrument rates into ql.rate helpers, which are subsequently used to
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
            deposit_rate_helpers (list):    list of ql.DepositRateHelper
                                            objects.
        """
        return [ql.DepositRateHelper(
            ql.QuoteHandle(rate),
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
    instrument rates into ql.rate helpers, which are subsequently used to
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
        where each item holds the ql.period object and the associated
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
                                        the rate is a simple ql.quote object
        """
        instruments = []

        # filter instruments for instruments
        insts = [key for key, value in curve.instrument_ids.items() 
            if 'fras' in key and 
            value.upper() == 'TRUE']

        # create list of tuples (ql.Period, ql.SimpleQuote)
        for inst in insts:
            inst_period = inst.split('_')[1]
            start_month = int(inst_period.split('x')[0])
            end_month = int(inst_period.split('x')[1])
            rate = ql.SimpleQuote(float(curve.market_data[inst]))
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
            deposit_rate_helpers (list):    list of ql.FraRateHelper
                                            objects.
        """
        return [ql.FraRateHelper(
                ql.QuoteHandle(rate),
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
    instrument rates into ql.rate helpers, which are subsequently used to
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
            futures (list):             list of tuples, each tuple containing a ql
                                        Period object and a floating point rate
        """
        futures = [(ql.IMM.nextDate(curve.curve_date),
                    ql.SimpleQuote(float(curve.market_data['futures_1'])))]
        for future in range(int(curve.conventions['futures_NumberOfFutures']) - 1):
            period = ql.IMM.nextDate(futures[future][0])
            quote = ql.SimpleQuote(float(curve.market_data['futures_' + str(future + 2)]))
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
            deposit_rate_helpers (list):    list of ql.FuturesRateHelper
                                            objects.
        """
        return [ql.FuturesRateHelper(
                ql.QuoteHandle(rate),
                period,
                int(curve.conventions['futures_Tenor']),
                curve.calendar,
                self.bus_day_convention[curve.conventions['futures_Adjustment']],
                False, # End of month
                curve.day_count_fraction[curve.conventions['futures_DCF']],
                ql.QuoteHandle(ql.SimpleQuote(0.0)))
                for period, rate in self._inst_ids]

class SwapsInsts(InstrumentCollector):
    """
    SwapsInsts is an InstrumentCollector for swaps instruments. The
    primary utility is the get_rate_helpers function, which turns the
    instrument rates into ql.rate helpers, which are subsequently used to
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
        'Once'      : ql.Once,
        'Annual'    : ql.Annual,
        'Semiannual': ql.Semiannual,
        'Quarterly' : ql.Quarterly,
        'Monthly'   : ql.Monthly,
        'Daily'     : ql.Daily
        }

        self.ibor_indices = {
        'AUD': ql.AUDLibor,
        'CAD': ql.Cdor,
        'CHF': ql.CHFLibor,
        'DKK': ql.DKKLibor,
        'EUR': ql.Euribor,
        'GBP': ql.GBPLibor,
        'JPY': ql.JPYLibor,
        'NZD': ql.NZDLibor,
        'SEK': ql.SEKLibor,
        'TRL': ql.TRLibor,
        'USD': ql.USDLibor
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
            swap_rate_helpers (list):   list of ql.SwapRateHelper
                                        objects.
        """
        if curve.conventions['general_RequiresOIS'].lower() == 'true':
            return [ql.SwapRateHelper(
                ql.QuoteHandle(rate),
                period,
                curve.calendar,
                self.swap_freq[curve.conventions['swaps_FixedFreq']],
                self.bus_day_convention[curve.conventions['swaps_FixedAdjustment']],
                curve.day_count_fraction[curve.conventions['swaps_FixedLegDCF']],
                self.ibor_indices[curve.currency](self.period_function(curve.name)),
                ql.QuoteHandle(ql.SimpleQuote(0)), # spread on floating leg
                ql.Period(0, ql.Days), # days forward start
                ql.YieldTermStructureHandle(curve.ois_curve.qlcurve))
                for period, rate in self._inst_ids]
        else:            
            return [ql.SwapRateHelper(
                ql.QuoteHandle(rate),
                period,
                curve.calendar,
                self.swap_freq[curve.conventions['swaps_FixedFreq']],
                self.bus_day_convention[curve.conventions['swaps_FixedAdjustment']],
                curve.day_count_fraction[curve.conventions['swaps_FixedLegDCF']],
                self.ibor_indices[curve.currency](self.period_function(curve.name)))
                for period, rate in self._inst_ids]

class OISSwapsInsts(InstrumentCollector):
    """
    OISSwapsInsts is an InstrumentCollector for OIS swaps instruments. The
    primary utility is the get_rate_helpers function, which turns the
    instrument rates into ql.rate helpers, which are subsequently used to
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
        super(OISSwapsInsts, self).__init__()

        self.swap_freq = {
        'Once'      : ql.Once,
        'Annual'    : ql.Annual,
        'Semiannual': ql.Semiannual,
        'Quarterly' : ql.Quarterly,
        'Monthly'   : ql.Monthly,
        'Daily'     : ql.Daily
        }

        self.ibor_indices = {
        'EUR': ql.Eonia(),
        'GBP': ql.Sonia(),
        'USD': ql.FedFunds()
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
            swap_rate_helpers (list):   list of ql.SwapRateHelper
                                        objects.
        """
        return [ql.OISRateHelper(
                                   int(curve.conventions['deposits_SpotLag']),
                                   period,
                                   ql.QuoteHandle(rate),
                                   self.ibor_indices[curve.currency])
            for period, rate in self._inst_ids]



def main():
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
    usd = LiborCurve('USD_3M', now_date, conn)
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
