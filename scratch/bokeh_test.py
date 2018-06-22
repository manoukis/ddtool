#!/usr/bin/env python3

import sys
import os

import numpy as np
import pandas as pd

from bokeh.util.browser import view
from bokeh.document import Document
from bokeh.embed import file_html
from bokeh.layouts import gridplot
from bokeh.models.glyphs import Circle, Line
from bokeh.models import ColumnDataSource, Grid, LinearAxis, Plot, Range1d
from bokeh.resources import INLINE

from bokeh.plotting import figure
from bokeh.sampledata.iris import flowers

colormap = {'setosa': 'red', 'versicolor': 'green', 'virginica': 'blue'}
colors = [colormap[x] for x in flowers['species']]

p = figure(title = "Iris Morphology")
p.xaxis.axis_label = 'Petal Length'
p.yaxis.axis_label = 'Petal Width'

p.circle(flowers["petal_length"], flowers["petal_width"],
         color=colors, fill_alpha=0.2, size=10)

doc = Document()
doc.add_root(p)

if __name__ == "__main__":
    doc.validate()
    filename = "bokeh_test.html"
    with open(filename, "w") as f:
        f.write(file_html(doc, INLINE, "Bokeh Test"))
    print("Wrote %s" % filename)
    view(filename)