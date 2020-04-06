# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 11:37:04 2019

@author: y1064
"""

import sys
sys.path.append(r'E:/Gitlab/pythonsharedfunctions.git')
import pandas as pd
from collections import defaultdict, Counter
import lib_file
from lib_timetable import Timetable, FlightTimetable
import lib_grid
import lib_graph
import lib_plot
import networkx as nx
from shapely.geometry import Point
import geopandas as gpd
import geoplot as gplt
import lib_geo
import geoplot.crs as gcrs
import numpy as np
import lib_time

#### 1. 加载第0步已经做好的数据 （HSR:50km, Airport:150km）
G_AirGrids = lib_graph.createG_fromFile('graph_GridAir.csv', source='source', target='target', attr='')
G_HSRGrids = lib_graph.createG_fromFile('graph_GridHSR.csv', source='source', target='target', attr='')
#### 1.1 加载机场、车站位置数据
dict_AirportLocs = lib_file.pickle_load('dict_AirportLocs.pkl')
dict_HSRLocs = lib_file.pickle_load('dict_HSRLocs.pkl')

#### 2 由时刻表建图，获取联通关系 ## 属性上有车次
##### 2.1 飞机时刻表建图

air_timetable = FlightTimetable()
air_timetable.load_file('E:/Code/Data/ChinaAir/China_Air_Schedule_clean.csv')
G_airTimetable = air_timetable.get_graph()

##### 2.2 高铁时刻表  ### 建图，属性上有车次
timetable = Timetable()
timetable.load_file('E:/Code/Data/ChinaRailway/China_Railway_Schedule_20190701.csv')
G_HSRTimetable = timetable.get_graph()

#### 2.3 去掉时刻表中没有位置的点
for n in list(G_airTimetable.nodes()):
    if n not in dict_AirportLocs:
        G_airTimetable.remove_node(n)

for n in list(G_HSRTimetable.nodes()):
    if n not in dict_HSRLocs:
        G_HSRTimetable.remove_node(n)


ttt = lib_time.MeasureT()
#G_HSRTimetable = G_airTimetable ####################
#G_HSRGrids = G_AirGrids ############################
#dict_HSRLocs = dict_AirportLocs   ############################

### 3 选一个北京首都机场的格点
#point = dict_AirportLocs['PEK']
i = 0
for name in dict_HSRLocs:
#    if i<0.29*len(dict_HSRLocs):
#        i+=1
#        continue
    point = dict_HSRLocs[name]
    point = lib_grid.get_nearestGrid(point, 1/16)
    ### 4. 取出该点直接可访问的机场、车站
    first_order_HSR = list(nx.neighbors(G_HSRGrids,str(point)))  # 50千米
    #first_order_Airport = list(nx.neighbors(G_AirGrids,str(point)))  # 50千米  # 150千米
    ### 5.1 计算二阶可访问的机场、车站  (暂时只有高铁站)
    ####### 起点无需记录，记录终点站：所有车次
    #first_order_HSR = first_order_Airport #######################
    
    second_order_HSR = []
    dict_second_order_HSR_Trains = {}
    for hsr in first_order_HSR:
        hsr_d = set(nx.neighbors(G_HSRTimetable,hsr))-set(first_order_HSR) ## 计算每一个一阶可访问的车站的邻居车站
        for d in hsr_d:
            dict_second_order_HSR_Trains[d] = set(G_HSRTimetable[hsr][d].keys())  ### 两站之间所有的车次
        
    ### 5.2 计算二阶可访问的区域
    #G_areaTrains = nx.Graph() ### （起点的）二阶可接近区域 与 可用车次 的映射
    dict_areaTrains = defaultdict(set)  ### 没用图，格点-->火车 的单向映射
    for hsr in dict_second_order_HSR_Trains:
        trains = dict_second_order_HSR_Trains[hsr] ## 到达该目的车站可用的车次
        area = [ eval(p) for p in nx.neighbors(G_HSRGrids,hsr)]  ### 目的地和可用车次之间还用 图 来传吗？？？
        for p in area:
            dict_areaTrains[p] =dict_areaTrains[p] | set(trains)
        #for t in trains:
        #    for p in area:
        #        G_areaTrains.add_edge(t,p)
    
    ##second_order_Airport = []
    ##for air in first_order_Airport:
    ##    second_order_Airport+= list(nx.neighbors(G_airTimetable,air))
    ##second_order_Airport = list(set(second_order_Airport))
    #
    
    # 画二阶可访问车站
    #out = []
    #for p in dict_second_order_HSR_Trains:
    #    out.append([len(dict_second_order_HSR_Trains[p]),Point(dict_HSRLocs[p])])
    #gdf = gpd.GeoDataFrame(out,columns=['value','geometry'])
    #
    #gdf_shp =  lib_geo.readSHP2gdf('E:/Code/Data/gadm36_CHN_shp/gadm36_CHN_1.shp')
    #ax = gplt.polyplot(gdf_shp, projection=gcrs.AlbersEqualArea())
    #gplt.pointplot(gdf,hue='value', legend=True,k=5,s=40)  
    
    ## 画二阶可访问区域
    #out = []
    #for p in dict_areaTrains:
    #    out.append([len(dict_areaTrains[p]),Point(p)])
    #gdf = gpd.GeoDataFrame(out,columns=['value','geometry'])
    #gplt.pointplot(gdf, hue='value', legend=True,k=5,s=0.02)
    minx,maxx,miny,maxy = (73.4997347, 134.7754563, 17.7, 53.560815399999996)
    r = 1/16
    minx = round(minx/r+0.5*r)*r
    miny = round(miny/r+0.5*r)*r
    maxx = round(maxx/r+0.5*r)*r
    maxy = round(maxy/r+0.5*r)*r
    
    data = np.zeros([int((maxx-minx)/r),int((maxy-miny)/r)])
    for p in dict_areaTrains:
        ix = int((p[0]-minx)/r)
        iy = int((p[1]-miny)/r)
        data[ix][iy] = len(dict_areaTrains[p])
    
    implot = lib_plot.ImPlot('E:/Gitlab/pythonsharedfunctions.git/China.png')
    implot.load_array(data.T, extent=[minx,maxx,miny,maxy])
    implot.imshow(fpath='figures/'+name)    

    lib_time.progress_bar(i+1,len(dict_HSRLocs))
    i+=1
    #break
ttt.duration()