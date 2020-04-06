# -*- coding: utf-8 -*-
"""
Created on Wed Nov 13 17:12:01 2019

@author: y1064
"""

import os
import sys
OS = '/run/media/pengfei/OTHERS/' # 
sys.path.append(OS+'Gitlab/pythonsharedfunctions.git')

import lib_graph
from lib_timetableNewStructure import TimetableNew, TransferRoute
import lib_timetableNewStructure
import copy
import networkx as nx
import pandas as pd
import lib_file
import lib_grid
import lib_time
from collections import defaultdict
import lib_plot

## 位置  id:(lon,lat)
dict_HSRLocs = lib_graph.getLocation_fromFile(OS+'Code/Data/Sebastian_ScheduleDataChina20191114/stations.csv', ID='ID', lon='lon', lat='lat')
dict_AirportLocs = lib_graph.getLocation_fromFile(OS+'Code/Data/Sebastian_ScheduleDataChina20191114/airports.csv', ID='ID', lon='lon', lat='lat')
dict_PortLocs = copy.deepcopy(dict_HSRLocs)
for k in dict_AirportLocs:
    dict_PortLocs[k] = dict_AirportLocs[k]
## 异站换乘driving time 
G_PortPort = lib_graph.createG_fromFile(OS+'Code/Data/Sebastian_ScheduleDataChina20191114/drivingTime.csv', source='source', target='target', attr=['contype','distance_km','duration_s'])
## 车站到网格的驾车时间
G_PortGrid = lib_file.pickle_load('G_PortGrid.pkl')
###############################################
### 时刻表建图
timetable = TimetableNew()
timetable.load_trainFile(OS+'Code/Data/Sebastian_ScheduleDataChina20191114/trains.txt')
timetable.load_flightFile(OS+'Code/Data/Sebastian_ScheduleDataChina20191114/flights.csv')
G_schedule = timetable.get_DiGraph(mode='all')
for name in G_schedule:  ## 为图节点添加属性
    G_schedule.node[name]['type']= 'airport' if name in dict_AirportLocs else 'station'

""" 5.城市中心坐标数据
"""
ffff = OS+'Code/Data/ChinaRailway/China_cities_population.csv'
df_pops = pd.read_csv(ffff)
dict_CityLocs = dict(zip(df_pops.name,df_pops.location))




""" Program Start
"""
NAME='北京市'
originGrid = str(lib_grid.get_nearestGrid(eval(dict_CityLocs[NAME]),1/12))  # 分辨率 1/12度， 5弧分
RESOLUTION=10

ttt = lib_time.MeasureT()  ##### 开始计时

startT = 7*3600  #  start

transfer_obj = TransferRoute()  ### 建立一个换乘对象 #######################
### 1.1 初始化，从家cardriving可达的车站
transfer_obj.get_driving_origins(G_PortGrid,originGrid,startT)

#
while transfer_obj.dict_Candidate:
    selected = transfer_obj.add_shortest2Sure()  ## 从这站开始
    dict_drivings = transfer_obj.get_Drivings(selected, G_PortPort)  ## 从这站先驾车到其他站，再换乘
    ### part1,先selected节点为换乘站做同站换乘
    list_scheme_of_source = transfer_obj.dict_Sure[selected]
    transfer_obj.update_Candidate(selected, list_scheme_of_source, G_schedule)
    ## part2, 再以 dict_drivings中的节点为换乘站做异站换乘
    for node in dict_drivings:
        list_scheme_of_source = dict_drivings[node]
        transfer_obj.update_Candidate(node, list_scheme_of_source, G_schedule)

#    updates2 = transfer_obj.update_Candidate_cardriving(selected, G_PortPort)



dict_Sure = transfer_obj.dict_Sure
### 简化结果，只取最短时间，不要路径
dict_accessed = {}
for name in dict_Sure:
    dict_accessed[name] = dict_Sure[name][-1]['totalT']
ttt.duration('Scheme ready')    






##### 车站id与车站名的映射，方便观察
#dict_stationIDName = lib_file.creat_dict_from_CSV(OS+'Code/Data/Sebastian_ScheduleDataChina20191114/stations.csv','ID','name')
#dict_airportIDName = lib_file.creat_dict_from_CSV(OS+'Code/Data/Sebastian_ScheduleDataChina20191114/airports.csv','ID','IATA')
#
#dict_stationNameID =  lib_file.creat_dict_from_CSV(OS+'Code/Data/Sebastian_ScheduleDataChina20191114/stations.csv','name','ID')

#
#dict_a = {}
#for ID in dict_accessed:
#    if ID in dict_stationIDName:
#        dict_a[dict_stationIDName[ID]] = round(dict_accessed[ID]/60)
#    else:
#        dict_a[dict_airportIDName[ID]] = round(dict_accessed[ID]/60)
#
#
### 4. 将可达车站扩展到可达的区域
dict_AccessArea = defaultdict(list)

for name in dict_accessed:
    if name not in G_PortGrid:
        #print(name,dict_HSRLocs[name])
        continue
    neighbors = list(nx.neighbors(G_PortGrid, name))
    for grid in neighbors:
        dict_AccessArea[grid].append(dict_accessed[name]+G_PortGrid[grid][name]['duration_s'])

dict_AccessAreaMin={}  ### 选出最短的旅行时间
for p in dict_AccessArea:
    dict_AccessAreaMin[p] = min(dict_AccessArea[p])

dict_4hours = {}
for grid in dict_AccessAreaMin:
    if dict_AccessAreaMin[grid]<=6*60*60:
        dict_4hours[grid] = dict_AccessAreaMin[grid]

lib_file.json_save(dict_4hours ,'dict_4hours.json')
#### 5.1 画图
###  imshow的底图+ 带colorbar的散点图
#x,y = zip(*[eval(k) for k in dict_AccessAreaMin.keys()])
#z = list(dict_AccessAreaMin.values())
#
#xs = []
#ys = []
#zs = []
#for i,v in enumerate(z):
#    if v/60/60<=30:             ########### 新版的时间是分钟制
#        xs.append(x[i])
#        ys.append(y[i])
#        zs.append(v/60/60)
#x,y,z=xs,ys,zs
#
#implot = lib_plot.ImPlot(OS+'Gitlab/pythonsharedfunctions.git/China.png',region='China')
#lib_plot.scatter_with_colorbar(x,y,z, s=0.5,vmax=20, vmin=0 ) # 
#implot.plot_points(eval(originGrid)[0],eval(originGrid)[1],marker='x',color='black',alpha=0.5,s=10,text=None)
##implot.plot_point(121.451093,31.25151,marker='+',color='green',alpha=1,markersize=10)
##plt.title(ppinyin.get_pinyin(NAME, '').capitalize()+' '+str_startT)
##ii = int(strT_to_floatT(str_startT,unit='m')/RESOLUTION)  ## 五分钟的分辨率
#
##path = OS+'每日总结/20191110/%s'%NAME
##if not os.path.exists(path): # 判断文件夹是否已经存在    
##    os.mkdir(path)
#implot.imshow(  )    #fpath=os.path.join(path,str(ii))

