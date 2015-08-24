"""
This module uses the QuantLib quantitative finance library to bootstrap
interest rate curves. The purpose of this file is to bootstrap many
curves quickly, with a variety of conventions and rates. Please see
quantlib.org for all information related to the QuantLib library.
Please see Kevin Keogh, kevin dot d dot keogh at gmail dot com, with
any questions on the use and operation of this script.
"""

import QuantLib as qlib
import pandas

class Curve:
    """
    Curve class is a class that contains all the classes and methods
    used in order to build a PiecewiseCubicZero QuantLib yield curve.
    Instantiating a Curve object requires all the information needed
    to build a yield curve, and, on instantiation, all the information
    is populated.
    """

    def __init__(self, curve, curve_date, conventions,
                 instruments, market_data):
        self.name = curve
        self.curve_date = curve_date

        self.settlement_date = curve_date + \
            qlib.Period(
                int(conventions[self.name]["deposits_SpotLag"]),
                qlib.Days)
        self.calendar = self.holiday_calendar(
            conventions[self.name]["general_HolidayCalendar"])
        self.currency = conventions[self.name]["general_Currency"]
        self.instruments = instruments
        self.market_data = market_data
        self.conventions = conventions

        # nested class declarations
        self.deposits = self.Deposits(self, conventions)
        self.futures = self.Futures(self, conventions)
        self.swaps = self.Swaps(self, conventions)
        self.outputs = self.Outputs()

    class Deposits:

        def __init__(self, curve, conventions):
            # conventions
            self.settlement_days = int(
                conventions[curve.name]["deposits_SpotLag"])
            self.day_counter = curve.day_count_fraction(
                conventions[curve.name]["deposits_DCF"])
            self.adjustment = curve.bus_day_convention(
                conventions[curve.name]["deposits_Adjustment"])

            # utilies
            self.instruments = []
            self.rate_helpers = []

        def get_deposits_rate_helpers(self, curve):
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
            self.rate_helpers = [qlib.DepositRateHelper(
                qlib.QuoteHandle(quote),
                date,
                self.settlement_days,
                curve.calendar,
                self.adjustment,
                False,  # end of month
                self.day_counter)
                                 for date, quote in self.instruments]
            curve.outputs.rate_helpers += self.rate_helpers

    class Futures:

        def __init__(self, curve, conventions):
            # conventions
            self.settlement_days = conventions[curve.name]["futures_SpotLag"]
            self.day_counter = curve.day_count_fraction(
                conventions[curve.name]["futures_DCF"])
            self.adjustment = curve.bus_day_convention(
                conventions[curve.name]["futures_Adjustment"])
            self.months = int(conventions[curve.name]["futures_Tenor"])
            self.number_of_futures = int(
                conventions[curve.name]["futures_NumberOfFutures"])
            self.days_to_exclude = int(
                conventions[curve.name]["futures_DaysToExclude"])

            # utilities
            self.instruments = []
            self.rate_helpers = []

        def get_futures_imm_codes(self, curve, exclude_first_future):
            """
            get_futures_imm_codes takes the curve and a boolean
            exclude_first_future parameter to determine whether the
            first future should be included. The function calculates the first
            to 1 + the number of futures, and returns the first through second-
            to-last or second through last futures IMM codes in a list.

            Args:
                curve (Curve): curve-class object
                exclude_first_future (bool): t/f of including the first future

            Returns:
                futures_imm_codes (list): list of futures IMM codes (str)
            """
            futures_imm_codes = []
            for future in range(self.number_of_futures + 1):
                if future == 0:
                    futures_imm_codes.append(
                        qlib.IMM.nextCode(curve.curve_date))
                else:
                    futures_imm_codes.append(
                        qlib.IMM.nextCode(futures_imm_codes[future - 1]))
            if exclude_first_future:
                return futures_imm_codes[1:self.number_of_futures + 1]
            else:
                return futures_imm_codes[0:self.number_of_futures]

        # TODO implement convexity adjustment in code
        def get_futures_rate_helpers(self, curve):
            """
            get_futures_rate_helpers takes the Curve object, and loops through
            the elements futures_instruments attribute list to create a list
            of FuturesRateHelp QuantLib objects. These objects use several
            of the conventions that are assigned to the Curve object (besides
            the futures_instruments), namely the date, futures tenor, calendar,
            business day convention, and day-count-fraction. FuturesRateHelper
            Note also can take a convexity adjustment parameter. At this time,
            it has been set to 0, as the futures quotes I am currently using
            have already been adjusted for convexity. There is a plan to use
            this functionality in future.Note that the End of Month parameter
            has been permanently set to False, as I am not aware of any futures
            instrument that only pays EOM.

            Args:
                curve (object): Curve-class object

            Returns:
                futures_rate_helpers (list): list of QuantLib FuturesRateHelper
                                             objects.
            """
            self.rate_helpers = [qlib.FuturesRateHelper(
                qlib.QuoteHandle(quote),
                date,
                self.months,
                curve.calendar,
                self.adjustment,
                False,  # end of month
                self.day_counter,
                qlib.QuoteHandle(
                    qlib.SimpleQuote(0.0)))
                                 for date, quote in self.instruments]
            curve.outputs.rate_helpers += self.rate_helpers

    class Swaps:

        def __init__(self, curve, conventions):
            # conventions
            self.settlement_days = int(
                conventions[curve.name]["swaps_SpotLag"])
            # fixed leg conventions
            self.fixed_leg_frequency = self.swap_freqs(
                conventions[curve.name]["swaps_FixedFreq"])
            self.fixed_leg_tenor = self.swap_periods(
                conventions[curve.name]["swaps_FixedTenor"])
            self.fixed_leg_adjustment = curve.bus_day_convention(
                conventions[curve.name]["swaps_FixedAdjustment"])
            self.fixed_leg_day_counter = curve.day_count_fraction(
                conventions[curve.name]["swaps_FixedLegDCF"])
            # floating leg conventions
            self.floating_leg_frequency = self.swap_freqs(
                conventions[curve.name]["swaps_FloatFreq"])
            self.floating_leg_tenor = self.swap_periods(
                conventions[curve.name]["swaps_FloatTenor"])
            self.floating_leg_adjustment = curve.bus_day_convention(
                conventions[curve.name]["swaps_FloatAdjustment"])
            # utilities
            self.instruments = []
            self.rate_helpers = []

        def swap_index_name(self, curve):
            """
            swap_index takes a Curve-class object and returns the appropriate
            index. Because QuantLib has a separate index object for each
            currency (for reasons that are not entirely clear to me), this
            function is necessary for creating swapRateHelpers. The function
            takes the curve object, then uses the currency and
            floating_leg_tenor attributes to determine the index.

            Currently, the function can handle the following currencies:
            AUD, CAD, CHF, DKK, EUR, GBP, JPY, NZD, SEK, TRL, USD

            Args:
                curve (Curve): curve-class object

            Returns
                object: QuantLib index, defined for a specified period
            """
            if curve.currency == "AUD":
                return qlib.AUDLibor(self.floating_leg_tenor)
            elif curve.currency == "CAD":
                return qlib.CADLibor(self.floating_leg_tenor)
            elif curve.currency == "CHF":
                return qlib.CHFLibor(self.floating_leg_tenor)
            elif curve.currency == "DKK":
                return qlib.DKKLibor(self.floating_leg_tenor)
            elif curve.currency == "EUR":
                return qlib.Euribor(self.floating_leg_tenor)
            elif curve.currency == "GBP":
                return qlib.GBPLibor(self.floating_leg_tenor)
            elif curve.currency == "JPY":
                return qlib.JPYLibor(self.floating_leg_tenor)
            elif curve.currency == "NZD":
                return qlib.NZDLibor(self.floating_leg_tenor)
            elif curve.currency == "SEK":
                return qlib.SEKLibor(self.floating_leg_tenor)
            elif curve.currency == "TRL":
                return qlib.TRLibor(self.floating_leg_tenor)
            elif curve.currency == "USD":
                return qlib.USDLibor(self.floating_leg_tenor)

        def swap_freqs(self, freq):
            """
            swap_freqs takes a string a converts it to the reset frequency of
            a swap leg. This function takes all available frequencies available
            in QuantLib.

            Currently, the function takes the following strings:
            Once, Annual, Semiannual, Quarterly, Monthly, Daily

            Args:
                freq (str): reset frequency

            Returns:
                object: QuantLib object of reset frequency
            """
            if freq == "Once":
                return qlib.Once
            if freq == "Annual":
                return qlib.Annual
            if freq == "Semiannual":
                return qlib.Semiannual
            if freq == "Quarterly":
                return qlib.Quarterly
            if freq == "Monthly":
                return qlib.Monthly
            if freq == "Daily":
                return qlib.Daily

        def swap_periods(self, period):
            """
            swap_periods takes a string and converts it to payment frequency of
            a swapleg. The function currently only takes common payment
            frequencies.

            Currently, the function takes the following strings:
            Annual, Semiannual, Quarterly, Monthly, Daily

            Args:
                period (str): string of payment frequency

            Returns:
                object: Quantlib payment frequency object
            """
            if period == "Annual":
                return qlib.Period(1, qlib.Years)
            if period == "Semiannual":
                return qlib.Period(6, qlib.Months)
            if period == "Quarterly":
                return qlib.Period(3, qlib.Months)
            if period == "Monthly":
                return qlib.Period(1, qlib.Months)
            if period == "Daily":
                return qlib.Period(1, qlib.Days)

        def get_swaps_rate_helpers(self, curve):
            """
            get_swaps_rate_helpers takes the Curve object, and loops through
            the elements in the swaps_instruments attribute list to create a
            list of SwapRateHelper QuantLib objects. These objects use several
            of the conventions that are assigned to the Curve object (besides
            the swaps_instruments), namely the date, futures tenor calendar,
            business day convention, and day-count-fraction. FuturesRateHelper
            Note also can take a convexity adjustment parameter. At this time,
            it has been set to 0, as the futures quotes I am currently using
            have already been adjusted for convexity. There is a plan to use
            this functionality in future.Note that the End of Month parameter
            has been permanently set to False, as I am not aware of any futures
            instrument that only pays EOM.

            Args:
                curve (object): Curve-class object

            Returns:
                futures_rate_helpers (list): list of QuantLib FuturesRateHelper
                                             objects.
            """
            self.rate_helpers = [qlib.SwapRateHelper(
                qlib.QuoteHandle(quote),
                date,
                curve.calendar,
                self.fixed_leg_frequency,
                self.fixed_leg_adjustment,
                self.fixed_leg_day_counter,
                self.swap_index_name(curve))
                                 for date, quote in self.instruments]
            curve.outputs.rate_helpers += self.rate_helpers

    class Outputs:

        def __init__(self):
            self.rate_helpers = []
            self.qlib_curve = []
            self.pandas_curve = []
            self.dates = []
            self.discount_factors = []

    def bus_day_convention(self, adjustment):
        """
        bus_day_convention takes a string that is used in the
        conventions DataFrame, and returns the QuantLib-equivalent
        business day object. This function takes all business day
        conventions that are currently allowed in QuantLib.

        Currently, the function takes the following strings:
        Act360, Act365Fixed, ActAct, Bus252, 30360

        Args:
            adjustment (str): business day convention

        Returns:
            object: QuantLib business day convention object
        """
        if adjustment == "Modified Following":
            return qlib.ModifiedFollowing
        elif adjustment == "Following":
            return qlib.Following
        elif adjustment == "Preceding":
            return qlib.Preceding
        elif adjustment == "Modified Preceding":
            return qlib.ModifiedPreceding
        elif adjustment == "Unadjusted":
            return qlib.Unadjusted

    def holiday_calendar(self, calendar):
        """
        holiday_calendar takes a string that is used in the
        conventions DataFrame, and returns the QuantLib-equivalent
        calendar object. More will need to be added, particularly
        as more exotic curves are able to be built.

        Currently, the function takes the following strings:
        NYSE

        Args:
            calendar (str): string name of calendar

        Returns:
            object: Quantlib calendar object
        """
        if calendar == "NYSE":
            return qlib.UnitedStates(qlib.UnitedStates.NYSE)

    def day_count_fraction(self, dcf):
        """
        day_count_fraction takes a string that is used in the
        conventions DataFrame, and returns the QuantLib-equivalent
        day-count object. This function takes all day-counters that are
        currently allowed in QuantLib.

        Currently, the function takes the following strings:
        Act360, Act365Fixed, ActAct, Bus252, 30360

        Args:
            dcf (str): day count fraction string

        Returns:
            object: QuantLib day-count-fraction object
        """
        if dcf == "Act360":
            return qlib.Actual360()
        elif dcf == "Act365Fixed":
            return qlib.Actual365Fixed()
        elif dcf == "ActAct":
            return qlib.ActualActual()
        elif dcf == "Bus252":
            return qlib.Business252()
        elif dcf == "30360":
            return qlib.Thirty360()

    def period_function(self, string):
        """
        period_function parses a string (something like "deposits_ON" or
        "swaps_10YR") and returns the length (in the examples, 1 and 10)
        and the period (in the examples, days and years). It then returns
        the QuantLib object for each.

        Args:
            string (str): string of instrument, eg. "deposits_ON"

        Returns
            object: QuantLib Period object
        """
        delimiter = "_"
        index = string.find(delimiter)
        string = string[index + 1:]
        length = len(string)
        period_type = string[-2:]

        # determine period length (e.g. number of years)
        if period_type == "ON":
            period_length = 1
        elif period_type == "TN":
            period_length = 2
        elif period_type == "SN":
            period_length = 3
        else:
            period_length = string[:length-2]

        # determine period type (e.g. years) and return object
        if period_type == "YR":
            return qlib.Period(int(period_length), qlib.Years)
        elif period_type == "MO":
            return qlib.Period(int(period_length), qlib.Months)
        elif period_type == "WK":
            return qlib.Period(int(period_length), qlib.Weeks)
        elif    period_type == "ON" or \
                period_type == "TN" or \
                period_type == "SN":
            return qlib.Period(int(period_length), qlib.Days)

    def get_instruments(self, instruments, market_data, filter_string):
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
                                 (typically "deposits" or "swaps")

        Returns:
            instruments_output (list): list of tuples of QuantLib periods
                                       and QuantLib quote objects. The list
                                       only contains elements that are True
                                       in the instruments DataFrame or, if
                                       futures, the convention-determined
                                       number of futures
        """
        if filter_string == "futures":
            instruments_output = []
            # get futures maturity dates
            first_future_date = qlib.IMM.nextDate(self.curve_date)
            days_to_first_future = first_future_date - self.curve_date
            if days_to_first_future > int(self.futures.days_to_exclude):
                exclude_first = False
            else:
                exclude_first = True
            futures_imm_codes = self.futures.get_futures_imm_codes(
                self, exclude_first)
            # determine which future to start with
            futures_number = 1
            if exclude_first:
                futures_number = futures_number + 1
            if exclude_first:
                futures_number = futures_number
            # get futures quotes
            for date in futures_imm_codes:
                futures_date = qlib.IMM.date(date)
                futures_price = qlib.SimpleQuote(
                    market_data[self.name]
                    ["futures_" + str(futures_number)])
                data = (futures_date, futures_price)
                instruments_output.append(data)
                futures_number = futures_number + 1
            return instruments_output
        else:
            instruments_included = []
            instruments_periods = []
            instruments_rates = []
            instruments_output = []
            # filter instruments for instruments
            all_instruments = [inst for inst in
                               list(instruments.index.values)
                               if filter_string in inst]
            # filter instruments for True's
            for inst in all_instruments:
                if instruments[self.name][inst] == True:
                    instruments_included.append(inst)
            # get periods for all instruments
            for inst in instruments_included:
                instruments_periods.append(self.period_function(inst))
            # get rates for all instruments
            for inst in instruments_included:
                instruments_rates.append(qlib.SimpleQuote(
                    market_data[self.name][inst]))
            # create list of tuples for instruments
            for i in range(len(instruments_included)):
                data = (instruments_periods[i], instruments_rates[i])
                instruments_output.append(data)
            return instruments_output

    def build(self):
        # create Curve object
        #curve = Curve(curve, curve_date, conventions)

        # gather instruments
        self.deposits.instruments = self.get_instruments(
            self.instruments, self.market_data, "deposits")
        self.futures.instruments = self.get_instruments(
            self.conventions, self.market_data, "futures")
        self.swaps.instruments = self.get_instruments(
            self.instruments, self.market_data, "swaps")

        # create rate helpers
        self.deposits.get_deposits_rate_helpers(self)
        self.futures.get_futures_rate_helpers(self)
        self.swaps.get_swaps_rate_helpers(self)

        # build curve
        self.outputs.qlibcurve = qlib.PiecewiseCubicZero(
            self.settlement_date,
            self.outputs.rate_helpers,
            self.deposits.day_counter)

        # assign data to Curve object
        self.outputs.dates = self.outputs.qlibcurve.dates()
        for date in self.outputs.dates:
            self.outputs.discount_factors.append(
                self.outputs.qlibcurve.discount(date))
        self.outputs.pandas_curve = pandas.DataFrame(
            data=self.outputs.discount_factors,
            columns=["DiscountFactors"],
            index=self.outputs.dates)

        return self

# curve date
def set_date():
    curve_month = int(input('Month (MM)?'))
    curve_day = int(input('Day (DD)?'))
    curve_year = int(input('Year (YYYY)?'))
    curve_date = qlib.Date(curve_day, curve_month, curve_year)
    qlib.Settings.instance().evaluationDate = curve_date
    return curve_date

# import data
def filter_curves(all_curves):
    """
    filter_curves takes a list of curves in the curves_to_build
    DataFrame, and returns a filtered list of curves should be built
    (i.e., where there is a True in the True/False column).

    Args:
        all_curves (DataFrame): pandas DataFrame of the
                                'curves_to_build.csv'

    Returns:
        curves (list): list of curve names that should be built (str)
    """
    curves = []
    for curve in all_curves.index.values:
        if all_curves["True/False"][curve] == True:
            curves.append(curve)
    return curves

def import_data():
    datapath = "C://Users//Kevin Keogh//Documents" + \
               "//Coding//PyScripts//CurveBuilder//"
    conventions = pandas.read_csv(datapath + "conventions.csv", index_col=0)
    instruments = pandas.read_csv(datapath + "instruments.csv", index_col=0)
    market_data = pandas.read_csv(datapath + "market_data.csv", index_col=0)
    all_curves = pandas.read_csv(datapath + "curves_to_build.csv", index_col=0)
    curves_to_build = filter_curves(all_curves)
    return conventions, instruments, market_data, curves_to_build

def main():
    #curve_date = set_date()
    curve_date = qlib.Date(31, 12, 2014)
    qlib.Settings.instance().evaluationDate = curve_date
    conventions, instruments, market_data, curves_to_build = import_data()

    for curve in curves_to_build:
        print("Building " + curve + "...")
        curve = Curve(curve,
                      curve_date,
                      conventions,
                      instruments,
                      market_data)
        curve.build()
        print(curve.outputs.pandas_curve)
        curve.outputs.pandas_curve.to_csv("outputs//" + curve.name + ".csv")

if __name__ == "__main__":
    main()
