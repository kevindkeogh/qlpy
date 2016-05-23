# qlpy
Library for using QuantLib SWIG bindings for Python.

Users need to install QuantLib and the requisite SWIG bindings for Python in order to use this library.

For example use, please run

```bash
$ python3 main.py
```

This will walk through an example build of the USD 3M LIBOR curve. The script will build a market data sqlite3 database, which can be designed to suit your needs. I plan on implementing more features, particularly calibrating equity/rate volatility surfaces.

Please reach out with any questions.
