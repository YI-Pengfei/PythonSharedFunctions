# -*- coding: utf-8 -*-
"""
寻找功能互补的车站簇
限制条件：  1. 20min车程内
           2. 相似度在0.02以下
           3. 运行列车数在XXXX以上 （过滤掉小站）
           4. 直接可达的车站数在XXX以上

最后有画图功能 用不同的颜色，不同的marker，有题注
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
import multiprocessing
from haversine import haversine


def jaccard_similarity(list1, list2):
    s1 = set(list1)
    s2 = set(list2)
    return len(s1.intersection(s2)) / len(s1.union(s2))

# 1 数据准备
##### 1.1 车站的位置
dict_HSRLocs = lib_file.pickle_load('E:/Code/需求与辐射模型-欧洲/dict_HSRLocs.pkl')

###### 1.2 列车时刻表,加载有向图
timetable = Timetable()
timetable.load_file('E:/Code/Data/EuropeRailway/Europe_Railway_Schedule.csv',mode='ALL',encoding='utf-8')  ### ALL 指的是全部车型， 还可以特指HSR，但是欧洲不支持
#G_schedule = timetable.get_DiGraph(mode="all")
G_HSRTimetable = timetable.get_graph()

#### 2.3 去掉时刻表中没有位置的点
for n in list(G_HSRTimetable.nodes()):
    if n not in dict_HSRLocs:
        G_HSRTimetable.remove_node(n)

### 2.4 车站间 car driving时间的数据   2019.09.27添加   
G_stationPair = lib_graph.createG_fromFile('E:/Code/Data/EuropeRailway/Europe_StationPairAccessibility_200km.csv', source='source', target='target', attr=['distanceLBS_km','duration_min'])
##### 挑出来 20min 之内的可互达的车站
for e in list(G_stationPair.edges):
    if G_stationPair[e[0]][e[1]]['duration_min']>20:   ### 门限1，20 mins
        G_stationPair.remove_edge(e[0],e[1])
for n in list(G_stationPair.nodes):
    if len(list(nx.neighbors(G_stationPair,n)))==0:
        G_stationPair.remove_node(n)


###############################################################################
#################### program start ############################################
"""
限制条件：  1. 20min车程内
           2. 相似度在0.02以下
           3. 运行列车数在XXXX以上 （过滤掉小站）
           4. 直接可达的车站数在XXX以上
"""
G_JS = nx.Graph()  # 边权值为Jaccard Similarity
for name in G_stationPair.nodes:
    if len(timetable.get_TrainCodes_of_station(name)) <= 20 or len(list(nx.neighbors(G_HSRTimetable, name)))<=10:
        continue  ## 日运行车次数小于20，忽略      
    
    neighbors = list(nx.neighbors(G_stationPair, name))
    accessed_stations = list(nx.neighbors(G_HSRTimetable, name))
    for n in neighbors:   #### 只需要 在 20mins 内可达的车站间计算 相似度
        if len(timetable.get_TrainCodes_of_station(n)) <= 20 or len(list(nx.neighbors(G_HSRTimetable, n)))<=10:
            continue  ## 日运行车次数小于20，忽略  
        if (name,n) in G_JS.edges:  ## 已经比较过，无需再计算
            continue 
        accessed_stations2 = list(nx.neighbors(G_HSRTimetable, n))
        js = jaccard_similarity(accessed_stations, accessed_stations2)
        if js<0.04:  ### 相似度小于0.02
            G_JS.add_edge(name, n, jaccard=js)
            
        
components = [list(c) for c in nx.connected_components(G_JS)]
        

stations = set()
for c in components:
    for s in c:
        stations.add(s)

## 为 graph画图
#list_locs = [dict_HSRLocs[s] for s in stations]     
#m=lib_plot.plot_From_Locations(list_locs,s=0.1,fpath=None,x=900,y=900,dpi=150,shp_file=None,m=None,color='r',marker='.',bbox=None)
#
##lib_graph.plot_G(G_JS, dict_HSRLocs, attr=None)
#for line in G_JS.edges:
#    s1,s2 = line
#    lon1,lat1 = dict_HSRLocs[s1]
#    lon2,lat2 = dict_HSRLocs[s2]
#    lib_plot.plotLine(m,lon1,lat1,lon2,lat2,color="blue",lwd=0.5,lty="-",alpha=0.5,linewidth=0.15) 

#### 为 互补车站画图
import lib_timetable   
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors


colors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)

# Sort colors by hue, saturation, value and name.
by_hsv = sorted((tuple(mcolors.rgb_to_hsv(mcolors.to_rgba(color)[:3])), name)
                for name, color in colors.items())
colors = list(colors.keys())

for jj in range(len(components)):   ### 画出所有的片
    list_stations = components[jj]
    all_accessible_stations = set()
    for s in list_stations:
        neighbors = list_accessed = set(nx.neighbors(G_HSRTimetable, s))
        all_accessible_stations = all_accessible_stations |neighbors
        
    m=lib_timetable.plot_trainPoints(list(all_accessible_stations), dict_HSRLocs)  #### 要传进去所有的车站
    #colors = ['peru','dodgerblue','brown',
    #          'darkslategray','yellow', 'lightsalmon',
    #          'orange','chartreuse','red']
    
    markers = [',', 'o', '^', 'v', '<', '>', '+', 'x', 'D', 'd',   # , 's'
        '1','2', '3','4',  # 三脚架朝上下左右
        'h', 'H','p',  # 六角形五角形
         '|', '_']  # 垂线水平线
    
    legends = []
    #for i,list_trains in enumerate(list_list_trains):
    for i,name in enumerate(list_stations):
        list_accessed = list(nx.neighbors(G_HSRTimetable, name))
        #lib_timetable.plot_trainlines(m,list_trains, dict_HSRLocs, name=list_names[i],color=colors[i])
        #ledgends.append(l)
        l = lib_timetable.plot_stations(m, list_accessed, dict_HSRLocs, name=None,color=colors[i],marker=markers[i],s=10)
        legends.append(l)
        
    plt.legend(tuple(legends), tuple(list_stations))
    fpath='E:/每日总结/20191002/c'+str(jj)
    plt.savefig(fpath+'.png',dpi=150) # 指定分辨率
    plt.close()
    #break