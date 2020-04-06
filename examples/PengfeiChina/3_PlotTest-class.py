# -*- coding: utf-8 -*-
"""
Created on Fri Sep 13 16:06:52 2019

@author: y1064
"""

import sys
sys.path.append(r'E:/Gitlab/pythonsharedfunctions.git')
import lib_plot
import pandas as pd
import numpy as np

implot = lib_plot.ImPlot('China.png')

dfprovinces=pd.read_csv("Provinces.csv.gz")
dfHighlight=dfprovinces[(dfprovinces["name"]=="Beijing")]
for row in dfHighlight.itertuples():        
    lonsL=eval(row.lons)
    latsL=eval(row.lats)
    implot.load_polygon(lonsL,latsL)

data=np.array([[0.8, 2.4, 2.5, 3.9, 0.0, 4.0, 0.0],
                [2.4, 0.0, 4.0, 1.0, 2.7, 0.0, 0.0],
                [1.1, 2.4, 0.8, 4.3, 1.9, 4.4, 0.0],
                [0.6, 0.0, 0.3, 0.0, 3.1, 0.0, 0.0],
                [0.7, 1.7, 0.6, 2.6, 2.2, 6.2, 0.0],
                [1.3, 1.2, 0.0, 0.0, 0.0, 3.2, 5.1],
                [0.1, 2.0, 0.0, 1.4, 0.0, 1.9, 6.3]])

implot.load_array(data, extent=[90,120,30,45])

implot.imshow()