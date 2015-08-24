import QuantLib as qlib
"This module contains many functions/classes/etc. that allow financial"
import pandas
"This module does something"

class Curve:

#def __init__(self, curvename, curve_date, conventions, instruments, market_data):

    self.conventions = self.Conventions(curvename, curve_date, conventions)
    self.deposits = self.Deposits(curve, conventions)
    self.futures = self.Futures(curve, conventions)
    self.swaps = self.Swaps(curve, conventions)
    self.curveoutputs = self.Curveoutputs()

    def holiday_calendar(calendar):
        """
        holiday_calendar takes a string that is used in the
        conventions DataFrame, and returns the QuantLib-equivalent calendar
        object. More will need to be added, particularly as more exotic
        curves are able to be built.

        Currently, the function takes the following strings:
        NYSE

        Args:
            calendar (str): string name of calendar

        Returns:
            object: Quantlib calendar object
        """
        if calendar == "NYSE":
            return qlib.UnitedStates(qlib.UnitedStates.NYSE)

    def day_count_fraction(dcf):
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

    def bus_day_convention(adjustment):
        """
        bus_day_convention takes a string that is used in the
        conventions DataFrame, and returns the QuantLib-equivalent business
        day object. This function takes all business day conventions
        that are currently allowed in QuantLib.

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

    def get_instruments(curve, instruments, market_data, filter_string):
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
            first_future_date = qlib.IMM.nextDate(curve.curve_date)
            days_to_first_future = first_future_date - curve.curve_date
            if days_to_first_future > int(curve.futures.days_to_exclude):
                exclude_first = False
            else:
                exclude_first = True
            futures_imm_codes = get_futures_imm_codes(curve, exclude_first)
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
                    market_data[curve.name]
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
                if instruments[curve.name][inst] == True:
                    instruments_included.append(inst)
            # get periods for all instruments
            for inst in instruments_included:
                instruments_periods.append(period_function(inst))
            # get rates for all instruments
            for inst in instruments_included:
                instruments_rates.append(qlib.SimpleQuote(
                    market_data[curve.name][inst]))
            # create list of tuples for instruments
            for i in range(len(instruments_included)):
                data = (instruments_periods[i], instruments_rates[i])
                instruments_output.append(data)
            return instruments_output

    def period_function(string):
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

    def build():

        # create Curve object
        curve = Curve(curve, curve_date, conventions)
        # gather instruments
        curve.deposits.instruments = get_instruments(curve, instruments, market_data, "deposits")
        curve.futures.instruments = get_instruments(curve, conventions, market_data, "futures")
        curve.swaps.instruments = get_instruments(curve, instruments, market_data, "swaps")
        # gather rate helpers
        curve.deposits.rate_helpers = get_deposits_rate_helpers(curve)
        curve.futures.rate_helpers = get_futures_rate_helpers(curve)
        curve.swaps.rate_helpers = get_swaps_rate_helpers(curve)
        # combine rate helpers
        helpers = curve.deposits.rate_helpers + curve.futures.rate_helpers + curve.swaps.rate_helpers
        # build curve
        curve.curveoutputs.qlibcurve = qlib.PiecewiseCubicZero(curve.settlement_date, helpers, curve.deposits.day_counter)

        # assign data to Curve object
        curve.cruveoutputs.dates = curve.curveoutputs.qlibcurve.dates()
        for date in curve.curveoutputs.dates:
          curve.curveoutputs.discount_factors.append(curve.curveoutputs.qlibcurve.discount(date))
        curve.curveoutputs.pandascurve = pandas.DataFrame(data=curve.curveoutputs.discount_factors, columns=["DiscountFactors"], index=curve.outputs.dates)

        return curve

    class Conventions:

        def __init__(self, curvename, curve_date, conventions):

            self.name = curvename
            self.curve_date = curve_date
            self.settlement_date = curve_date + \
                qlib.Period(int(conventions[curvename]["deposits_SpotLag"]), qlib.Days)
            self.calendar = super().holiday_calendar(
                conventions[curvename]["general_HolidayCalendar"])
            self.currency = conventions[curvename]["general_Currency"]

    class Deposits:

        def __init__(self, curve, conventions):

            # conventions
            self.settlement_days = int(
                conventions[curve]["deposits_SpotLag"])
            self.day_counter = day_count_fraction(
                conventions[curve]["deposits_DCF"])
            self.adjustment = bus_day_convention(
                conventions[curve]["deposits_Adjustment"])

            # utilies
            self.instruments = []
            self.rate_helpers = []

        def get_deposits_rate_helpers(curve):
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
            deposits_rate_helpers = [qlib.DepositRateHelper(
                qlib.QuoteHandle(quote),
                date,
                curve.deposits.settlement_days,
                curve.calendar,
                curve.deposits.adjustment,
                False,  # end of month
                curve.deposits.day_counter)
                                     for date, quote in
                                     curve.deposits.instruments]
            return deposits_rate_helpers

    class Futures:

        def __init__(self, curve, conventions):

            # conventions
            self.settlement_days = conventions[curve]["futures_SpotLag"]
            self.day_counter = day_count_fraction(
                conventions[curve]["futures_DCF"])
            self.adjustment = bus_day_convention(
                conventions[curve]["futures_Adjustment"])
            self.months = int(conventions[curve]["futures_Tenor"])
            self.number_of_futures = int(
                conventions[curve]["futures_NumberOfFutures"])
            self.days_to_exclude = int(
                conventions[curve]["futures_DaysToExclude"])

            # utilities
            self.instruments = []
            self.rate_helpers = []

        def get_futures_imm_codes(curve, exclude_first_future):
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
            for future in range(curve.futures.number_of_futures + 1):
                if future == 0:
                    futures_imm_codes.append(qlib.IMM.nextCode(curve.curve_date))
                else:
                    futures_imm_codes.append(
                        qlib.IMM.nextCode(futures_imm_codes[future - 1]))
            if exclude_first_future:
                return futures_imm_codes[1:curve.futures.number_of_futures + 1]
            else:
                return futures_imm_codes[0:curve.futures.number_of_futures]

        # TODO implement convexity adjustment in code
        def get_futures_rate_helpers(curve):
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
            futures_rate_helpers = [qlib.FuturesRateHelper(
                qlib.QuoteHandle(quote),
                date,
                curve.futures.months,
                curve.calendar,
                curve.futures.adjustment,
                False,  # end of month
                curve.futures.day_counter,
                qlib.QuoteHandle(
                    qlib.SimpleQuote(0.0)))
                                    for date, quote in
                                    curve.futures.instruments]
            return futures_rate_helpers

    class Swaps:

        def __init__(self, curve, conventions):

            # conventions
            self.settlement_days = int(conventions[curve]["swaps_SpotLag"])

            # fixed leg conventions
            self.fixed_leg_frequency = swap_freqs(
                conventions[curve]["swaps_FixedFreq"])
            self.fixed_leg_tenor = swap_periods(
                conventions[curve]["swaps_FixedTenor"])
            self.fixed_leg_adjustment = bus_day_convention(
                conventions[curve]["swaps_FixedAdjustment"])
            self.fixed_leg_day_counter = day_count_fraction(
                conventions[curve]["swaps_FixedLegDCF"])

            # floating leg conventions
            self.floating_leg_frequency = swap_freqs(
                conventions[curve]["swaps_FloatFreq"])
            self.floating_leg_tenor = swap_periods(
                conventions[curve]["swaps_FloatTenor"])
            self.floating_leg_adjustment = bus_day_convention(
                conventions[curve]["swaps_FloatAdjustment"])

            # utilities
            self.instruments = []
            self.rate_helpers = []

        def swap_periods(period):
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

        def swap_freqs(freq):
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

        def swap_index(curve):
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
                return qlib.AUDLibor(curve.swaps.floating_leg_tenor)
            elif curve.currency == "CAD":
                return qlib.CADLibor(curve.swaps.floating_leg_tenor)
            elif curve.currency == "CHF":
                return qlib.CHFLibor(curve.swaps.floating_leg_tenor)
            elif curve.currency == "DKK":
                return qlib.DKKLibor(curve.swaps.floating_leg_tenor)
            elif curve.currency == "EUR":
                return qlib.Euribor(curve.swaps.floating_leg_tenor)
            elif curve.currency == "GBP":
                return qlib.GBPLibor(curve.swaps.floating_leg_tenor)
            elif curve.currency == "JPY":
                return qlib.JPYLibor(curve.swaps.floating_leg_tenor)
            elif curve.currency == "NZD":
                return qlib.NZDLibor(curve.swaps.floating_leg_tenor)
            elif curve.currency == "SEK":
                return qlib.SEKLibor(curve.swaps.floating_leg_tenor)
            elif curve.currency == "TRL":
                return qlib.TRLibor(curve.swaps.floating_leg_tenor)
            elif curve.currency == "USD":
                return qlib.USDLibor(curve.swaps.floating_leg_tenor)

        def get_swaps_rate_helpers(curve):
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
            swaps_rate_helpers = [qlib.SwapRateHelper(
                qlib.QuoteHandle(quote),
                date,
                curve.calendar,
                curve.swaps.fixed_leg_frequency,
                curve.swaps.fixed_leg_adjustment,
                curve.swaps.fixed_leg_day_counter,
                swap_index(curve))
                                  for date, quote in curve.swaps.instruments]
            return swaps_rate_helpers

    class Curveoutputs:

        def __init__(self):
            self.qlib_curve = []
            self.pandas_curve = []
            self.dates = []
            self.discount_factors = []




# This is code that I want to work

# curve date
def setDate():
  curveMonth = int(input('Month (MM)?'))
  curveDay = int(input('Day (DD)?'))
  curveYear = int(input('Year (YYYY)?'))
  curve_date = qlib.Date(curveDay,curveMonth,curveYear)
  qlib.Settings.instance().evaluationDate = curve_date
  return curve_date

# import data
def importdata():
  datapath = "C://Users//Kevin Keogh//Documents//Coding//PyScripts//CurveBuilder//"
  conventions = pandas.read_csv(datapath + "conventions.csv", index_col = 0)
  instruments = pandas.read_csv(datapath + "instruments.csv", index_col = 0)
  market_data = pandas.read_csv(datapath + "market_data.csv", index_col = 0)
  allCurves = pandas.read_csv(datapath + "curves_to_build.csv", index_col = 0)
  curves_to_build = Curve.filter_curves(allCurves)
  return conventions, instruments, market_data, curves_to_build

def main():
  #curve_date = setDate()
  curve_date = qlib.Date(31,12,2014)
  qlib.Settings.instance().evaluationDate = curve_date
  conventions, instruments, market_data, curves_to_build = importdata()

  for curve in curves_to_build:
    print("Building " + curve + "...")
    curve = Curve(curve, curve_date, conventions, instruments, market_data)
    curve.build()
#    curve.outputs.pandascurve.to_csv("outputs//" + curve.name + ".csv")

if __name__ == "__main__":
  main()

