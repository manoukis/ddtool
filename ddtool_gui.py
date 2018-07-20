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
import subprocess

import numpy as np
import pandas as pd

import matplotlib as mpl
mpl.use('TkAgg')
import matplotlib.pyplot as plt

import tkinter as tk
from tkinter import ttk
import tkinter.filedialog

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
# temperatures_file: testfiles/LAAR_CountryClub2000-2018_Temps.xlsx

# station: Country Club
# start_date: 2018-01-01

# base_temp: 54.3
# DD_per_gen: 622
# num_gen: 3

# min_readings_per_day: 4 # exclude days with too few temperature reads/points
# max_num_years_to_norm: 6
# norm_method: median # use either 'mean' or 'median' for normal/typical temperatures
# num_years_to_add_for_projection: 3
# interpolation_window: 3  # number of points to average on ends of gaps before interpolating

# skiprows: 0
# station_col: STATION
# date_col: DATE
# time_col: TIME
# air_temp_col: TEMP_A_F

# interactive: False
"""

###
def main(argv):
    # parse cfg_file argument and set defaults
    conf_parser = argparse.ArgumentParser(description=__doc__,
                                          add_help=False)  # turn off help so later parse handles it
    inline_default_cfg_file = io.StringIO(INLINE_DEFAULT_CFG_FILE)
    inline_default_cfg_file.name = 'INLINE DEFAULT CONFIG' # needs to have a name for argparse to work with it
    conf_parser.add_argument(dest='cfg_file', nargs='?', type=argparse.FileType('r'),
                             default=inline_default_cfg_file,
                             help="Config file specifiying options/parameters.\n"
                             "Any long option can be set by removing the leading '--' and replacing '-' with '_'")
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
        for k in ['num_gen', # ints
                  'max_num_years_to_norm',
                  'num_years_to_add_for_projection',
                  'min_readings_per_day',
                  'interpolation_window',
                  'skiprows']:
            if k in defaults:
                defaults[k] = int(defaults[k])
        for k in ['base_temp', # floats
                  'DD_per_gen']:
            if k in defaults:
                defaults[k] = float(defaults[k])
        for k in ['interactive']: # booleans
            if k in defaults:
                defaults[k] = defaults[k].lower() in ['true', 'yes', 'y', '1']
        #if( 'files' in defaults ): # files needs to be a list
        #    defaults['files'] = [ x for x in defaults['files'].split('\n')
        #                        if x and x.strip() and not x.strip()[0] in ['#',';'] ]
    else:
        defaults = {}

    if cfg_filename == 'INLINE DEFAULT CONFIG':
        #print("Using default configuration")
        # require a configuration file
        print("Error: Must specify a configuration file", file=sys.stderr)
        sys.exit(2)
    else:
        print("Using configuration file '{}'".format(cfg_filename))

    # parse rest of arguments with a new ArgumentParser
    parser = argparse.ArgumentParser(description=__doc__, parents=[conf_parser])
    parser.add_argument("-f","--temperatures_file", default=None,
            help="File containing the daily min & max temperature data for all sites")
    parser.add_argument("-o","--out-file", default=None,
            help="Filename to output results report to; Default is to ask")
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
    parser.add_argument("--min-readings-per-day", type=int, default=4,
            help="Exclude days with fewer temperature values from min & max calculation")
    parser.add_argument("--max-num-years-to-norm", type=int, default=6,
            help="Maximun number of years to use for normal temperature calculation. "
                "'0' uses all available data")
    parser.add_argument("--norm-method", default="median",
            help="Use either 'mean' or 'median' to calculate normal/typical temperatures for projection")
    parser.add_argument("--num-years-to-add-for-projection", type=int, default=3,
            help="Number of years of normal temperatures to generate for projection")
    parser.add_argument("--interpolation-window", type=int, default=3,
            help="Number of points to average on ends of gaps before interpolating")
    parser.add_argument("--skiprows", type=int, default=0,
            help="Number of initial rows to skip of input temperature data file")
    parser.add_argument("--station-col", default="STATION",
            help="Column heading for station names in data file")
    parser.add_argument("--date-col", default="DATE",
            help="Column heading for dates in data file")
    parser.add_argument("--time-col", default="TIME",
            help="Column heading for time in data file")
    parser.add_argument("--air-temp-col", default="TEMP_A_F",
            help="Column heading for air temperatures in data file")
    parser.add_argument('-i', "--interactive", action='store_true', default=False,
            help="Display interactive plots")
    parser.add_argument('-q', "--quiet", action='count', default=0,
            help="Decrease verbosity")
    parser.add_argument('-v', "--verbose", action='count', default=0,
            help="Increase verbosity")
    parser.add_argument("--verbose_level", type=int, default=0,
            help="Set verbosity level as a number")

    parser.set_defaults(**defaults) # add the defaults read from the config file
    args = parser.parse_args(remaining_argv)
    vars(args).update({'cfg_filename':cfg_filename})

    # test for required arguments/parameters
    for k in ['station',
              'start_date',
              'base_temp',
              'DD_per_gen',
             ]:
        if not k in args or vars(args)[k] is None:
            parser.error("Must specify '{}' parameter".format(k))

    logging.getLogger().setLevel(logging.getLogger().getEffectiveLevel()+
                                 (10*(args.quiet-args.verbose-args.verbose_level)))
    # Startup output
    run_time = time.time()
    logging.info("Started @ {}".format(
                        datetime.fromtimestamp(run_time).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")))
    logging.info("args="+str(args))

    retval = main_process(args)

    # cleanup and exit
    logging.info("Ended @ {}".format(
                        datetime.fromtimestamp(time.time()).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")))
    #input("Press any key to exit")
    return retval


#######


class DDToolFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)

        self.temperatures_file = None

        self.root = parent
        self.root.title("DD Tool")
        self.pack(fill=tk.BOTH, expand=1)

        foo = ttk.Frame(parent)
        foo.pack(anchor=tk.W, padx=10, pady=2)
        self.temperatures_file_label = ttk.Label(foo, text='')
        self.temperatures_file_label.pack(side=tk.LEFT)
        self.default_label_bg = self.temperatures_file_label.cget('background') # only need once
        self.temperatures_file_button = tk.Button(foo, text='Select', command=self._choose_tfile)
        self.temperatures_file_button.pack(side=tk.RIGHT)
        self.default_button_bg = self.temperatures_file_button.cget('bg') # only need once
        self._update_tfile()

        foo = ttk.Frame(parent)
        foo.pack(anchor=tk.W, padx=10, pady=2)
        self.temperatures_file_label = ttk.Label(foo, text='')
        self.temperatures_file_label.pack(side=tk.LEFT)
        self.default_label_bg = self.temperatures_file_label.cget('background') # only need once
        self.temperatures_file_button = tk.Button(foo, text='Select', command=self._choose_tfile)
        self.temperatures_file_button.pack(side=tk.RIGHT)
        self.default_button_bg = self.temperatures_file_button.cget('bg') # only need once
        self._update_tfile()

        self.tktext = tk.Text(master=parent)
        self.tktext.pack(anchor=tk.W, expand=1, fill=tk.BOTH)

        run_button = ttk.Button(parent, text='RUN', command=self._quit)
        run_button.pack(anchor=tk.S, padx=3, pady=3)
        quit_button = ttk.Button(parent, text='Quit', command=self._quit)
        quit_button.pack(anchor=tk.SE, padx=3, pady=3)

    def _quit(self):
        self.root.quit()

    def _choose_tfile(self):
        if self.temperatures_file:
            tmpd, tmpf = os.path.split(self.temperatures_file)
        else:
            tmpd = '.'
            tmpf = None
        tfn = tk.filedialog.askopenfilename(
                title = "Select Temperatures File",
                initialdir=tmpd,
                initialfile=tmpf,
                defaultextension=".xlsx",
                filetypes = (("Excel files",("*.xlsx","*.xls")), ("all files","*.*")))
        if tfn:
            if os.path.isfile(tfn):
                self.temperatures_file = tfn
            else:
                logging.warn("'{}' is not a file... This shouldn't happen".format(tfn))
        self._update_tfile()

    def _update_tfile(self):
        if self.temperatures_file:
            tmptxt = "temperatures file : {}".format(self.temperatures_file)
            self.temperatures_file_label.config(text=tmptxt, background=self.default_label_bg)
            self.temperatures_file_button.config(text="Change", bg=self.default_button_bg)
        else:
            tmptxt = "temperatures file :"
            self.temperatures_file_label.config(text=tmptxt, background='yellow')
            self.temperatures_file_button.config(text="CHOOSE", bg='red')


def main_process(args):
    print("main process")

    tkroot = tk.Tk()
    #root.geometry("800x600")
    app = DDToolFrame(tkroot)

    tkroot.mainloop()
    sys.exit(0)

    #tkroot.withdraw()




    tktext.insert(tk.END, "DDTool:\n\n")
    tktext.insert(tk.END, "Started at {}\n".format(time.strftime("%Y-%m-%d %T %z")))
    tktext.insert(tk.END, "Using configuration file '{}'\n".format(args.cfg_filename))
    tktext.see(tk.END) # scroll if needed
    tkroot.update()


    if args.temperatures_file:
        temperatures_filename = args.temperatures_file
    else:
        temperatures_filename = tk.filedialog.askopenfilename(initialdir=".",
                title = "Select Temperatures File",
                defaultextension=".xlsx",
                filetypes = (("Excel files",("*.xlsx","*.xls")), ("all files","*.*")))
        if not temperatures_filename:
            logging.critical("Select Temperatures File cancled")
            sys.exit(0)

    tktext.insert(tk.END, "Loading temperatures file '{}'\n".format(temperatures_filename))
    tktext.see(tk.END) # scroll if needed
    tkroot.update()
    t, norm_start = load_temperature_data(temperatures_filename, args)

    tktext.insert(tk.END, "Computing thermal accumulation values\n")
    tktext.see(tk.END) # scroll if needed
    tkroot.update()
    dd = compute_BMDD_Fs(t['minAT'], t['maxAT'], args.base_temp)

    ## Plot

    ## Main results figure ... spaehtti-like plot
    fig = plt.figure(figsize=(7,4))
    ax = fig.add_subplot(1,1,1)

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
    max_plot_date = fdate[-1] # track maximum date used
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
        # @TCC -- could distinquish previous years used in normal from older years
        c = 'k'
        if sd < norm_start:
            c = 'k'
        ax.plot((tmp.index-sd).days, tmp, '-', c=c, alpha=0.25, label=lab, zorder=1)
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
    ax.set_ylabel('thermal accumulation [degree-days]')
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.legend()
    fig.tight_layout()

    # save figure to memory (optionally show)
    figio = io.BytesIO()
    fig.savefig(figio, format="svg", bbox_inches='tight')
    main_fig_str = b'<svg' + figio.getvalue().split(b'<svg')[1]
    del figio
    if args.interactive:
        plt.show()

    ## Temperature plot
    t2 = t.loc[norm_start:max_plot_date] # only show values actually used
    fig = plt.figure(figsize=(7,4))
    gs = mpl.gridspec.GridSpec(2, 1, height_ratios=[4,1])

    ax = fig.add_subplot(gs[0,0])
    regions = [['input',        (t2['filled'] == 0) & (t2['normN'] == 0), 'C0'],
               ['interpolated', (t2['filled'] != 0) & (t2['normN'] == 0), 'C1'],
               ['projected',    (t2['normN'] != 0),                       'C2'],
              ]
    for label, mask, color in regions:
        tmp = t2.copy()
        tmp.loc[~mask] = np.nan
        x = np.column_stack((tmp.index, tmp.index+pd.Timedelta(days=1))).flatten()
        ymin = np.column_stack((tmp['minAT'], tmp['minAT'])).flatten()
        ymax = np.column_stack((tmp['maxAT'], tmp['maxAT'])).flatten()
        ax.fill_between(x, ymin, ymax, linewidth=0.5,
                        facecolor=mpl.colors.to_rgba(color, alpha=0.5),
                        edgecolor=mpl.colors.to_rgba(color, alpha=1),
                        label=label)
    ax.axvline(x=pd.to_datetime(start_date), c='k', ls=':', label="start date", alpha=0.5)
    ldg = ax.legend(loc='lower left', ncol=4, bbox_to_anchor=(0,1))
    ax.set_ylabel("temperature")

    ax2 = fig.add_subplot(gs[1,0], sharex=ax)
    ax2.plot(t2.index, t2['cntAT'])
    ax2.set_ylabel("# readings\nper day")
    ax2.set_xlabel("date")
    ax2.set_xlim(left=t2.index[0])
    fig.tight_layout()

    # save figure to memory (optionally show)
    figio = io.BytesIO()
    fig.savefig(figio, format="svg", bbox_extra_artists=(ldg,), bbox_inches='tight')
    t_fig_str = b'<svg' + figio.getvalue().split(b'<svg')[1]
    del figio
    if args.interactive:
        plt.show()

    # computed variables for output
    latest_temp_datetime = t.loc[(t['filled'] == 0) & (t['normN'] == 0)].index[-1]

    # output html
    if not args.out_file:
        tmp = "{} {} {}.html".format(args.station, args.start_date, 
                      datetime.fromtimestamp(time.time()).astimezone().strftime("%Y-%m-%d"))#T%H:%M:%S.%f%z"))
        outfilename = tk.filedialog.asksaveasfilename(initialdir=".",
                title = "Save Report",
                initialfile=tmp,
                defaultextension=".html",
                filetypes = (("html files","*.html"), ("all files","*.*")))
        if not outfilename:
            logging.critical("Save cancled")
            sys.exit(0)
    else:
        outfilename = args.out_file
    if not outfilename:
        logging.error("Cannot save to: '{}'".format(outfilename))
        sys.exit(1)
    logging.info("Saving to: '{}'".format(outfilename))

    # header boilerplate
    with open(outfilename, 'w') as fh:
        tmp = """<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <title>{station} {start_date}</title>
  <style>
	h1, h2, h3, h4, h5, h6{{
		margin-top: .5em;
		margin-bottom: 0em;
	}}
    ul {{ margin-top: .1em; }}
	.pagebreak {{ page-break-before: always; }}
  </style>
