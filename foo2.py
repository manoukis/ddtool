#!/usr/bin/env python3
"""
Convert a set of temperature files with indiviual readings to daily min and max values
"""

import sys
import os
import time
import configparser
from itertools import chain
import argparse
from datetime import datetime
import dateutil
import logging
import io
import glob

import numpy as np
import pandas as pd

# setup logging
def getlvlnum(name):
    return name if isinstance(name, int) else logging.getLevelName(name)
def getlvlname(num):
    return num if isinstance(num, str) else logging.getLevelName(num)
logging.basicConfig(format='%(levelname)s:%(message)s')
logging.getLogger().setLevel(logging.INFO)


## CONSTANTS ##
# The default configuration (as a string so we don't need an extra file)
INLINE_DEFAULT_CFG_FILE = """
# test configuration file for temps2daily.py

date_column: Date
temperature_column: Temperature
hour_offset: -7

files: a
	b
	c
    d
"""

###
def main(argv):
    # parse cfg_file argument and set defaults
    conf_parser = argparse.ArgumentParser(description=__doc__,
                                          add_help=False)  # turn off help so later parse (with all opts) handles it
    inline_default_cfg_file = io.StringIO(INLINE_DEFAULT_CFG_FILE)
    inline_default_cfg_file.name = 'inline_default_cfg_file' # needs to have a name for argparse to work with it
    conf_parser.add_argument('-c', '--cfg-file', type=argparse.FileType('r'), 
                             default=inline_default_cfg_file,
                             help="Config file specifiying options/parameters.\n"
                             "Any long option can be set by remove the leading '--' and replace '-' with '_'")
    args, remaining_argv = conf_parser.parse_known_args(argv)
    # build the config (read config files)
    cfg_filename = None
    if args.cfg_file:
        cfg_filename = args.cfg_file.name
        cfg = configparser.ConfigParser(inline_comment_prefixes=('#',';'))
        cfg.optionxform = str # make configparser case-sensitive
        cfg.read_file(chain(("[DEFAULTS]",), args.cfg_file))
        defaults = dict(cfg.items("DEFAULTS"))
        # special handling of paratmeters that need it like lists
        #defaults['overwrite'] = defaults['overwrite'].lower() in ['true', 'yes', 'y', '1']
        if( 'files' in defaults ): # files needs to be a list
            defaults['files'] = [ x for x in defaults['files'].split('\n') 
                                if x and x.strip() and not x.strip()[0] in ['#',';'] ]
    else:
        defaults = {}

    # parse rest of arguments with a new ArgumentParser
    parser = argparse.ArgumentParser(description=__doc__, parents=[conf_parser])
    parser.add_argument(dest='files', nargs='*', default=[],
            help="Filenames of (time, temperature) csv files")
    parser.add_argument("--date-column", default="Date",
            help="The label (header) of the column containing date+time in the input files")
    parser.add_argument("--temperature-column", default="Temperature",
            help="The label (header) of the column containing temperature in the input files. "
            "Matches just the first part to accomodate hobo csv files. "
            "NOTE: USES THE FIRST MATCHING COLUMN")
    parser.add_argument("--hour-offset", type=int, default=0,
            help="Offset from times in file to localtime for grouping by day. "
            "Typically timezone offset from UTC; eg: CA is -7. "
            "Ignores daylight-savings")
    parser.add_argument('-q', "--quiet", action='count', default=0,
            help="Decrease verbosity")
    parser.add_argument('-v', "--verbose", action='count', default=0,
            help="Increase verbosity")
    parser.add_argument("--verbose_level", type=int, default=0,
            help="Set verbosity level as a number")

    parser.set_defaults(**defaults) # add the defaults read from the config file
    args = parser.parse_args(remaining_argv)

    logging.getLogger().setLevel(logging.getLogger().getEffectiveLevel()+
                                 (10*(args.quiet-args.verbose-args.verbose_level)))

    # check for required arguments
    if not args.files:
        logging.critical("Must specify input file(s)")
        sys.exit(1)

    # Startup output
    start_time = time.time()
    logging.info("Started @ {}".format(
                        datetime.fromtimestamp(time.time()).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")))
    logging.info("args="+str(args))

    return_value = main_process(args)

    # cleanup and exit
    logging.info("Ended @ {}".format(
                        datetime.fromtimestamp(time.time()).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")))
    # pause so if this is being run as executable, the window doesn't disappear immediately
    input("Press any key to exit")
    return return_value


#######
def main_process(args):
    print("main process")
    
    # check the input files
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
        
    for f in files:
        logging.info("Input file '{}'".format(f))
        df = load_tfile(f, args.date_column, args.temperature_column)
        if df is None:
            logging.critical("Failed to load file '{}'".format(f))
            return 1
#        break
    
    return 0


def load_tfile(fn, date_column, temperature_column):
    df = pd.read_csv(fn, parse_dates=[date_column]).dropna()
    tcol = [x for x in df.columns if x.startswith(temperature_column)]
    if len(tcol) < 1:
        logging.critical("Temperature column starting with '{}' not found".format(temperature_column))
        return None
    else:
        tmp = [x.strip() for x in tcol[0].split(',')]
        station = tmp[-1]
        print(tmp, station)
        
        t = df.loc[:,[date_column,tcol[0]]]
        t.set_index(date_column, inplace=True)
        t.columns = ['T']
        t.sort_index(inplace=True)
        #t['station'] = station
        first = t.index[0]
        last = t.index[-1]
        print(station, first, last)
    print(t.shape)
    print(t.head())
    return t

## Main hook for running as script
if __name__ == "__main__":
    sys.exit(main(argv=None))
