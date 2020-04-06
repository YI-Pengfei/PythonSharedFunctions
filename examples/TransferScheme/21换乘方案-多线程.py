# -*- coding: utf-8 -*-
"""
    根据中国高速铁路列车运行时刻表，给定网格点及出发时刻，
    计算到任意网格点的 最短旅行时间 及 出行方案
    算法基于： BFS 图的 广度优先搜索
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

import lib_time  ### 关于时间的相应操作在这个包里
from lib_time import get_deltaT, strT_to_floatT, floatT_to_strT


def get_scheme(source, target, G_schedule, dict_parents, prepareT=0.25):
    """ 在起终点之间有很多的车，找一班最近的列车
        G_schedule: 列车时刻表建的有向图
        dict_parents: 上一代的信息
        return: 乘坐的最佳列车的基本信息
    """
    last_arrive = dict_parents[source]['arrive']  ## 前车的到站时间
    last_travelT = dict_parents[source]['travelT']  ## 在以前已经用掉的旅行时间
    
    all_trains = list(G_schedule[source][target].items())
    temp_travelT = 10000
    out_info = {}
    for depart, info in all_trains:
        delta_t = get_deltaT(last_arrive, depart, unit='h')
        if delta_t>=12 or delta_t<prepareT:  ### 相差十二小时以上是无法判断的 
            continue
        during = get_deltaT(info['depart'], info['arrive'],unit="h") 
        travelT = last_travelT + delta_t + during  ## 已用 + 换乘 + 本次
        if travelT<temp_travelT:
            temp_travelT = travelT
            daysign = 1 if strT_to_floatT(info['arrive']) < strT_to_floatT(info['depart']) else 0  #### 非必须
            out_info = info
            ## 计算一个在当前车上的停留时间
            out_info['travelT'] = travelT # 前车已用的旅行时间+准备时间，准备好到真正发车的时间，本次列车将花费的时间
            out_info['scheduleDelay'] = delta_t
            out_info['daysign'] = daysign
            out_info['last_depart_station'] = source
            out_info['during'] = during
            
    return out_info


def get_accessHSRs(G_schedule, dict_parents, dict_accessed):
    """ 由第N层已经到达的车站的信息，确定可到达的第N+1层的车站的信息
        G_schedule: 列车时刻表建立的有向图
        dict_parents: 第N层可到达的车站的信息 (例如已用的旅行时间，列车到站时间)
        dict_accessed: 汇总的前N层中到达各站最短的旅行时间
    """
    dict_ChildInfo = {} # defaultdict(dict)
    for s in dict_parents:
        ### 在原来的到站时间的基础上添加一个准备时间
        neighbors =  list(nx.neighbors(G_schedule,s))
        for n in neighbors:
            info = get_scheme(s, n, G_schedule, dict_parents)
            if not info:  ### 并没有合适的列车
                continue
            #if info['scheduleDelay'] > 12: # 在车站等待四个小时以上
            #    continue
            if (n in dict_accessed) and (info['travelT'] - dict_accessed[n]>=-0.1): ## 就没快几分钟，不用换了
                continue
            if (n not in dict_ChildInfo) or (dict_ChildInfo[n]['travelT'] > info['travelT']):
                dict_ChildInfo[n] = info    

    
    return dict_ChildInfo


###############################################################################
######################     Data prepare     ###################################
##### 1.1 高铁车站的位置
dict_HSRLocs = lib_file.pickle_load('dict_HSRLocs.pkl')
##### 2.2 高铁时刻表,加载有向图
timetable = Timetable()
timetable.load_file('/run/media/pengfei/OTHERS/Code/Data/ChinaRailway/China_Railway_Schedule_20190701.csv')
###### 2.3 去掉时刻表中没有位置的点
G_schedule = timetable.get_TravelT(mode="all")
for n in list(G_schedule.nodes()):
    if n not in dict_HSRLocs:
        G_schedule.remove_node(n)
        
#### 3.1 加载 车站在三小时car driving 时间内可达的格点的图(graph)
f_HSRGrid = '/run/media/pengfei/OTHERS/Code/Data/ChinaRailway/CalculateGridTravelTTeacherGiveME/StationGridAccessibility_Adapt.csv'
G_HSRGrid = lib_graph.createG_fromFile(f_HSRGrid, source='station', target='grid', attr=['distanceLBS_m','distance_m','duration_s'])

##### 感觉三小时太长了，换成1.0小时
for e in list(G_HSRGrid.edges):
    if G_HSRGrid[e[0]][e[1]]['duration_s']>1.0*60*60:
        G_HSRGrid.remove_edge(e[0],e[1])
for n in list(G_HSRGrid.nodes):
    if len(list(nx.neighbors(G_HSRGrid,n)))==0:
        G_HSRGrid.remove_node(n)
##### 顺便区分一下格点
grids = set()  ### 注意这还是 字符串型
for n in list(G_HSRGrid.nodes):
    if n not in dict_HSRLocs:  ### 分辨了格点和车站
        grids.add(n)

grids = list(grids)


lons,lats = zip(*[eval(p) for p in grids])
lons = sorted(lons)
lats = sorted(lats)

Beijing =(116.3912757,39.906217) #  (121.4890497,31.2252985)#上海      #
lon = 0
lat = 0
for l in lons:
    if abs(l-Beijing[0]) <abs(lon-Beijing[0]):
        lon = l
for l in lats:
    if abs(l-Beijing[1]) <abs(lat-Beijing[1]):
        lat = l
        
###############################################################################
####################### Program start #########################################
ttt = lib_time.MeasureT()  ##### 开始计时
##### 4. 计算任意起点到可达车站的最短旅行时间
###### 选一个起点，设一个在家出来的时间


def func(str_startT):  # DataFrame的一条，只能传进来列表
    startT = strT_to_floatT(str_startT)
    list_layerAccess = []  
    dict_accessed = {}  # 车站:最短旅行时间
    dict_ChildInfo = {} # defaultdict(dict) # 车站：由N层到N+1层 所乘坐列车基本信息
    originGrid = str((lon, lat))
    carAccessHSR = list(nx.neighbors(G_HSRGrid,originGrid))  ## 1.5小时内开车到达的车站
    
    for s in carAccessHSR: 
        arriveT = startT + G_HSRGrid[s][originGrid]['duration_s']/60/60  # 出发时刻+开车时间+准备时间
        dict_ChildInfo[s] = {}
        dict_ChildInfo[s]['arrive'] = str(int(arriveT)).zfill(2)+':'+str(int((arriveT%1)*60)).zfill(2)  # 字符串
        dict_ChildInfo[s]['travelT'] = arriveT-startT ## 浮点数
        dict_ChildInfo[s]['daysign'] = 0
        dict_ChildInfo[s]['train_code'] = 'carDriving'
    
    while dict_ChildInfo:
        for name in dict_ChildInfo:  ## 既然是被留下来的，就证明是旅行时间更短的
            dict_accessed[name] = dict_ChildInfo[name]['travelT']
        list_layerAccess.append(dict_ChildInfo)
            
        dict_ChildInfo = get_accessHSRs(G_schedule, list_layerAccess[-1], dict_accessed)
    
    
    ttt.duration('shortest travel time finished')
    
    #### 将可达车站扩展到可达区域
    ### 5. 将可达车站扩展到可达的区域
    dict_AccessArea = defaultdict(list)
    
    for name in dict_accessed:
        neighbors = list(nx.neighbors(G_HSRGrid, name))
        for grid in neighbors:
            dict_AccessArea[grid].append(dict_accessed[name]+G_HSRGrid[grid][name]['duration_s']/3600)
    
    dict_AccessAreaMin={}  ### 选出最短的旅行时间
    for p in dict_AccessArea:
        dict_AccessAreaMin[p] = min(dict_AccessArea[p])
    
    ### 5.1 画图
    ##  imshow的底图+ 带colorbar的散点图
    ## 画车站
    #x = []
    #y = []
    #z = []
    #for name in dict_HSRshortestT:
    #    if dict_HSRshortestT[name]<=20:
    #        x.append(dict_HSRLocs[name][0])
    #        y.append(dict_HSRLocs[name][1])
    #        
    #        z.append(dict_HSRshortestT[name])
    
    x,y = zip(*[eval(k) for k in dict_AccessAreaMin.keys()])
    z = list(dict_AccessAreaMin.values())

    xs = []
    ys = []
    zs = []
    for i,v in enumerate(z):
        if v<=7:
            xs.append(x[i])
            ys.append(y[i])
            zs.append(v)
    x,y,z=xs,ys,zs
    
    minx,maxx,miny,maxy = (73.4997347, 134.7754563, 17.7, 53.560815399999996)
    implot = lib_plot.ImPlot('/run/media/pengfei/OTHERS/Gitlab/pythonsharedfunctions.git/China.png')
    lib_plot.scatter_with_colorbar(x,y,z, s=4,vmin=0,vmax=7)
    implot.plot_point(eval(originGrid)[0],eval(originGrid)[1],marker='x',color='black',alpha=1,markersize=10)
    implot.plot_point(121.451093,31.25151,marker='+',color='green',alpha=1,markersize=10)
    plt.title(str_startT)
    ii = int(strT_to_floatT(str_startT,unit='m')/5)  ## 五分钟的分辨率
    implot.imshow(fpath='/run/media/pengfei/OTHERS/每日总结/20190923/beijing-5.5h/'+str(ii))    # 
    ttt.duration('plot finished.')


def main():
    pool = multiprocessing.Pool(processes=8)
    res = pool.map(func, list_str_startT)
    return res


#### 生成todo列表
list_str_startT = []
str_startT = '00:00'
startT = 0
while startT<24:
    list_str_startT.append(str_startT)
    startT = (strT_to_floatT(str_startT, unit='m') + 5)/60 # 加五分钟
    str_startT = floatT_to_strT(startT, unit='h')
    

main()