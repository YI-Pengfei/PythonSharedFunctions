import sys
sys.path.append(r'E:/Gitlab/pythonsharedfunctions.git')
import pandas as pd
import lib_file
from lib_timetable import Timetable
import lib_grid
import networkx as nx
import lib_graph

#### 1. 铁路
timetable_obj = Timetable()
timetable_obj.load_file('E:/Code/Data/ChinaRailway/China_Railway_Schedule_20190701.csv')
timetable_obj.convert_trains()

df_railwayLocs = lib_file.read_file2df('E:/Code/Data/ChinaRailway/China_Station_Location_City.xls')
dict_railwayLocs = lib_file.get_LocIndex(df_railwayLocs)
dict_HSRLocs = {}  ## 高铁站 名:位置
for name in dict_railwayLocs:
    if name in timetable_obj.hsr_stations:
        dict_HSRLocs[name] = dict_railwayLocs[name]
        
#### 2. 飞机
df_airports = pd.read_csv('E:/Code/Data/ChinaAir/China_Airports.csv',encoding='gbk')
dict_AirportLocs = lib_file.get_LocIndex(df_airports,key='iata_code',lon='longitude_deg',lat='latitude_deg')

#df_schedule = pd.read_csv('E:/Code/Data/ChinaAir/China_Air_Schedule_clean.csv')

#### 3.1 建立高铁车站与服务的格点之间的映射
G_hsr_grid = nx.Graph()  # 车站<-->可服务的格点
for name in dict_HSRLocs: # dict_HSRLocs    dict_AirportLocs
    list_grids = lib_grid.get_gridArea(dict_HSRLocs[name], 1/32, 50)     ## 服务距离设置为50米    
    for grid in list_grids:
        G_hsr_grid.add_edge(grid,name)


#### 3.2 建立机场与服务的格点之间的映射
G_air_grid = nx.Graph()  # 车站<-->可服务的格点
for iata in dict_AirportLocs:
    list_grids = lib_grid.get_gridArea(dict_AirportLocs[iata], 1/32, 150)     ## 服务距离设置为50米    
    for grid in list_grids:
        G_air_grid.add_edge(grid,iata)    
    
        
##### 5.保存这两个 图映射关系
lib_graph.saveG_toFile(G_hsr_grid,"graph_GridHSR.csv")
lib_graph.saveG_toFile(G_air_grid,"graph_GridAir.csv")
        
### 6.把机场、车站位置也保存，以方便使用
lib_file.pickle_save(dict_AirportLocs,'dict_AirportLocs.pkl')
lib_file.pickle_save(dict_HSRLocs,'dict_HSRLocs.pkl')