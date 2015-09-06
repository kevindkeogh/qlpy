import QuantLib as qlib
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import qlibpy


qlib.Settings.instance().evaluationDate = qlib.Date(31,12,2014)
today = qlib.Date(31, 12, 2014)
usd = qlibpy.LiborCurve('USD_3M', today)

usd.export()