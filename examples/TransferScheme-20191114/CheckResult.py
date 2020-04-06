import os
import sys
OS = 'E:/' #'/run/media/pengfei/OTHERS/' # 
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
from haversine import haversine


## 位置  id:(lon,lat)
dict_HSRLocs = lib_graph.getLocation_fromFile(OS+'Code/Data/Sebastian_ScheduleDataChina20191114/stations.csv', ID='ID', lon='lon', lat='lat')
dict_AirportLocs = lib_graph.getLocation_fromFile(OS+'Code/Data/Sebastian_ScheduleDataChina20191114/airports.csv', ID='ID', lon='lon', lat='lat')
dict_PortLocs = copy.deepcopy(dict_HSRLocs)
for k in dict_AirportLocs:
    dict_PortLocs[k] = dict_AirportLocs[k]

org_loc = eval(originGrid)
for ID in dict_accessed:
    travelT = dict_accessed[ID]
    loc = dict_PortLocs[ID]
    dis = haversine(  (org_loc[1],org_loc[0]), (loc[1],loc[0])  )