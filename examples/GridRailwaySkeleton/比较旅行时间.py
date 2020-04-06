import sys
sys.path.append(r'/run/media/pengfei/OTHERS/pythonlibs')
import numpy as np
from lib_time import MeasureT
from lib_timetable import Stations, Timetable
from lib_osm import queryRoute
from lib_plot import jointplotFromLists
######### 加载车站位置数据
fl = "/run/media/pengfei/OTHERS/Code/Data/ChinaRailway/China_Station_Location_City.xls"
stations_obj = Stations(fl)
dict_NameLoc = stations_obj.get_NameLoc_Index()

fs = "/run/media/pengfei/OTHERS/Code/Data/ChinaRailway/China_Railway_Schedule_20190701.csv"
timetable_obj = Timetable(fs)
df_timetable = timetable_obj.df
dict_pairT_timetable = timetable_obj.get_directTravelT()

tdd = MeasureT()  # 开始计时

dict_pairDis = {}  # 地理距离
dict_pairTrainT = {}  # 列车时刻表的真实旅行时间的中值
dict_pairDrivingT = {}  # OSRM路径规划的行车距离

for p in dict_pairT_timetable:
    s1, s2 = p[0], p[1]
    if not (s1 in dict_NameLoc and s2 in dict_NameLoc):
        continue
    loc1, loc2 = dict_NameLoc[s1], dict_NameLoc[s2]
    dict_pairDis[p] = stations_obj.get_distance(s1,s2)
    dict_pairTrainT[p] = np.median(dict_pairT_timetable[p]) 
    route,traveltime = queryRoute(loc1,loc2)
    dict_pairDrivingT[p] = traveltime

tdd.duration()  # 计时结束

jointplotFromLists(dict_pairDrivingT.values(),dict_pairTrainT.values(),'OSRM driving Time','HSR schedule')
jointplotFromLists(dict_pairDis.values(),dict_pairTrainT.values(),'Distance','HSR schedule')
jointplotFromLists(dict_pairDis.values(),dict_pairDrivingT.values(),'Distance','OSRM driving Time')
