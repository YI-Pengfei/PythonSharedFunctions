"""
网格化方法简化网络
"""
import pandas as pd
import time
import sys
import networkx as nx
sys.path.append(r'/run/media/pengfei/OTHERS/pythonlibs')
import lib_osm
import lib_graph
import lib_time
from lib_timetable import Stations, Timetable
import matplotlib.pyplot as plt
import numpy as np
from rtree import index
from collections import defaultdict

def new_round(_float, _len):
    if str(_float)[-1] == '5':
        return(round(float(str(_float)[:-1]+'6'), _len))
    else:
        return(round(_float, _len))

ttt = lib_time.MeasureT()

f_stations = "/run/media/pengfei/OTHERS/Code/Data/ChinaRailway/China_Station_Location_City.xls"
stations_obj = Stations()
stations_obj.load_file(f_stations)
dict_NameLoc_stations = stations_obj.get_NameLoc_Index()

#dict_IDStations = {}  # 为车站点创建 ID与位置的映射，（其实直接用名字做映射也可以）
f_links = '/run/media/pengfei/OTHERS/OSM/OSMData/China/china-latest-rail-links.csv'
f_nodes = '/run/media/pengfei/OTHERS/OSM/OSMData/China/china-latest-rail-nodes.csv'
#G = lib_graph.createG_fromFile(f_links, source='source', target='target', attr='maxspeed')
df_links = pd.read_csv(f_links)

dict_IDLoc_nodes = lib_graph.getLocation_fromFile(f_nodes, ID='ID', lon='lon', lat='lat')

#### 2. 列出所有节点 (不列也行)
list_nodes = [v for k,v in list(dict_NameLoc_stations.items())+list(dict_IDLoc_nodes.items())]

r = 1/32
dict_Nodegrid = {}
dict_gridNodes = defaultdict(list)   # 聚集到一个格点的节点
for n_ID in dict_IDLoc_nodes:
    x,y = dict_IDLoc_nodes[n_ID]
    nearest_grid = round(x/r+0.5*r)*r, round(y/r+0.5*r)*r
    dict_gridNodes[nearest_grid].append(n_ID)  # 这里暂时有一个问题就是还是 位置:[n_id,n_id...]
    dict_Nodegrid[n_ID] = nearest_grid  

ttt.duration('Finished searching nearest grid points') 
    
#### 4. 用网格中节点的中值点代表网格点的位置
dict_gridNewlocations = {}
for grid in dict_gridNodes:
    n_IDs = dict_gridNodes[grid]
    n_locs = lib_osm.get_represent_point([dict_IDLoc_nodes[ID] for ID in n_IDs])
    dict_gridNewlocations[str(grid)] = n_locs  ## 做成一个字符串，以后用起来方便

#### 5. 传递节点间的连通关系,,确定 格点id 之间的连通关系
dict_links = {}
for row in df_links.itertuples():
    s_grid = dict_Nodegrid[row.source]
    t_grid = dict_Nodegrid[row.target]
    spd = row.maxspeed
    if s_grid==t_grid:
        continue
    link = tuple(sorted([s_grid,t_grid]))
    dict_links[link]=max(spd,dict_links[link]) if link in dict_links else spd


#### 6. 保存到文件，一个_nodes文件， 节点:id-lon/lat
f_out_nodes = 'china-gridded-nodes.csv'
lib_graph.saveLocation_toFile(dict_gridNewlocations,f_out_nodes)
#       一个_ways文件爱呢， 路径: fid,tid, maxspeed
f_out_links = 'china-gridded-links.csv'
out = [[*od, dict_links[od]] for od in dict_links]
df = pd.DataFrame(out, columns=['source','target','maxspeed'])
df.to_csv(f_out_links)

ttt.duration('Finished creating simplified network')    

G = lib_graph.createG_fromFile(f_out_links, source='source', target='target', attr='maxspeed')
lib_graph.plot_G(G, dict_gridNewlocations)

ttt.duration('Finished plotting')    