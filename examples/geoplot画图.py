# -*- coding: utf-8 -*-
"""
geoplot库(https://residentmario.github.io/geoplot/quickstart/quickstart.html)的相关练习    
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString

import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
from collections import defaultdict 
import geoplot as gplt

####### 画城市人口、密度图
gdf = gpd.read_file('E:/pythonlibs/populations.shp')

(fx, fy) = (900, 600)
my_dpi = 100
fig = plt.figure(figsize=(fx / my_dpi, fy / my_dpi), dpi=my_dpi)
ax = fig.add_subplot(1,1,1)

gplt.choropleth(gdf, 
    ax=ax, hue='density', #projection=gcrs.AlbersEqualArea(),
    edgecolor='black', linewidth=0.2,
    #cmap='Greens',
    legend=True,
    #scheme='fisherjenks',
#    legend_labels=[
#        '<1.5 million', '1.5-2.6 million', '2.6-3.9 million',
#        '3.9-5.7 million', '5.7-27.7 million'
#    ]
)