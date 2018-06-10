#!/usr/bin/env python3
"""
Read old CDFA binary temperature files used by COPY13.BAS and output csv
"""

import sys
import os
import time
import argparse
from datetime import datetime
from datetime import date as datetimedate
# import dateutil
import logging
import io
import glob
import struct
import tkinter as tk
from tkinter.filedialog import askopenfilenames, asksaveasfilename

# import numpy as np
# import pandas as pd

# setup logging
def getlvlnum(name):
    return name if isinstance(name, int) else logging.getLevelName(name)
def getlvlname(num):
    return num if isinstance(num, str) else logging.getLevelName(num)
logging.basicConfig(format='%(levelname)s:%(message)s')
logging.getLogger().setLevel(logging.INFO)


###

def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(dest='files', nargs='*', default=[],
            help="Filename(s) of MBF format (COPY13.BAS generated) temepratures")
    parser.add_argument("-o", "--outfilename", default=None,
            help="Name of the file to output.  Defaults to asking.")
    parser.add_argument("-d", "--delim", default=',', help="Field delimiter for output")
    parser.add_argument('-q', "--quiet", action='count', default=0,
            help="Decrease verbosity")
    parser.add_argument('-v', "--verbose", action='count', default=0,
            help="Increase verbosity")
    parser.add_argument("--verbose_level", type=int, default=0,
            help="Set verbosity level as a number")
    args = parser.parse_args()
    
    logging.getLogger().setLevel(logging.getLogger().getEffectiveLevel()+
                                 (10*(args.quiet-args.verbose-args.verbose_level)))

    start_time = time.time()
    logging.info("Started @ {}".format(
                        datetime.fromtimestamp(time.time()).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")))
    logging.info("args="+str(args))

    if not args.files or not args.outfilename:
        root = tk.Tk();
        root.withdraw();
    
    if not args.files:
        args.files = askopenfilenames(title="MBF/OPEN13.BAS format temperature files to open")
    
    files = []
    for f in args.files:
        if os.path.isfile(f):
            files.append(f)
        else:
            tmp = glob.glob(f)
            if not tmp:
                logging.critical("Input '{}' not found".format(f))
                return 1 # exit with error code
            files.extend(tmp)
    if not files:
        logging.critical("No input files found")
        return 1
    
    dat = []
    for f in files:
        logging.info("Input file '{}'".format(f))
        d = load_datfile(f)
        if not d:
            logging.critical("Failed to load file '{}'".format(f))
            return 1
        dat.extend(d)
    # sort?

    if not args.outfilename:
        args.outfilename = asksaveasfilename(defaultextension=".csv", filetypes=[('CSV', ".csv")])
    if not args.outfilename:
        logging.critical("Save canceled")
        return 1
    logging.info("Saving to '{}'".format(args.outfilename))

    with open(args.outfilename, 'w') as fh:
        print("day of year",
              "day",
              "month",
              "year",
              "temperature min",
              "temperature max",
              "date",
              "filename",
              sep=args.delim, file=fh)
        for l in dat:
            print(*l, sep=args.delim, file=fh)
    
        
    logging.info("Ended @ {}".format(
                        datetime.fromtimestamp(time.time()).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")))
    # input("Press any key to exit")
    return 0


#######

def msbin2ieee(msbin):
    """
    Convert an array of 4 bytes containing Microsoft Binary floating point
    number to IEEE floating point format (which is used by Python)
    adapted from: https://github.com/choonkeat/ms2txt/blob/master/metastock/utils.py
    """
    as_int = struct.unpack("i", msbin)
    if not as_int:
        return 0.0
    man = int(struct.unpack('H', msbin[2:])[0])
    if not man:
        return 0.0
    exp = (man & 0xff00) - 0x0200
    man = man & 0x7f | (man << 8) & 0x8000
    man |= exp >> 1
    ieee = msbin[:2]
    ieee += bytes([man & 0xFF])
    ieee += bytes([(man >> 8) & 0xFF])
    return struct.unpack("f", ieee)[0]
    

def load_datfile(fn):
    # BASIC FIELDS: 3 AS N$, 2 AS D$, 2 AS M$, 2 AS Y$, 5 AS M2$, 5 AS M3$, 16 AS X$
    date_fmt = r"=hchhh"
    date_size = struct.calcsize(date_fmt)
    current_year = int(datetime.strftime(datetimedate.today(), '%Y'))
    dat = []
    with open(fn, 'rb') as fh:
        while True:
            date_bytes = fh.read(date_size)
            if len(date_bytes) < date_size:
                if len(date_bytes) > 0:
                    print("WARNING: Some data left in file")
                break
            (n, _, d, m, y) = struct.unpack(date_fmt, date_bytes)
            tmin = msbin2ieee(fh.read(4))
            assert fh.read(1) == b' ' # This byte should be a space (0x20)
            tmax = msbin2ieee(fh.read(4))
            assert fh.read(1) == b' ' # This byte should be a space (0x20)
            fooX = fh.read(16) # specified in old BASIC code but not used.  Don't know what it is
            if y == 0:
                date_str = ""
            else:
                # convert 2 digit year to 4 digits... This will break in 2100
                fully = y+2000
                if fully > current_year:
                    fully -= 100
                date_str = "{:04d}-{:02d}-{:02d}".format(fully, m, d)
            dat.append([n, d, m, y, tmin, tmax, date_str, fn])
            _ = fh.read(128-35) # skip to next record in the file (each record is 128 bytes because??)
        # dat = pd.DataFrame(dat, columns=['jday', 'day', 'month', 'year', 'Tmin', 'Tmax', 'date_str', 'is_projection'])
    # dat['date'] = pd.to_datetime(dat['date_str'])
    # dat.drop('date_str', axis=1, inplace=True)
    return dat


    
# def load_tfile(fn, date_column, temperature_column):
    # df = pd.read_csv(fn, parse_dates=[date_column]).dropna()
    # tcol = [x for x in df.columns if x.startswith(temperature_column)]
    # if len(tcol) < 1:
        # logging.critical("Temperature column starting with '{}' not found".format(temperature_column))
        # return None
    # else:
        # tmp = [x.strip() for x in tcol[0].split(',')]
        # station = tmp[-1]
        # print(tmp, station)
        
        # t = df.loc[:,[date_column,tcol[0]]]
        # t.set_index(date_column, inplace=True)
        # t.columns = ['T']
        # t.sort_index(inplace=True)
        # #t['station'] = station
        # first = t.index[0]
        # last = t.index[-1]
        # print(station, first, last)
    # print(t.shape)
    # print(t.head())
    # return t

## Main hook for running as script
if __name__ == "__main__":
    sys.exit(main(argv=None))
