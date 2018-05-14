#!/usr/bin/env python3
"""
Convert a set of temperature files with indiviual readings to daily min and max values
"""

import sys
import os
import fcntl
import serial
import minimalmodbus
import time
import configparser
from itertools import chain
import argparse
from datetime import datetime
import dateutil
from threading import Event
from collections import deque
import signal
import logging

import pandas as pd

import especmodbus


# setup logging
def getlvlnum(name):
    return name if isinstance(name, int) else logging.getLevelName(name)
def getlvlname(num):
    return num if isinstance(num, str) else logging.getLevelName(num)
logging.basicConfig()
logging.getLogger().setLevel(logging.WARNING)


## CONSTANTS ##
DEFAULT_CONFIG_FILE = "test_temps2daily.cfg"


###
def main(argv):
    # parse cfg_file argument and set defaults
    conf_parser = argparse.ArgumentParser(description=__doc__,
                                          add_help=False)  # turn off help so later parse (with all opts) handles it
    conf_parser.add_argument('-c', '--cfg-file', type=argparse.FileType('r'), default=DEFAULT_CONFIG_FILE,
                             help="Config file specifiying options/parameters.\nAny long option can be set by remove the leading '--' and replace '-' with '_'")
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
        #if( 'bam_files' in defaults ): # bam_files needs to be a list
        #    defaults['bam_files'] = [ x for x in defaults['bam_files'].split('\n') if x and x.strip() and not x.strip()[0] in ['#',';'] ]
    else:
        defaults = {}

    # parse rest of arguments with a new ArgumentParser
    parser = argparse.ArgumentParser(description=__doc__, parents=[conf_parser])
    parser.add_argument('-i', "--in", default=None,
            help="Filename of main (time, temperature) csv file")
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
    if args.file is None:
        print("ERROR: -f/--input-file must be set", file=sys.stderr)
        sys.exit(1)

    # Startup output
    start_time = time.time()
    logging.info("Started @ {}".format(
                        datetime.fromtimestamp(time.time()).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z"))
    logging.info(args)

    return_value = main_process(args)

    # cleanup and exit
    logging.info("Ended @ {}".format(
                        datetime.fromtimestamp(time.time()).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z"))
    return return_value


#######
def main_process(args):
    print("main process")
    return 0



## Main hook for running as script
if __name__ == "__main__":
    sys.exit(main(argv=None))
