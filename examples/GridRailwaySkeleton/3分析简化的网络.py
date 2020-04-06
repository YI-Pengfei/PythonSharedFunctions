import sys
sys.path.append(r'E:/pythonlibs')
import numpy as np
import pandas as pd
from rtree import index
import networkx as nx
from lib_timetable import Stations, Timetable
from lib_graph import createG_fromFile, getLocation_fromFile
from haversine import haversine
import lib_graph
from lib_plot import jointplotFromLists, ConvexHull


G_timetable = createG_fromFile('E:/OSM/OSMData/China/timetable_links.csv')
## 获取车站的位置， 不再使用精确的车站位置数据，而是使用简化的版本
#f_stations = "E:/Code/Data/ChinaRailway/China_Station_Location_City.xls"
f_nodes = 'china-gridded-nodes.csv'
stations_obj = Stations()
stations_obj.load_file(f_nodes)
dict_NameLoc = stations_obj.get_NameLoc_Index() # 创建一个 name:(lon,lat)的字典
dict_NameID = dict(zip(stations_obj.df['name'], stations_obj.df['ID']))


dict_IDLoc = lib_graph.getLocation_fromFile(f_nodes, ID='ID', lon='lon', lat='lat')
### 加载列车时刻表
fs = "E:/Code/Data/ChinaRailway/China_Railway_Schedule_20190701.csv"
timetable_obj = Timetable()
timetable_obj.load_file(fs)
df_timetable = timetable_obj.df
dict_pairT_timetable = timetable_obj.get_directTravelT()

### 简化的网络
f_links = 'china-gridded-links.csv'
f_nodes = 'china-gridded-nodes.csv'
G = createG_fromFile(f_links, source='source', target='target', attr='maxspeed')
for e in G.edges:
    o_loc = dict_IDLoc[e[0]]
    d_loc = dict_IDLoc[e[1]]
    dis = haversine((o_loc[1],o_loc[0]), (d_loc[1],d_loc[0]))	
    #maxspd = G[e[0]][e[1]]['maxspeed']
    maxspd = 200
    t = dis/maxspd*60  # 时间以min为单位
    G[e[0]][e[1]]['tempdistance_s'] = t

dict_locG = getLocation_fromFile(f_nodes)
### 看有多少连通片
components = list(sorted(nx.connected_components(G), key=len, reverse=True))
components = [list(c) for c in components]

dict_pairDis = {}  # 地理距离
dict_pairTrainT = {}  # 列车时刻表的真实旅行时间的中值
dict_pairDrivingT = {}  # OSRM路径规划的行车距离
dict_pairSkeletonT = {}  # 铁路骨架的旅行时间
dict_pairTimetableT = {}

for p in dict_pairT_timetable:
    s1, s2 = p[0], p[1]  # 出来的是 名字
    if not (s1 in dict_NameLoc and s2 in dict_NameLoc):
        continue
    loc1, loc2 = dict_NameLoc[s1], dict_NameLoc[s2]
    #dict_pairDis[p] = stations_obj.get_distance(s1,s2)
    dict_pairTrainT[p] = np.median(dict_pairT_timetable[p]) 
    #route,traveltime = osrm.queryRoute(loc1,loc2)
    #dict_pairDrivingT[p] = traveltime
    s1_id = dict_NameID[s1]
    s2_id = dict_NameID[s2]
    t = lib_graph.get_travelT(G,s1_id,s2_id)
    #if t==-1:
    #    print(s1,s2)
    #else:
    dict_pairSkeletonT[p] = t
    dict_pairTimetableT[p] = lib_graph.get_travelT(G_timetable, s1, s2)

hull = ConvexHull()
hull.add_list(list(dict_pairTimetableT.values()),list(dict_pairSkeletonT.values()))
hull.get_hull_points()
hull.display(s=0.1, texts = list(dict_pairSkeletonT.keys()),xlabel='Real travel time (mins)', ylabel='Skeleton network travel time (mins)')