</head>
<body>
<h1>Thermal accumulation projections for {station} starting on {start_date}</h1>
<small>Generated at {run_time_str}</small>

<h3> Model </h3>
<ul style='list-style-type:none'>
<li> Single-sine degree day
<li> Base Temperature : {base_temp}
<li> Degree-days per generation : {DD_per_gen}
</ul>

<h3> Temperature data available </h3>
<ul style='list-style-type:none'>
<li> Station : {station}
<li> Lastest temperatre date : {latest_temp_date}
<li> Earliest temperature date : {earliest_temp_date}
<li> Normal temeperatures calcuated using : {norm_start} to {latest_temp_date}
<li> Input filename : {temperatures_filename}
</ul>

<h3> Results </h3>
<ul style='list-style-type:none'>
<li> start : {start_date}
""".format(station=args.station,
           start_date=args.start_date,
           run_time_str=datetime.fromtimestamp(time.time()).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z"),
           base_temp=args.base_temp,
           DD_per_gen=args.DD_per_gen,
           latest_temp_date=latest_temp_datetime.date(),
           earliest_temp_date=t.index[0].date(),
           norm_start=norm_start.date(),
           temperatures_filename=temperatures_filename)
        print(tmp, file=fh)
        for i in range(len(fdate)-1):
            print("<li> generation {} : {}  ({} days past start)".format(i+1,
                    fdate[i+1].date(), (fdate[i+1]-fdate[0]).days), file=fh)
            if fdate[i+1] <= latest_temp_datetime:
                print("<span style='color:green'> passed </span>", file=fh)
            else:
                print("<span style='color:red'> projection </span>", file=fh)
        print("</ul>", file=fh)

    with open(outfilename, 'ab') as fh:
        fh.write(main_fig_str)

    with open(outfilename, 'a') as fh:
        print("<div class='pagebreak'></div>", file=fh)
        print("<h3>Temperature values used for normals and current projection</h3>", file=fh)
    with open(outfilename, 'ab') as fh:
        fh.write(t_fig_str)

    with open(outfilename, 'a') as fh:
        tmp = """
