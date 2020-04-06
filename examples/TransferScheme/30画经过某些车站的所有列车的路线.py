""" 画经过某些车站的所有列车的路线，L-space型
    用于对单个车站的debug
    23互补高铁站的统计 是这个程序的拓展

"""

OS = 'E:/'  # 'E:/' # 
import sys
sys.path.append(OS+'Gitlab/pythonsharedfunctions.git')
import pandas as pd
from collections import defaultdict, Counter
import lib_file
from lib_timetable import Timetable, FlightTimetable
import lib_timetable
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

import lib_time  ### 关于时间的相应操作在这个包里
from lib_time import get_deltaT, strT_to_floatT, floatT_to_strT


# 1 数据准备
##### 1.1 车站的位置
dict_HSRLocs = lib_file.pickle_load('E:/Code/需求与辐射模型-欧洲/dict_HSRLocs.pkl')

###### 1.1 列车时刻表,加载有向图
timetable = Timetable()
timetable.load_file('E:/Code/Data/EuropeRailway/Europe_Railway_Schedule.csv', mode='ALL',encoding='utf-8')  ### ALL 指的是全部车型， 还可以特指HSR，但是欧洲不支持

#list_names = ['London Euston', 'London Paddington', 'London St Pancras',
#             'London Kings Cross', 'London Liverpool Street', 'London Blackfriars', 
#             'London Bridge', 'London Charing Cross', 'London Victoria']

##  dict_pairJS    应该也建成图
###### 识别一个互补车站群  #####################################
#G = nx.Graph()
#for pair in dict_pairJS:
#    JS = dict_pairJS[pair]
#    G.add_edge(pair[0],pair[1],weight=JS)
#    
#NAME = 'Paris Nord'
#stations = set()
#temp = {'Paris Nord'}
#while temp!=stations:
#    stations = stations|temp
#    temp = set()
#    for name in stations:
#        neighbors = nx.neighbors(G,name)
#        for n in neighbors:
#            if G[name][n]['weight'] <0.02:
#                temp.add(n)
#########################################################################
list_names = list(stations)    

list_names = ['Berlin Lichtenberg']  ### 指定一个车站，或者多个车站，
list_list_trains = []
list_stations = []
for NAME in list_names:

#NAME = 'London Euston'
    train_codes = timetable.get_TrainCodes_of_station(NAME)
    list_trains = []
    for code in train_codes:
        sub_df = timetable.get_train(code)
        list_trains.append(tuple(sub_df.station_name))


    ##### 线路上是有重复的,
    list_trains = list(set(list_trains)) 
    for train in list_trains:
        list_stations += [s for s in train]
    
    list_list_trains.append(list_trains)

   

m=lib_timetable.plot_trainPoints(list_stations, dict_HSRLocs)
colors = ['peru','dodgerblue','brown',
          'darkslategray','yellow', 'lightsalmon',
          'orange','chartreuse','red']

markers = [',', 'o', '^', 'v', '<', '>', 's', '+', 'x', 'D', 'd', 
    '1','2', '3','4',  # 三脚架朝上下左右
    'h', 'H','p',  # 六角形五角形
     '|', '_']  # 垂线水平线

legends = []
for i,list_trains in enumerate(list_list_trains):
    lib_timetable.plot_trainlines(m,list_trains, dict_HSRLocs, name=list_names[i],color=colors[i])  ## 画线，
    #ledgends.append(l)
    l = lib_timetable.plot_trainpoints(m, list_trains, dict_HSRLocs, name=list_names[i],color=colors[i],marker=markers[i],s=10)
    legends.append(l)
    
plt.legend(tuple(legends), tuple(list_names))
        