# -*- coding: utf-8 -*-
"""
   2019.11.14 堆优化

@author: y1064
"""
import re
import pandas as pd
import networkx as nx

import heapq
from pprint import pprint
import lib_graph
import lib_file


class TimetableNew:
    def __init__(self):
        self.dict_trains={}  ## schedule中的顺序是：[depStationID, depTime, arrStationID, arrTime,info]
        self.list_flights = []  #  保持与train一样的顺序：[depStationID, depTime, arrStationID, arrTime,info]

    def load_trainFile(self, f, mode='ALL', encoding='utf-8'):
        f=open(f, "rt", encoding='utf-8')
        #self.dict_trains={}  ## schedule中的顺序是：[depStationID, depTime, arrStationID, arrTime,info]
        for line in f.readlines():  # 有航班号相同的情况
            code, schedule = eval(line)
            if mode=='ALL' or (mode=='HSR' and bool(re.search(r'^C|^D|^G',code))) :
                self.dict_trains[code]=schedule
        
        f.close()
        
    def load_flightFile(self, f):
        df = pd.read_csv(f)
        for row in df.itertuples():
            self.list_flights.append([row.source, row.depTime_s, row.target, row.arrTime_s, row.flightNumber+':'+row.info ])
            
    def get_DiGraph(self, mode='all'):
        """ 给出两两车站间所有列车的信息， 有向图
            mode:   1. direct: 只计算两两直接相连的车站之间的旅行时间
                    2. all: 只要两车站同时被一列火车连接，就计算旅行时间
        """  
        day_s = 24*3600  # 一天的秒数  
        G = nx.DiGraph()
        # 1. trains
        for ID in self.dict_trains:
            train = self.dict_trains[ID]

            for i,row in enumerate(train):
                dept_id,dt,arr_id,at, describe = row  

                during = at-dt if at-dt>0 else at-dt+day_s  # 旅行持续时间，秒为单位
#                if during<=0:
#                    print('wwww',ID,at,dt)
                G.add_edge(dept_id,arr_id)
                ## 为边添加信息，[depart, dt, arrive, at, during, describe] (时间已经回到24小时之内)
                G[dept_id][arr_id][ID] = [dept_id,dt%day_s,arr_id, at%day_s, during, str(ID)+':' +describe]
                if mode=='direct':  ## 只直连， 就没有第二层循环了
                    continue
                ## 不然向下延伸 
                for j in range(i+1,len(train)):
                    row2 = train[j]
                    _, _, arr_id, at, describe_post = row2   #前两个都没用
                    if arr_id==dept_id:
                        #print('same name:',arr_id)
                        continue

                    during = at-dt if at-dt>0 else at-dt+day_s
                    if during<=0:
                        print('wwww',ID,at,dt)
                    
                    G.add_edge(dept_id,arr_id)
                    ## 为边添加信息，depart, dt, arrive, at, during (时间已经回到24小时之内)
                    G[dept_id][arr_id][ID] = [dept_id, dt%day_s, arr_id, at%day_s, during, str(ID)+':' +describe.split('->')[0] + '->' + describe_post.split('->')[1]]
        
        # 2. flights
        for flight in self.list_flights:
            dept_id, dt, arr_id, at, describe = flight
            ID = describe.split(':')[0]
            during = at -dt
            if during<=0:
                print('wwww')
            G.add_edge(dept_id,arr_id)
            ## 为边添加信息，depart, dt, arrive, at, during (时间已经回到24小时之内)
            G[dept_id][arr_id][ID] = [dept_id, dt%day_s, arr_id, at%day_s, during, describe]
        
        #self.G_schedule = G
        return G

""" 2. 换乘策略
"""


