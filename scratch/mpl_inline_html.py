#!/usr/bin/env python3
"""
Testing matplotlib inline output into html document
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
#import xml.etree.cElementTree as ET

mpl.rc('text', usetex=False)

FN = "mpl_inline_html.html"

fig = plt.figure(figsize=(7,5))
ax = fig.add_subplot(1,1,1)
x = np.arange(1,10,.01)
ax.plot(x, np.sin(x), 'b-.')
fig.tight_layout()

figio = io.BytesIO()
fig.savefig(figio, format="svg", bbox_inches='tight')
figio_str = b'<svg' + figio.getvalue().split(b'<svg')[1]
del figio

with open(FN, 'w') as fh:
    # header boilerplate
    print('<!doctype html>', file=fh)
    print('<html lang="en">', file=fh)
    print('<head>', file=fh)
    print('  <meta charset="utf-8">', file=fh)
    print('  <title>TEST</title>', file=fh)
    print('</head>', file=fh)
    print('<body>', file=fh)
    # main body
    print('<h3>A figure</h3>', file=fh)
    print('<p>text', file=fh)
    print('<div style="background-color:#cccccc">', file=fh)
    
with open(FN, 'ab') as fh:
    fh.write(figio_str)

with open(FN, 'a') as fh:
    print('</div>', file=fh)
    print('<p>Some text below the figure', file=fh)
    # end boilerplate
    print('</body>', file=fh)
    print('</html>', file=fh)
