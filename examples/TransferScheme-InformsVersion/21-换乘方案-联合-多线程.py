import os
import sys
OS = '/run/media/pengfei/OTHERS/' # 
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
from multiprocessing import Pool
import random
import matplotlib.pyplot as plt

import lib_time  ### 关于时间的相应操作在这个包里
from lib_time import get_deltaT, strT_to_floatT, floatT_to_strT
 
import lib_transferTWO 
from xpinyin import Pinyin
import time

ppinyin = Pinyin()
"""
    1. 基础数据     车站位置，机场位置
    数据类型： 字典 dict
"""
##### 1.1 车站的位置
df_railwayLocs = lib_file.read_file2df(OS+'Code/Data/ChinaRailway/China_Station_Locs_All.csv')
dict_HSRLocs = lib_file.get_LocIndex(df_railwayLocs)  
##### 1.2 机场的位置
dict_AirportLocs = lib_file.pickle_load(OS+'Code/空铁联合换乘/data/dict_AirportLocs.pkl')
##### 1.3 位置信息合并
dict_PortLocs = dict( dict_HSRLocs, **dict_AirportLocs )

"""
    2. 时刻表数据
    数据类型： 有向图 DiGraph
"""
def add_type2G(G, dict_HSRLocs, dict_AirportLocs):
    ## 为图中的节点添加类型标示， "station" or "airport"
    for name in G:  ## 为图节点添加属性
        if name in dict_HSRLocs: # 火车站
            G.node[name]['type']= 'station'
        elif name in dict_AirportLocs:
            G.node[name]['type']= 'airport'    
    return G

##### 2.1 列车时刻表
G_Rail = lib_file.pickle_load(OS+'Code/Data/ChinaRailway/G_schedule.pkl')
##### 2.2 航班时刻表
flights = FlightTimetable()
flights.load_file(OS+'Code/Data/ChinaAir/China_Air_Schedule_Clean.csv')
G_flights = flights.get_DiGraph()
for name in list(G_flights.nodes):  ### 有五个机场没有位置信息，删除了
    if name not in dict_AirportLocs:
        G_flights.remove_node(name)   
##### 2.3 两个时刻表合并
G_schedule = nx.compose(G_Rail,G_flights)  ## 二者连成一张图
##### 2.4 为节点添加类型标示
G_schedule = add_type2G(G_schedule, dict_HSRLocs, dict_AirportLocs)
"""
    3. 机场/车站 与 网格点之间驾车时间的数据    机场--网格：2hours   车站--网格: 1hour
    数据类型： 无向图 Graph
"""
##### 3.1 车站<-->网格 1 hours
f_HSRGrid = OS+'Code/Data/ChinaRailway/China_StationGridAccessibility_1h_5mins.csv'  # 分辨率是1/12度
G_HSRGrid = lib_graph.createG_fromFile(f_HSRGrid, source='station', target='grid', attr=['distanceLBS_m','duration_s'])     
##### 3.2 机场<-->网格 2 hours
f_AirGrid = OS+'Code/空铁联合换乘/data/China_AirportGridAccessibility_2h_5mins.csv'
G_AirGrid = lib_graph.createG_fromFile(f_AirGrid, source='station', target='grid', attr=['distanceLBS_m','duration_s'])
##### 3.3 合并
G_PortGrid = nx.compose(G_HSRGrid,G_AirGrid)  ## 二者连成一张图
##### 2.4 为节点添加类型标示
G_PortGrid = add_type2G(G_PortGrid, dict_HSRLocs, dict_AirportLocs)

"""
    4. 车站<-->车站   机场<-->机场    车站<-->机场   驾车时间的数据 （ 需要自设门限然后截取）
"""
def cut_G(G,thres):
    """  根据门限对图进行截取
        thres: 门限， mins为单位， 例如 20 mins
    """
    for e in list(G.edges):
        if G[e[0]][e[1]]['duration_min']>thres:
            G.remove_edge(e[0],e[1])
    for n in list(G.nodes):
        if len(list(nx.neighbors(G,n)))==0:
            G.remove_node(n)    
    return G
##### 4.1 车站<-->车站   200km内， 截取 20mins车程可达的
f_stationPair = OS+'Code/Data/ChinaRailway/China_StationPairAccessibility_200km.csv'
G_stationPair = lib_graph.createG_fromFile(f_stationPair, source='source', target='target', attr=['distanceLBS_km','duration_min'])
G_stationPair = cut_G(G_stationPair,20)
##### 4.2 机场<-->机场   300km内，截取1h车程可达的
f_airportPair = OS+'Code/空铁联合换乘/data/China_AirportPairAccessibility_300km.csv'
G_airportPair = lib_graph.createG_fromFile(f_airportPair, source='source', target='target', attr=['distanceLBS_km','duration_min'])
G_airportPair = cut_G(G_airportPair,60)
##### 4.3 机场<-->车站   300km内，截取1h车程可达的
f_airportStation = OS+'Code/空铁联合换乘/data/China_AirportStationAccessibility_300km.csv'
G_airportStation = lib_graph.createG_fromFile(f_airportStation, source='source', target='target', attr=['distanceLBS_km','duration_min'])
G_airportStation = cut_G(G_airportStation,60)
##### 4.4 合并三个图到一起
G_PortPort = nx.compose(G_airportStation, G_airportPair)  ## 二者连成一张图
G_PortPort = nx.compose(G_PortPort, G_stationPair)
##### 4.5 为节点添加类型标示
G_PortPort = add_type2G(G_PortPort, dict_HSRLocs, dict_AirportLocs)