class TransferRoute:
    def __init__(self):
        self.heap = []
        self.dict_Sure = {} ## 存储已经找到最短路径的点 
        self.dict_Candidate = {} ## 存储找到路径的
        #heapq.heappush(self.heap, (travelT, station_name ))  ## 可以接受元组， (travelT, station_name)
        #heapq.heappop(self.heap)
        
    def load_airports(self, f):
        self.dict_airport_IDName = lib_file.creat_dict_from_CSV(f,'ID','IATA')
        self.dict_airport_IDName = lib_file.creat_dict_from_CSV(f,'IATA','ID')
    def load_stations(self, f):
        self.dict_station_IDName = lib_file.creat_dict_from_CSV(f,'ID','name')
        self.dict_station_NameID =  lib_file.creat_dict_from_CSV(f,'name','ID')

        
    def get_driving_origins(self, G_HSRGrid, originGrid, startT):
        """ 确定从家里出发，驾车可达的源车站
            startT: 以一天中的秒为单位的时间
        """
        day_s = 24*3600  # 一天的秒数  
        startT = startT % day_s  ## 为了避免输入错误
        
        dict_ChildInfo = {}
        carAccess = list(nx.neighbors(G_HSRGrid,originGrid))  
        ### 组装一个初始的 dict_ChildInfo 字典
        for s in carAccess: 
            driveT = round(G_HSRGrid[s][originGrid]['duration_s'])
            if driveT>=2*3600:   ## 寻找2小时之内驾车可达的车站/机场 #############################
                continue
            at = startT + driveT
            
            dict_ChildInfo[s] = {'train_code': 'Car',
                                 'dept_id': '--', 'arr_id': s,
                                 'deptT': startT, 'arrT': at%day_s,
                                 }
    
            dict_ChildInfo[s]['during'] = at-startT if at-startT>0 else at-startT+day_s  # 旅行持续时间，秒为单位
            dict_ChildInfo[s]['totalT'] = dict_ChildInfo[s]['during']  # 秒为单位
            ## 进栈
            heapq.heappush(self.heap, (dict_ChildInfo[s]['totalT'], s) ) ## (旅行时间，车站id) 进栈

        ### 1.2 构造成方案列表的形式
        for name in dict_ChildInfo:
            self.dict_Candidate[name] = [dict_ChildInfo[name]]
        #return dict_ChildInfo
    
    
    def add_shortest2Sure(self):
        """ 2019.11.14 使用堆栈 而不是顺序查找最小的车站(节点) 复杂度从 O(n)降到O(logn)
            在self.dict_Candidate中选出一个路径最短的节点（及其换乘信息）添加到self.dict_Sure中
        """
        travelT, tempname = heapq.heappop(self.heap)        
        while tempname not in self.dict_Candidate:  ## 可能是旧的旅行时间，弹出来
            travelT, tempname = heapq.heappop(self.heap)
        
        if not travelT ==  self.dict_Candidate[tempname][-1]['totalT']:
            print('heap wrong')

#        tempname = ''
#        tempT = 10**6
#        for name in self.dict_Candidate:
#            travelT = self.dict_Candidate[name][-1]['totalT']
#            if travelT<tempT:
#                tempname  = name  ## 选出一个最短路径的点，更新所有
#                tempT = travelT
#                
#        if tempname in self.dict_Sure:
#            print('该车站已存在')    
#            print(self.dict_Sure[tempname], self.dict_Candidate[tempname] )
#            pass

        self.dict_Sure[tempname] = self.dict_Candidate[tempname] # 添加到 确定 中
        del self.dict_Candidate[tempname]  # 并将其从 备选 中删除
        #print('shorest path for %s found.'%tempname)
        return tempname


    def update_Candidate(self, source, list_scheme_of_source, G_schedule, maxHops=3, AirProcess=60,TrainProcess=15):
        """ 根据已经确定的source节点的信息更新所有的路径 (扫描由这个新添节点出发，是否可以使得某些已有的路径变得更短)
            self.dict_Candidate: 已经存在的路径，但未确定最短路径的 节点 及其 方案
            maxHops: 最大允许几跳 （换乘次数+1）
        """

        ##### 2019.11.10 新添，限制最大换乘次数为2
        modes = set([s['train_code'] for s in list_scheme_of_source]) - {'Car'}
        if len(modes)>=maxHops:  ## Car之外的交通方式多于3段，证明换乘次数超过了2次
            return []
        ##### 2019.12.08 新添，限制最大旅行时间为24h
        if list_scheme_of_source[-1]['totalT']>24*3600: ## 旅行时间超过24h，不再进行更新
            return []
        ##### 2019.10.16 加 根据source类型，设置不同的prepareT #### 火车15min, 飞机60min
        #prepareT = 15*60 if G_schedule.nodes[source]['type']=='station' else 60*60  # 秒为单位
        prepareT = TrainProcess*60 if G_schedule.nodes[source]['type']=='station' else AirProcess*60  # 秒为单位

        list_updates = []
        neighbors =  set(nx.neighbors(G_schedule,source)) - set(self.dict_Sure.keys())
        
        for name in neighbors:
            if name not in G_schedule: ## 20191208加，欧洲有的机场没有航班
                continue
            list_scheme, travelT = self._get_scheme(source, name, G_schedule, list_scheme_of_source, prepareT)
            if not list_scheme:  ## 并没有生成可用的方案
                continue
            ## 如果新添了路径，或者路径变短了，更新方案
            if name not in self.dict_Candidate \
                or self.dict_Candidate[name][-1]['totalT']>travelT \
                or (self.dict_Candidate[name][-1]['totalT']==travelT and  len(self.dict_Candidate[name])>len(list_scheme)):
                self.dict_Candidate[name] = list_scheme
                ## 进栈  但是问题是旧的旅行时间没有弹出来 
                heapq.heappush(self.heap, (travelT ,name) )  
                list_updates.append(name)
        
        return list_updates