<h3> Configuration used </h3>
configuration filename : {cfg_filename}

<pre style="white-space: pre-wrap;">
temperatures_file: {temperatures_filename}
station: {station}
start_date: {start_date}

base_temp: {base_temp}
DD_per_gen: {DD_per_gen}
num_gen: {num_gen}

min_readings_per_day: {min_readings_per_day}
max_num_years_to_norm: {max_num_years_to_norm}
norm_method: {norm_method}
num_years_to_add_for_projection: {num_years_to_add_for_projection}

skiprows: {skiprows}
station_col: {station_col}
date_col: {date_col}
time_col: {time_col}
air_temp_col: {air_temp_col}

out_file: {outfilename}
interactive: {interactive}
</pre>
</body>
</html>""".format(temperatures_filename=temperatures_filename,
                    outfilename=outfilename,
                    **vars(args))
        print(tmp, file=fh)


    # open file
    if sys.platform=='win32':
        os.startfile(outfilename)
    elif sys.platform=='darwin':
        subprocess.Popen(['open', outfilename])
    else:
        try:
            subprocess.Popen(['xdg-open', outfilename])
        except OSError:
            logging.warn("Cannot figure out how to open the report file")

    # done
    return 0


def load_temperature_data(fn, args):
    #fn = args.temperatures_file
    station = args.station
    interp_window = args.interpolation_window
    max_num_years_to_norm = args.max_num_years_to_norm
    norm_method = args.norm_method.lower().strip()
    num_years_to_add_for_projection = args.num_years_to_add_for_projection
    skiprows = args.skiprows
    station_col = args.station_col
    date_col = args.date_col
    time_col = args.time_col
    air_temp_col = args.air_temp_col
    min_readings_per_day = args.min_readings_per_day

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
    gb = df.groupby(df['date'].rename('foo'))['AT']
    mmdf = gb.count().to_frame()
    mmdf.columns = ['cntAT']
    print(mmdf.head())
    mmdf['minAT'] = gb.min()
    mmdf['maxAT'] = gb.max()
    mmdf.loc[mmdf['cntAT'] < min_readings_per_day, ['minAT','maxAT']] = np.nan
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
    gb = tmp.groupby([tmp.index.month.rename('_month'), tmp.index.day.rename('_day')])
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
        tmp.index = idx
        if lnorm is None:
            lnorm = tmp
        else:
            lnorm = pd.concat((lnorm, tmp), axis=0)
        lnorm.resample('D').mean()
        lnorm.interpolate(method='linear') # fill in any 02-29
    t = pd.concat((t, lnorm.loc[t.index[-1]+pd.DateOffset(days=1):
                                t.index[-1]+pd.DateOffset(years=num_years_to_add_for_projection)]))
    return t, norm_start


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