"""
    5.城市中心坐标数据
"""
ffff = open(OS+'Code/比较旅行时间/China_cities_population.csv')
df_pops = pd.read_csv(ffff)
dict_CityLocs = dict(zip(df_pops.name,df_pops.location))

       
 
#ttt = lib_time.MeasureT()  ##### 开始计时
#NAME='北京'
#originGrid = str(lib_grid.get_nearestGrid(dict_HSRLocs[NAME],1/20))
RESOLUTION=10
#### 生成todo列表
list_str_startT = []
str_startT = '00:00'
startT = 0
while startT<24:
    list_str_startT.append(str_startT)
    startT = (strT_to_floatT(str_startT, unit='m') + RESOLUTION)/60 # 加五分钟
    str_startT = floatT_to_strT(startT, unit='h')


def func(NAME):
    originGrid = str(lib_grid.get_nearestGrid(eval(dict_CityLocs[NAME]),1/12))
    if originGrid not in G_PortGrid:
        print('Grid point is not in G_HSRGrid. %s:%s'%(NAME, originGrid))
        return 0
    for str_startT in list_str_startT:   # 生成所有时间点
        #str_startT = '00:10'
        dict_Sure = {} ## 存储已经找到最短路径的点 
        dict_Candidate = {} ## 存储找到路径的
        
        ### 1.1 初始化，从家cardriving可达的车站
        originInfo_station = lib_transferTWO.get_driving_origins(G_PortGrid,originGrid,str_startT)
        ### 1.2 构造成方案列表的形式
        for name in originInfo_station:
            dict_Candidate[name] = [originInfo_station[name]]
        while dict_Candidate:
            ### 2.1 选出一个旅行时间最短的目的 车站/机场 添加进 dict_Sure中
            selected = lib_transferTWO.add_shortest2Sure(dict_Sure,dict_Candidate)
            ### 2.2 用该确定最短路径的节点更新所有其他节点的路径  (机场-->机场， 车站--> 车站)
            updates = lib_transferTWO.update_Candidate(selected, dict_Candidate, dict_Sure, G_schedule)  
            
            updates2 = lib_transferTWO.update_Candidate_cardriving(selected, dict_Candidate, dict_Sure, G_PortPort,{})
        
        ### 3处理结果
        ### 简化结果，只取最短时间，不要路径
        dict_accessed = {}
        for name in dict_Sure:
            dict_accessed[name] = dict_Sure[name][-1]['total_travelT']
        #ttt.duration('Scheme ready')       
    
        df = lib_transferTWO.save_scheme(dict_Sure)   ############### 生成详细信息
        #path = '/run/media/pengfei/OTHERS/每日总结/20191015/%s/'%NAME
        path = '/run/media/pengfei/OTHERS/每日总结/20191016-2/%s/'%NAME
        if not os.path.exists(path): # 判断文件夹是否已经存在
            os.mkdir(path)
        ii = int(strT_to_floatT(str_startT, unit='m')/RESOLUTION)  ## 五分钟的分辨率
        df.to_csv(os.path.join(path, str(ii)+'.csv.gz'), compression='gzip')
        lib_file.json_save(dict_accessed, os.path.join(path, str(ii)+'.json'))
        #break
    #ttt.duration(NAME)

###### 不同城市间采用多进程
#def main(list_names):
#    pool = multiprocessing.Pool(processes=8)
#    res = pool.map(func, list_names)  # res十个列表，列表里边是一个个字典
def execute(f,todo,threads):    
    data=[0,len(todo),time.time(),threads]
    
    def update(a):    
        data[0]=data[0]+1
        curt=time.time()
        elapsedt=curt-data[2]
        leftt=elapsedt*(data[1]-data[0])/data[0]
        
        print("Processing %d/%d, time spent: %0.1fs, time left: %0.1fs"%(data[0],data[1],elapsedt,leftt))
        
    pool = Pool(threads)
    #mulresAsync=[]
    for i in range(len(todo)):
        #mulresAsync.append(pool.apply_async(f, args=(todo[i],), callback=update))
        pool.apply_async(f, args=(todo[i],), callback=update)
    
    pool.close()
    pool.join()

    #return r
    
    
L=execute(func,list(dict_CityLocs.keys())[:48],8)
#main(list(dict_CityLocs.keys())[10:20])