##   not used any longer.
        
#    def update_Candidate_cardriving(self, source, G_stationPair):
#        
#        list_updates = []
#        if source not in G_stationPair:  # 不存在可以异站换乘的车站、机场
#            return []
#        list_scheme_of_source = self.dict_Sure[source]
#        ### 2019.10.16加，这个车站本身就是驾车到达的，不要再驾车去其他车站了，直接返回
#        if list_scheme_of_source[-1]['train_code']=='Car':
#            return []        
#        
#        last_arriveT = list_scheme_of_source[-1]['arrT']  # 前车的到站时间
#        past_travelT = list_scheme_of_source[-1]['totalT']  # 在以前已经用掉的旅行时间
#        neighbors =  set(nx.neighbors(G_stationPair,source)) - set(self.dict_Sure.keys())
#        
#        for name in neighbors:
#            driveT = round(G_stationPair[source][name]['duration_s'])  ## 秒为单位的驾车时间
#            travelT = past_travelT + driveT
#            if name not in self.dict_Candidate or self.dict_Candidate[name][-1]['totalT']>travelT:
#                ### 组成方案
#                out_info = {
#                        'train_code': 'Car',
#                        'deptT': last_arriveT, 'arrT': (last_arriveT+driveT)%(24*3600),  ## 发车时间，到站时间
#                        'dept_id':source,'arr_id':name,
#                        'during': driveT, 'totalT':travelT, 
#                        }
#                ## 加入，进栈
#                self.dict_Candidate[name] = list_scheme_of_source + [out_info]
#                heapq.heappush(self.heap, (travelT ,name) )  
#                list_updates.append(name)
#                
#        return list_updates


    def get_Drivings(self, source, G_stationPair):
        """ 2019.11.14 加，在确定了一个节点source的最短旅行时间并添加进self.dict_Sure之后
            除由source直接同站换乘之外， 即 update_Candidate 的功能
            还可以先驾车到其他临近车站，由临近车站接续换乘
            **本程序就是先计算驾车到达临近车站的时间**
        """
        dict_Drivings = {}
        if source not in G_stationPair:  # 不存在可以驾车到达的临近车站
            return dict_Drivings

        list_scheme_of_source = self.dict_Sure[source]
        ### 2019.10.16加，这个车站本身就是驾车到达的，不要再驾车去其他车站了，直接返回
        if list_scheme_of_source[-1]['train_code']=='Car': ## 这种情况应该只在开始是出现
            return {}                

        last_arriveT = list_scheme_of_source[-1]['arrT']  # 前车的到站时间
        past_travelT = list_scheme_of_source[-1]['totalT']  # 在以前已经用掉的旅行时间
        neighbors =  set(nx.neighbors(G_stationPair,source)) - set(self.dict_Sure.keys())
        
        for name in neighbors:
            driveT = round(G_stationPair[source][name]['duration_s'])  ## 秒为单位的驾车时间
            ### 其实还是应该控制一下， 现在 去火车站 和 去机场 都是1h
            travelT = past_travelT + driveT
            
            if name not in self.dict_Candidate or self.dict_Candidate[name][-1]['totalT']>travelT:
                ### 组成方案
                out_info = {
                        'train_code': 'Car',
                        'deptT': last_arriveT, 'arrT': (last_arriveT+driveT)%(24*3600),  ## 发车时间，到站时间
                        'dept_id':source,'arr_id':name,
                        'during': driveT, 'totalT':travelT, 
                        }

                dict_Drivings[name] = list_scheme_of_source + [out_info]
        
        return dict_Drivings   ## 返回source车站驾车 可扩展的


    
    def _get_scheme(self, source, target, G_schedule, list_scheme_of_source, prepareT):
        """ 在起终点之间所有的列车中，选择总旅行时间最短的列车
            所有的时间都是以 秒 为单位
        """
        last_arriveT = list_scheme_of_source[-1]['arrT']  # 前车的到站时间
        past_travelT = list_scheme_of_source[-1]['totalT']  # 在以前已经用掉的旅行时间
        
        all_trains = G_schedule[source][target]
        
        min_travelT = 10**6*(24*3600)  # 设置一个足够大的旅行时间
        temp_service = [] ## 放置服务信息
        out_info = {}
        for ID in all_trains:
            info = all_trains[ID]   ### 这里的info是列表 [depart, dt, arrive, at, during, describe]
            departT = info[1]
            delta_t = departT-last_arriveT
            delta_t = delta_t if delta_t>=0 else delta_t+24*3600 ## 处理隔天
            ######################################## 2019.12.06 改，改用15小时 ########################
            if not 0<=delta_t-prepareT<24*3600-prepareT:  ## 纯等待时间不超过15个小时 ############################
                continue
            ###### 20191208加，第一段的纯等待时间不超过1小时
