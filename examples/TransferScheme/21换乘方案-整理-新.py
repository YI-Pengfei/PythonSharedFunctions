OS = 'E:/' # /run/media/pengfei/OTHERS/
import sys
sys.path.append(OS+'Gitlab/pythonsharedfunctions.git')
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


def get_scheme(source, target, G_schedule, dict_parents, prepareT=15):
    """ 在起终点之间 找最早的一班列车
        G_schedule: 列车时刻表建的有向图
        dict_parents: 上一代的信息
        prepareT: 准备时间 15 mins
        return: 乘坐的最佳列车的基本信息
    """
    last_arriveT = dict_parents[source]['arrive']  ## 前车的到站时间
    past_travelT = dict_parents[source]['total_travelT']  ## 在以前已经用掉的旅行时间

    all_trains = G_schedule[source][target]
    
    min_travelT = 10**6  # 设置一个足够大的旅行时间
    out_info = {'from':source,'to':target,'last_arrive':last_arriveT,'past_travelT':past_travelT}
    for ID in all_trains:
        info = all_trains[ID]
        departT = info['depart']
        delta_t = get_deltaT(last_arriveT, departT, unit='min')  ### 前车到站时间 和 下趟车出发时间 的比较
        if delta_t>=12*60 or delta_t<prepareT:  # 接续换乘等待时间不太长，也不太短
            continue
        this_during = info['travel_time']  # 本次列车的运行时间，min
        travelT = past_travelT + delta_t + this_during  # 已用 + 换乘 + 本次
        if travelT< min_travelT:
            min_travelT = travelT
            
            for k in info:
                out_info[k] = info[k]
            out_info['scheduleDelay'] = delta_t # mins
            out_info['total_travelT'] = travelT
            out_info['total_travelT_h'] = str(travelT//60).zfill(2)+':'+str((travelT%60)).zfill(2)  # 字符串
    
    return out_info


def get_accessHSRs(G_schedule, dict_parents, dict_accessed):
    """ 由第N层已经到达的车站的信息，确定可到达的第N+1层的车站的信息
        G_schedule: 列车时刻表建立的有向图
        dict_parents: 第N层可到达的车站的信息 (例如已用的旅行时间，列车到站时间)
        dict_accessed: 汇总的前N层中到达各站最短的旅行时间
    """
    dict_ChildInfo = {}
    for s in dict_parents:
        neighbors =  list(nx.neighbors(G_schedule,s))
        for n in neighbors:
            info = get_scheme(s, n, G_schedule, dict_parents)
            if not 'train_code' in info:  ## 并没有产生有效的接续换乘策略
                continue
            if (n in dict_accessed) and (info['total_travelT'] - dict_accessed[n]>=-0.1): ## 现在是以分钟为单位，应该不需要后边这个条件了
                continue
            if (n not in dict_ChildInfo) or (dict_ChildInfo[n]['total_travelT'] > info['total_travelT']):
                dict_ChildInfo[n] = info              
    
    return dict_ChildInfo
                
    
    
# 1 数据准备
###### 1.1 列车时刻表,加载有向图
timetable = Timetable()
timetable.load_file(OS+'Code/Data/ChinaRailway/China_Railway_Schedule_20190701.csv',mode='HSR')
G_schedule = timetable.get_DiGraph(mode="all")
###### 1.2 保存有向图
#lib_file.pickle_save(G_schedule,OS+'Code/Data/ChinaRailway/G_schedule.pkl')
##### 1.3 直接加载有向图
#G_schedule = lib_file.pickle_load(OS+'Code/Data/ChinaRailway/G_schedule.pkl')

##### 1.1 车站的位置
df_railwayLocs = lib_file.read_file2df(OS+'Code/Data/ChinaRailway/China_Station_Locs_All.csv')
dict_HSRLocs = lib_file.get_LocIndex(df_railwayLocs)        

#### 3.1 加载 车站在一小时car driving 时间内可达的格点的图(graph)
f_HSRGrid = OS+'Code/Data/ChinaRailway/China_StationGridAccessibility_1h_correct.csv'
G_HSRGrid = lib_graph.createG_fromFile(f_HSRGrid, source='station', target='grid', attr=['distanceLBS_m','duration_s'])


##### 顺便区分一下格点
grids = set()  ### 注意这还是 字符串型
for n in list(G_HSRGrid.nodes):
    if n not in dict_HSRLocs:  ### 分辨了格点和车站
        grids.add(n)

grids = list(grids)
##### 3.1.1 为了同时适用于 高铁、全部 两种情况，这里将不是高铁站的去掉
for n in list(G_HSRGrid.nodes):
    if n in dict_HSRLocs and n not in G_schedule:
        G_HSRGrid.remove_node(n)

### 3.2    2019.09.27添加   车站间 car driving 的时间
f_stationPair = OS+'Code/Data/ChinaRailway/China_StationPairAccessibility_200km.csv'
G_stationPair = lib_graph.createG_fromFile(f_stationPair, source='source', target='target', attr=['distanceLBS_km','duration_min'])
##### 挑出来 20min 之内的可互达的车站
for e in list(G_stationPair.edges):
    if G_stationPair[e[0]][e[1]]['duration_min']>20:
        G_stationPair.remove_edge(e[0],e[1])
for n in list(G_stationPair.nodes):
    if len(list(nx.neighbors(G_stationPair,n)))==0:
        G_stationPair.remove_node(n)



ttt = lib_time.MeasureT()  ##### 开始计时

str_startT = '06:00'
#startT = 6.00
startT = strT_to_floatT(str_startT,unit='m')  ## min 

list_layerAccess = []  
dict_accessed = {}  # 车站:最短旅行时间
dict_ChildInfo = {} # defaultdict(dict) # 车站：由N层到N+1层 所乘坐列车基本信息
originGrid = str(lib_grid.get_nearestGrid(dict_HSRLocs['哈尔滨'],1/20))
carAccessHSR = list(nx.neighbors(G_HSRGrid,originGrid))  ## 1.5小时内开车到达的车站
### 组装一个初始的 dict_ChildInfo 字典
for s in carAccessHSR: 
    int_arriveT = startT + round(G_HSRGrid[s][originGrid]['duration_s']/60) # min 为单位
    arriveT = str((int_arriveT%1440)//60).zfill(2)+':'+str(int((int_arriveT%1440)%60)).zfill(2)  # 字符串
    dict_ChildInfo[s] = {}
    dict_ChildInfo[s]['train_code'] = 'carDriving'
    dict_ChildInfo[s]['depart'] = str_startT
    dict_ChildInfo[s]['arrive'] = arriveT
    dict_ChildInfo[s]['total_travelT'] = int_arriveT-startT ## 浮点数
    
while dict_ChildInfo:
    for name in dict_ChildInfo:  ## 既然是被留下来的，就证明是旅行时间更短的
        dict_accessed[name] = dict_ChildInfo[name]['total_travelT']
    list_layerAccess.append(dict_ChildInfo)
        
    dict_ChildInfo = get_accessHSRs(G_schedule, list_layerAccess[-1], dict_accessed)

ttt.duration('Scheme generated.')
#### 将可达车站扩展到可达区域
### 5. 将可达车站扩展到可达的区域
dict_AccessArea = defaultdict(list)

for name in dict_accessed:
    #if name not in {'上海','上海虹桥'}:
    #    continue
    neighbors = list(nx.neighbors(G_HSRGrid, name))
    for grid in neighbors:
        dict_AccessArea[grid].append(dict_accessed[name]+round(G_HSRGrid[grid][name]['duration_s']/60))

dict_AccessAreaMin={}  ### 选出最短的旅行时间
for p in dict_AccessArea:
    dict_AccessAreaMin[p] = min(dict_AccessArea[p])
    
x,y = zip(*[eval(k) for k in dict_AccessAreaMin.keys()])
z = list(dict_AccessAreaMin.values())

xs = []
ys = []
zs = []
for i,v in enumerate(z):
    if v/60<=30:  ## 只看五小时能到的
        xs.append(x[i])
        ys.append(y[i])
        zs.append(v/60)
x,y,z=xs,ys,zs

minx,maxx,miny,maxy = (73.4997347, 134.7754563, 17.7, 53.560815399999996)
implot = lib_plot.ImPlot(OS+'Gitlab/pythonsharedfunctions.git/China.png')
lib_plot.scatter_with_colorbar(x,y,z, s=1, vmax=30,vmin=0)
implot.plot_point(eval(originGrid)[0],eval(originGrid)[1],marker='x',color='black',alpha=1,markersize=10)
#implot.plot_point(121.451093,31.25151,marker='+',color='green',alpha=1,markersize=10)
plt.title(str_startT)
implot.imshow()    # fpath='/run/media/pengfei/OTHERS/每日总结/20190923/beijing2/'+str(ii)

ttt.duration('Plot finished.')

