#!/usr/bin/env python3
"""
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

import matplotlib as mpl
import matplotlib.pyplot as plt

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
# test configuration file

#temperatures_file: testfiles/Temp_20001.xlsx
temperatures_file: testfiles/LAAR_CountryClub2000-2018_Temps.xlsx

station: Country Club
start_date: 2018-01-01

base_temp: 54.3
DD_per_gen: 622
num_gen: 3

min_points_per_day: 4 # exclude days with too few temperature reads/points
max_num_years_to_norm: 6
norm_method: median # use either 'mean' or 'median' for normal/typical temperatures
num_years_to_add_for_projection: 2

skiprows: 0
station_col: STATION
date_col: DATE
time_col: TIME
air_temp_col: TEMP_A_F

#date_col: Date
#min_air_temp_col: MinOfTEMP_A_F
#max_air_temp_col: MaxOfTEMP_A_F

"""

###
def main(argv):
    # parse cfg_file argument and set defaults
    conf_parser = argparse.ArgumentParser(description=__doc__,
                                          add_help=False)  # turn off help so later parse handles it
    inline_default_cfg_file = io.StringIO(INLINE_DEFAULT_CFG_FILE)
    inline_default_cfg_file.name = 'inline_default_cfg_file' # needs to have a name for argparse to work with it
    conf_parser.add_argument(dest='cfg_file', nargs='?', type=argparse.FileType('r'),
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
        for k in ['num_gen',
                  'max_num_years_to_norm',
                  'num_years_to_add_for_projection',
                  'min_points_per_day',
                  'skiprows']:
            if k in defaults:
                defaults[k] = int(defaults[k])
        for k in ['base_temp',
                  'DD_per_gen']:
            if k in defaults:
                defaults[k] = float(defaults[k])
        #defaults['overwrite'] = defaults['overwrite'].lower() in ['true', 'yes', 'y', '1']
        #if( 'files' in defaults ): # files needs to be a list
        #    defaults['files'] = [ x for x in defaults['files'].split('\n')
        #                        if x and x.strip() and not x.strip()[0] in ['#',';'] ]
    else:
        defaults = {}

    if cfg_filename == 'inline_default_cfg_file':
        print("Using default configuration")
    else:
        print("Using configuration file '{}'".format(cfg_filename))

    # parse rest of arguments with a new ArgumentParser
    parser = argparse.ArgumentParser(description=__doc__, parents=[conf_parser])
    parser.add_argument("-f","--temperatures_file", default=None,
            help="File containing the daily min & max temperature data for all sites")
    parser.add_argument("-s","--station", default=None,
            help="Name of temperature station")
    parser.add_argument("--start-date", type=str, default=None,
            help="Date (YYYY-MM-DD) to begin degree-day accumulation calculation")
    parser.add_argument("--base-temp", type=float, default=None,
            help="Base tempertaure threshold for degree-day computation")
    parser.add_argument("--DD-per-gen", type=float, default=None,
            help="Degree-days required for one generation of development")
    parser.add_argument("--num-gen", type=int, default=3,
            help="Number of generations of development to model")
    parser.add_argument("--min-points-per-day", type=int, default=4,
            help="Exclude days with fewer temperature values from min & max calculation")
    parser.add_argument("--max-num-years-to-norm", type=int, default=0,
            help="Maximun number of years to use for normal temperature calculation. "
                "Default (0) uses all available data")
    parser.add_argument("--num-years-to-add-for-projection", type=int, default=3,
            help="Number of years of normal temperatures to generate for projection")
    parser.add_argument("--skiprows", type=int, default=1,
            help="Number of initial rows to skip of input temperature data file")
    parser.add_argument("--station-col", default="STATION",
            help="Column heading for station names in data file")
    parser.add_argument("--date-col", default="DATE",
            help="Column heading for dates in data file")
    parser.add_argument("--time-col", default="TIME",
            help="Column heading for time in data file")
    parser.add_argument("--air-temp-col", default="TEMP_A_F",
            help="Column heading for air temperatures in data file")
    parser.add_argument('-q', "--quiet", action='count', default=0,
            help="Decrease verbosity")
    parser.add_argument('-v', "--verbose", action='count', default=0,
            help="Increase verbosity")
    parser.add_argument("--verbose_level", type=int, default=0,
            help="Set verbosity level as a number")

    parser.set_defaults(**defaults) # add the defaults read from the config file
    args = parser.parse_args(remaining_argv)

    if not args.station:
        parser.error("Must provide a station name")
    if not args.start_date:
        parser.error("Must provide a start-date")

    logging.getLogger().setLevel(logging.getLogger().getEffectiveLevel()+
                                 (10*(args.quiet-args.verbose-args.verbose_level)))
    # Startup output
    start_time = time.time()
    logging.info("Started @ {}".format(
                        datetime.fromtimestamp(time.time()).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")))
    logging.info("args="+str(args))

    retval = main_process(args)

    # cleanup and exit
    logging.info("Ended @ {}".format(
                        datetime.fromtimestamp(time.time()).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")))
    #input("Press any key to exit")
    return retval


#######

def main_process(args):
    print("main process")
    t = load_temperature_data(args)

    dd = compute_BMDD_Fs(t['minAT'], t['maxAT'], args.base_temp)

    ## Plot
    if True:
        fig = plt.figure(figsize=(10,9))
        ax = fig.add_subplot(3,1,1)
        ax.fill_between(t.index, t['minAT'], t['maxAT'], facecolor='k', edgecolor='none', alpha=0.25)
        tmp = t.loc[(t['filled'] == 0) & (t['normN'] == 0)]
        ax.plot(tmp.index, tmp['minAT'], ls='none', marker='.', label='input', color='C0')
        ax.plot(tmp.index, tmp['maxAT'], ls='none', marker='.', label='', color='C0')
        tmp = t.loc[(t['filled'] > 0) & (t['normN'] == 0)]
        ax.plot(tmp.index, tmp['minAT'], ls='none', marker='.', label='interpolated', color='C1')
        ax.plot(tmp.index, tmp['maxAT'], ls='none', marker='.', label='', color='C1')
        tmp = t.loc[t['normN'] > 0]
        ax.plot(tmp.index, tmp['minAT'], ls='none', marker='.', label='projected', color='C2')
        ax.plot(tmp.index, tmp['maxAT'], ls='none', marker='.', label='', color='C2')
        #ax.plot(df['datetime'], df['AT'], ls='-', marker='.', label='', color='C3', alpha=0.5)
        ax.legend(loc='upper right')
        ax2 = fig.add_subplot(3,1,2, sharex=ax)
        ax2.plot(t.index, t['cntAT'])

        ## Main results figure ... spaehtti-like plot
        ax = fig.add_subplot(3,1,3)

        start_date = args.start_date
        DD_per_gen = args.DD_per_gen
        num_gen = args.num_gen

        cDD = dd['DD'].cumsum(skipna=False)
        start_dt = pd.to_datetime(start_date)
        proj_start_dt = t[t['normN'] > 0].index[0] # first day of projection based on normals

        # compute generation dates
        startcDD = cDD.loc[start_date]
        fdate = np.empty([num_gen+1], dtype=type(start_dt))
        fdate[0] = start_dt
        tmp = cDD-startcDD
        for gen in range(1,num_gen+1):
            fdate[gen] = cDD[tmp>DD_per_gen*gen].index[0]
        print(fdate)

        # previous years
        lab = 'previous years'
        for yr in np.arange(dd.index[0].year, start_dt.year):
            sd = start_dt.replace(year=yr)
            if not sd in dd.index:
                print("No data for year {}; skipping".format(yr))
                continue
            tmp = cDD-cDD.loc[sd]
            tmp = tmp.loc[sd:tmp[tmp>DD_per_gen*num_gen].index[0]]
            ax.plot((tmp.index-sd).days, tmp, '-', c='k', alpha=0.25, label=lab, zorder=1)
            lab = '' # only label first line

        # from the given start_date
        tmp = (cDD-startcDD).loc[fdate[0]:fdate[-1]]
        proj_mask = tmp.index >= proj_start_dt
        ax.plot((tmp[~proj_mask].index-start_dt).days, tmp[~proj_mask],
                '-', c='b', lw=2, label=str(start_dt.date()))
        ax.plot((tmp[proj_mask].index-start_dt).days, tmp[proj_mask],
                '-', c='r', lw=2, label=str(start_dt.date())+" projection")

        trans = mpl.transforms.blended_transform_factory(ax.transAxes, ax.transData)
        trans2 = mpl.transforms.blended_transform_factory(ax.transData, ax.transAxes)
        for i in range(num_gen):
            y = DD_per_gen*(i+1)
            ax.axhline(y=y, c='k', ls=':', alpha=0.5, lw=1)
            ax.text(0, y, ' F{:d}'.format(i+1), transform=trans, ha='left', va='bottom')
            x = (fdate[i+1]-fdate[0]).days
            ax.stem([x], [y], linefmt='k:', markerfmt='none')
            ax.text(x, 0, '{:d}'.format(int(x)), transform=trans2, ha='left', va='bottom')

        # xlabel in days and MM-DD dates
        def foo_formatter(x, pos):
            tmp = start_dt+pd.Timedelta(days=x)
            return "{:d}\n{:02d}-{:02d}".format(int(x), tmp.month, tmp.day)
        ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(foo_formatter))

        ax.set_xlabel('days after last fly detection / date (MM-DD)')
        ax.set_ylabel('thermal accumulation [DD]')
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.legend()

        fig.tight_layout()
        plt.show()


    if False:
        fig = plt.figure(figsize=(10,12))
        ax = fig.add_subplot(3,1,1)
        #ax.fill_between(t.index, t['minAT'], t['maxAT'], facecolor='k', edgecolor='none', alpha=0.25)

        t1 = t.copy(deep=True)
        t1 = t1.loc[t1['normN'] == 0]


        ax.fill_between(tmp.index, tmp['minAT'], tmp['maxAT'], where=tmp['filled']==0,
                        step='post', facecolor='C0', edgecolor='C0', alpha=0.25)
        ax.fill_between(tmp.index, tmp['minAT'], tmp['maxAT'], where=tmp['filled']!=0,
                        step='post', facecolor='C1', edgecolor='C1', alpha=0.25)
        print(t.loc['2017-07-06'])
        print(tmp.loc['2017-07-06'])
        print(t.loc['2017-07-07'])
        print(tmp.loc['2017-07-07'])

        #tmp = t.copy(deep=True)
        #tmp.loc[(tmp['filled'] == 0) | (tmp['normN'] != 0)] = np.nan
        #ax.fill_between(tmp.index, tmp['minAT'], tmp['maxAT'],
        #                step='pre', facecolor='C1', edgecolor='C1', alpha=0.25)

        #ax.plot(tmp.index, tmp['minAT'], ls='none', marker='.', label='input', color='C0')
        #ax.plot(tmp.index, tmp['maxAT'], ls='none', marker='.', label='', color='C0')
        #tmp = t.loc[(t['filled'] > 0) & (t['normN'] == 0)]
        #ax.plot(tmp.index, tmp['minAT'], ls='none', marker='.', label='interpolated', color='C1')
        #ax.plot(tmp.index, tmp['maxAT'], ls='none', marker='.', label='', color='C1')
        #tmp = t.loc[t['normN'] > 0]
        #ax.plot(tmp.index, tmp['minAT'], ls='none', marker='.', label='projected', color='C2')
        #ax.plot(tmp.index, tmp['maxAT'], ls='none', marker='.', label='', color='C2')
        ax.legend(loc='upper right')
        ax2 = fig.add_subplot(3,1,2, sharex=ax)
        ax2.plot(t.index, t['normN'])
        ax3 = fig.add_subplot(3,1,3, sharex=ax)
        ax3.plot(t.index, t['filled'])
        plt.show()


def load_temperature_data(args):
    fn = args.temperatures_file
    station = args.station
    interp_window = 3
    max_num_years_to_norm = args.max_num_years_to_norm
    norm_method = args.norm_method.lower().strip()
    num_years_to_add_for_projection = args.num_years_to_add_for_projection
    skiprows = args.skiprows
    station_col = args.station_col
    date_col = args.date_col
    time_col = args.time_col
    air_temp_col = args.air_temp_col
    min_points_per_day = args.min_points_per_day

    df = pd.read_excel(fn, skiprows=skiprows)#, parse_dates=[[date_col, time_col]])
    if df is None:
        logging.critical("Failed to load temperatures file '{}'".format(fn))
        return 1
    df.rename(columns={date_col:'date',
                       time_col:'time',
                       station_col:'station',
                       air_temp_col:'AT'}, inplace=True)
    df = df.loc[df['station'] == station]
    df['datetime'] = df.apply(lambda r : pd.datetime.combine(r['date'],r['time']),1)
    print(df.head())

    # min and max AT
    gb = df[['date','AT']].groupby('date')
    mmdf = gb.count()
    mmdf.columns = ['cntAT']
    mmdf['minAT'] = gb.min()
    mmdf['maxAT'] = gb.max()
    mmdf.loc[mmdf['cntAT'] < min_points_per_day, ['minAT','maxAT']] = np.nan
    mmdf = mmdf.resample('D').mean() # ensure daily frequency
    del df
    print("Total days:", mmdf.shape[0])

    ## fill missing data with interpolation ##
    missing_days = mmdf.index[mmdf.isnull().any(axis=1)]
    print("Missing days:", len(missing_days), missing_days)
    if interp_window <= 1: # simple linear interpolation
        t = mmdf.interpolate(method='linear')
    else: # interpolation based on smoothed / rolling mean values
        t = mmdf.copy()
        rt = t.rolling(interp_window, center=True).mean().interpolate(method='linear')
        t.loc[missing_days] = rt.loc[missing_days]
        t = t.interpolate(method='linear') # fill in any remaining missing values
    t['filled'] = False
    t.loc[missing_days, 'filled'] = True
    t.loc[missing_days, 'cntAT'] = 0

    ## compute normal temperatures for projection ##
    t['normN'] = 0 # keeps track of number of values used to compute normal projections
    if max_num_years_to_norm > 0:
        norm_start = t.index[-1]-pd.DateOffset(years=max_num_years_to_norm)+pd.DateOffset(days=1)
    else: # use all data
        norm_start = t.index[0]
    if norm_start < t.index[0]:
        logging.warn("Not enough data to compute normal using requested"
                     " {:d} years.".format(max_num_years_to_norm))
        norm_start= t.index[0]
    logging.info("Computing normal using data from {} to {}".format(norm_start, t.index[-1]))
    # actual norm computation
    tmp = t.loc[norm_start:]
    gb = tmp.groupby([tmp.index.month, tmp.index.day])
    if norm_method == 'mean':
        norm = gb.mean()
    elif norm_method == 'median':
        norm = gb.median()
    else:
        logging.critical("norm_method '{}' not understood".format(norm_method))
        return 1
    norm['normN'] = gb.count()['minAT']
    if (2,29) in norm.index: # drop Feb 29 if it is in there
        norm.drop((2,29), inplace=True)
    norm.sort_index(inplace=True)
    # extend data with multiple years of normals
    lnorm = None
    for yr in np.arange(0,num_years_to_add_for_projection+1)+t.index[-1].year:
        idx = pd.date_range(start='{:04d}-{:02d}-{:02d}'.format(yr,*norm.index[0]),
                            end=  '{:04d}-{:02d}-{:02d}'.format(yr,*norm.index[-1]),
                            freq='D')
        if idx.shape[0] == 366: # leapyear
            idx = idx[(idx.month!=2) | (idx.day!=29)]
        tmp = norm.copy()
        print(idx.shape)
        print(tmp.shape)
        tmp.index = idx
        if lnorm is None:
            lnorm = tmp
        else:
            lnorm = pd.concat((lnorm, tmp), axis=0)
        lnorm.resample('D').mean()
        lnorm.interpolate(method='linear') # fill in any 02-29
    t = pd.concat((t, lnorm.loc[t.index[-1]+pd.DateOffset(days=1):
                                t.index[-1]+pd.DateOffset(years=num_years_to_add_for_projection)]))
    return t


# Function which computes BM (single sine method) degree day generation from temperature data
def compute_BMDD_Fs(tmin, tmax, base_temp):
    # Used internally
    def _compute_daily_BM_DD(mint, maxt, avet, base_temp):
        """Use standard Baskerville-Ermin (single sine) degree-day method
        to compute the degree-day values for each a single day.
        """
        if avet is None:
            avet = (mint+maxt)/2.0 # simple midpoint (like in the refs)
        dd = np.nan # value which we're computing
        # Step 1: Adjust for observation time; not relevant
        # Step 2: GDD = 0 if max < base (curve all below base)
        if maxt < base_temp:
            dd = 0
        # Step 3: Calc mean temp for day; already done previously
        # Step 4: min > base; then whole curve counts
        elif mint >= base_temp:
            dd = avet - base_temp
        # Step 5: else use curve minus part below base
        else:
            W = (maxt-mint)/2.0
            tmp = (base_temp-avet) / W
            if tmp < -1:
                print('WARNING: (base_temp-avet)/W = {} : should be [-1:1]'.format(tmp))
                tmp = -1
            if tmp > 1:
                print('WARNING: (base_temp-avet)/W = {} : should be [-1:1]'.format(tmp))
                tmp = 1
            A = np.arcsin(tmp)
            dd = ((W*np.cos(A))-((base_temp-avet)*((np.pi/2.0)-A)))/np.pi
        return dd

    # compute the degree-days for each day in the temperature input (from tmin and tmax vectors)
    dd = pd.concat([tmin,tmax], axis=1)
    dd.columns = ['tmin', 'tmax']
    dd['DD'] = dd.apply(lambda x: _compute_daily_BM_DD(x[0], x[1], (x[0]+x[1])/2.0, base_temp), axis=1)
    return dd



## Main hook for running as script
if __name__ == "__main__":
    sys.exit(main(argv=None))