#            if len(list_scheme_of_source)==1 and delta_t-prepareT>=1*3600:
#                continue
            
            this_during = info[4]
            travelT = past_travelT + delta_t + this_during
            if travelT < min_travelT:
                min_travelT = travelT
                out_info['train_code'] = ID
                temp_service = info
            
        if not temp_service:
            return [], 10**6*(24*3600)
        out_info.update({'describe': temp_service[-1],
                'deptT': temp_service[1], 'arrT': temp_service[3],  ## 发车时间，到站时间
                'dept_id':source,'arr_id':target,
                'during': temp_service[4], 'totalT':min_travelT, 
                })
    
        list_schemes = list_scheme_of_source+[out_info]
        return list_schemes, out_info['totalT']        

###############################################################################
### 车站与网格的驾车时间图
### 3.1 车站<-->网格 1 hours
#f_HSRGrid = OS+'Code/Data/ChinaRailway/China_StationGridAccessibility_1h_5mins.csv'  # 分辨率是1/12度
#G_HSRGrid = lib_graph.createG_fromFile(f_HSRGrid, source='station', target='grid', attr=['distanceLBS_m','duration_s'])     
### 3.2 机场<-->网格 2 hours
#f_AirGrid = OS+'Code/HSR+AIR/data/China_AirportGridAccessibility_2h_5mins.csv'
#G_AirGrid = lib_graph.createG_fromFile(f_AirGrid, source='station', target='grid', attr=['distanceLBS_m','duration_s'])
### 3.3 合并
#G_PortGrid = nx.compose(G_HSRGrid,G_AirGrid)  ## 二者连成一张图
### 3.4 为节点添加类型标示
#def add_type2G(G, df_railwayLocs, dict_AirportLocs):
#    ## 为图中的节点添加类型标示， "station" or "airport"
#    for name in G:  ## 为图节点添加属性
#        if name in df_railwayLocs: # 火车站
#            G.node[name]['type']= 'station'
#        elif name in dict_AirportLocs:
#            G.node[name]['type']= 'airport'    
#    return G
#
#G_PortGrid = add_type2G(G_PortGrid, dict_HSRLocs, dict_AirportLocs)
### relabel一下
#df_HSRLocs = pd.read_csv(OS+'Code/Data/Sebastian_ScheduleDataChina20191113/stations.csv')
#df_AirportLocs = pd.read_csv(OS+'Code/Data/Sebastian_ScheduleDataChina20191113/airports.csv')
#station_id = dict(zip(df_HSRLocs.name, df_HSRLocs.ID))
#airport_id = dict(zip(df_AirportLocs.IATA, df_AirportLocs.ID))
#mapping =  dict( station_id, **airport_id )
#exclude = set()
#for name in mapping:
#    if name not in G_PortGrid:
#        exclude.add(name)
#for e in exclude:
#    del mapping[e]
#nx.relabel_nodes(G_PortGrid, mapping,copy=False)
#lib_file.pickle_save(G_PortGrid,'G_PortGrid.pkl')