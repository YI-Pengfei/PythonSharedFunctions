#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2019.09.20 core code is: nx.shortest_path_length()

Based on car dring time (<=3h) from stations, 
calculate the shortest travel time from grid to grid,
car-->hsr(could transfer)-->car

@author: pengfei
"""

import sys
sys.path.append(r'/run/media/pengfei/OTHERS/Gitlab/pythonsharedfunctions.git')
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
import multiprocessing
import random
import matplotlib.pyplot as plt
##### 1.1 高铁车站的位置
dict_HSRLocs = lib_file.pickle_load('dict_HSRLocs.pkl')
##### 2.2 高铁时刻表  ### 建图，属性上有车次
timetable = Timetable()
timetable.load_file('/run/media/pengfei/OTHERS/Code/Data/ChinaRailway/China_Railway_Schedule_20190701.csv')
G_HSRTimetable = timetable.get_graph()
#### 2.3 去掉时刻表中没有位置的点
for n in list(G_HSRTimetable.nodes()):
    if n not in dict_HSRLocs:
        G_HSRTimetable.remove_node(n)



#### 3.1 加载 车站在三小时car driving 时间内可达的格点的图(graph)
f_HSRGrid = '/run/media/pengfei/OTHERS/Code/Data/ChinaRailway/CalculateGridTravelTTeacherGiveME/StationGridAccessibility_Adapt.csv'
G_HSRGrid = lib_graph.createG_fromFile(f_HSRGrid, source='station', target='grid', attr=['distanceLBS_m','distance_m','duration_s'])

##### 感觉三小时太长了，换成1.5小时
for e in list(G_HSRGrid.edges):
    if G_HSRGrid[e[0]][e[1]]['duration_s']>1.5*60*60:
        G_HSRGrid.remove_edge(e[0],e[1])

##### 顺便区分一下格点
grids = set()  ### 注意这还是 字符串型
for n in list(G_HSRGrid.nodes):
    if n not in dict_HSRLocs:  ### 分辨了格点和车站
        grids.add(n)

grids = list(grids)


### 时刻表里取旅行时间
##### 在外边建图， 车站间旅行时间的图
dict_PairT = timetable.get_TravelT(mode="all")
G_HSRTravelT = nx.Graph()  ### 高铁站和高铁站之间的旅行时间
for pair in dict_PairT:
    if pair[0] in dict_HSRLocs and pair[1] in dict_HSRLocs and pair[0]!=pair[1]:
        median = np.median(dict_PairT[pair])
        t = min(dict_PairT[pair]) if min(dict_PairT[pair])>0.5*median else median  ### 避免说哪块数据有问题
        G_HSRTravelT.add_edge(pair[0],pair[1],minT=t)





###############################################################################
###############################################################################
### 正式开始，变多线程        


#ttt = lib_time.MeasureT()  ##### 开始计时
###### 4. 计算任意起点到可达车站的最短旅行时间
####### 选一个起点
#originGrid = random.choice(grids)
#first_order_HSR = list(nx.neighbors(G_HSRGrid,originGrid))
#
#founded_stations = set()  ## 记录已经遍历过的车站
### 已经不是换乘次数了，记录的是旅行时间
### dict_stationTransfer = {} ##  用来记录换乘次数的 {name:0}
#dict_drivingT = {}
#for name in first_order_HSR: ## 一阶可达的车站，car driving time 赋值
#    dict_drivingT[name] = G_HSRGrid[originGrid][name]['duration_s']/3600  ## 用分钟计数
#    
### 用networkx自带的这个函数 nx.shortest_path
#dict_AccessTime = defaultdict(list)
#for name in first_order_HSR:
#    dict_times = nx.shortest_path_length(G_HSRTravelT,source=name, weight='minT')
#    for n in dict_times:
#        if n not in dict_AccessTime:
#            dict_AccessTime[n]=dict_times[n]/60 + dict_drivingT[name]  # 加上开车到这个车站的时间
#        else:  ## 有很多车站能到达该车站，比较一下，找个最短的
#            dict_AccessTime[n] = min(dict_AccessTime[n],dict_times[n]/60 + dict_drivingT[name] )
#
#### 5. 将可达车站扩展到可达的区域
#dict_AccessArea = defaultdict(list)
#for name in dict_AccessTime:
#    neighbors = list(nx.neighbors(G_HSRGrid, name))
#    for p in neighbors:
#        dict_AccessArea[p].append(dict_AccessTime[name] + G_HSRGrid[p][name]['duration_s']/3600)
#
#dict_AccessAreaMin={}
#for p in dict_AccessArea:
#    dict_AccessAreaMin[p] = min(dict_AccessArea[p])

### 5.00 imshow的底图+ 带colorbar的散点图
#originGrid=res[9][0]
#dict_AccessAreaMin = res[9][1]
##x,y = zip(*[dict_HSRLocs[k] for k in dict_AccessAreaMin.keys()])
##z = list(dict_AccessAreaMin.values())
#x,y = zip(*[eval(p) for p in dict_AccessAreaMin.keys()])
#z = list(dict_AccessAreaMin.values())
#
#minx,maxx,miny,maxy = (73.4997347, 134.7754563, 17.7, 53.560815399999996)
#implot = lib_plot.ImPlot('/run/media/pengfei/OTHERS/Gitlab/pythonsharedfunctions.git/China.png')
#lib_plot.scatter_with_colorbar(x,y,z, s=1)
#implot.plot_point(eval(originGrid)[0],eval(originGrid)[1],marker='x',color='black',alpha=1,markersize=10)
#implot.imshow()    # fpath='random/'+name

#ttt.duration()


def func(originGrid):  # DataFrame的一条，只能传进来列表
    #### 传进去字典就会出问题？？？？？？
    #t1=time.time()
    first_order_HSR = list(nx.neighbors(G_HSRGrid,originGrid))
    ## 已经不是换乘次数了，记录的是旅行时间
    ## dict_stationTransfer = {} ##  用来记录换乘次数的 {name:0}
    dict_drivingT = {}
    for name in first_order_HSR: ## 一阶可达的车站，car driving time 赋值
        dict_drivingT[name] = G_HSRGrid[originGrid][name]['duration_s']/3600  ## 用分钟计数
        
    ## 用networkx自带的这个函数 nx.shortest_path
    dict_AccessTime = defaultdict(list)
    for name in first_order_HSR:
        dict_times = nx.shortest_path_length(G_HSRTravelT,source=name, weight='minT')
        for n in dict_times:
            if n not in dict_AccessTime:
                dict_AccessTime[n]=dict_times[n]/60 + dict_drivingT[name]  # 加上开车到这个车站的时间
            else:  ## 有很多车站能到达该车站，比较一下，找个最短的
                dict_AccessTime[n] = min(dict_AccessTime[n],dict_times[n]/60 + dict_drivingT[name] )
    
    ### 5. 将可达车站扩展到可达的区域
    dict_AccessArea = defaultdict(list)
    for name in dict_AccessTime:
        neighbors = list(nx.neighbors(G_HSRGrid, name))
        for p in neighbors:
            dict_AccessArea[p].append(dict_AccessTime[name] + G_HSRGrid[p][name]['duration_s']/3600)
    
    dict_AccessAreaMin={}
    for p in dict_AccessArea:
        dict_AccessAreaMin[p] = min(dict_AccessArea[p])
        
    #print(time.time()-t1)    
    return originGrid, dict_AccessAreaMin  


def main():
    pool = multiprocessing.Pool(processes=8)
    res = pool.map(func, grids[:100])

    return res


__spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
ttt = lib_time.MeasureT()  ##### 开始计时
res = main()
#### z组装结果
#dict_res = dict(res)
ttt.duration()
lib_file.pickle_save(res,'res.pkl')