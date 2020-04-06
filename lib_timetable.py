"""
    2019.10.16 complete "FlightTimetable" class
    2019.09.24 cross-day issue is considered for train travel.
	2019.09.11 add supports for Air timetable.
    2019.08.30 add mode options (HSR or ALL), and travel time options (direct or all) 
    
Common functions related to railway timetable(schedule)
temporary, Chinese timetable is in CSV format, while Europe timetale is in XML format.
"""
import pandas as pd
import networkx as nx

import re
from collections import defaultdict
from haversine import haversine


class FlightTimetable:
    """ 航班时刻表
		相比于铁路时刻表要简单一些
    """
    def __init__(self):
        self.set_norm()
    
    def set_norm(self):
        """ 按照时刻表的表头进行相应的设定
        """
        self.norm = {}
        self.norm['ID'] = 'flightNumber'
        self.norm['aID'] = 'arrivalAirportTlc'     ## 到达机场 (目的地)  对应的是 iata号
        self.norm['dID'] = 'departureAirportTlc'   ## 出发机场
        self.norm['arriveT'] = 'arrivalDate'
        self.norm['departT'] = 'departureDate'

    def load_file(self,f):
        """ 加载航班时刻表数据，csv/excel类型，每个航班占一行
        """
        self.df = pd.read_csv(f)  ## 暂时只支持csv,且编码是gbk 
        
    def get_travelT(self):
        """ 计算机场间的旅行时间, 是无向的
            return: (o,d):[t1,t2,...] 的字典
        """
        pass  ### 暂时略过
    
#    def get_graph(self):
#        """ 由 起点与目的地建 无权、无向 图
#            (这个功能跟lib_graph里边的功能是相同的)
#        """
#        G = nx.Graph()
#        #return nx.from_pandas_edgelist(self.df, source=self.norm['dID'], target=self.norm['aID']) # , attr='tempdistance_s' 
#        for row in self.df.itertuples():
#            o = getattr(row, self.norm['dID'])
#            d = getattr(row, self.norm['aID'])
#            G.add_edge(o,d)
#            G[o][d][getattr(row,self.norm['ID'])] = 1  ## 属性为航班号
#        return G


    def get_DiGraph(self, CH_name=True):
        """ 给出两两机场间所有航班的信息， 有向图
            CH_name: 为方便测试，可以选择为图中的节点添加中文名
            
            return 有向图      
            (这张图里包含详细的信息，其他的图都可以由这张图进行生成)
            (飞机建图要简单许多，一行就是一个航班)
        """        
        G = nx.DiGraph()  # 有向图
        for row in self.df.itertuples():
            flight_number = getattr(row, self.norm['ID'])  # 航班号
            o = getattr(row, self.norm['dID'])  # 出发机场 IATA号
            d = getattr(row, self.norm['aID'])  # 到达机场 
            
            depart_t = getattr(row, self.norm['departT']) # 起飞时间
            arrive_t = getattr(row, self.norm['arriveT']) # 到达时间
            travelT = get_deltaT(depart_t, arrive_t, unit='min', mode='auto')  # 飞行时间

            ### 构建信息，存入图中
            info = {'train_code':flight_number,  # 为了与铁路兼容， 也命名为 'train_code'
                    'depart':depart_t,
                    'arrive':arrive_t,
                    'travel_time':travelT,
                    }
            G.add_edge(o,d)
            G[o][d][flight_number] = info  # 为边添加属性 列车号:起发、持续时间的图
            
        if CH_name:
            dict_iata_name = dict(zip(self.df['arrivalAirportTlc'], self.df['arrivalAirportName']))
            dict_iata_city = dict(zip(self.df['arrivalAirportTlc'], self.df['arrivalCityName']))
            for name in G.nodes:
                G.node[name]['ch_name']= dict_iata_name[name]
                G.node[name]['city']= dict_iata_city[name]

        return G                    




class Timetable:
    """ 暂时只支持 Chinese timetable
    """
    def __init__(self):
        self.set_norm()
        self.dict_NameTraincodes = defaultdict(set)  ## 车站，和经过的列车的车号
        #self.G_travelT = nx.Graph()  # 两两车站之间旅行时间组成的图
    
    def load_file(self,f,mode='HSR',encoding='gbk'):
        """ 加载数据
            mode:  1. 'HSR': 只保留C,D,G字头 的动车组列车
                   2. 'ALL': 保留加载的时刻表文件中的所有列车
        """
        if f.endswith('.csv'):
            self.df = pd.read_csv(f,encoding=encoding) # ,encoding='utf-8'
        elif f.endswith('.xls') or f.endswith('.xlsx'):
            self.df = pd.read_excel(f,encoding=encoding)
        else:
            print('initialization failed. Unsupported file format! ')
            self.df = None    
            
        if mode=='HSR':
            self.df['HSR'] = self.df[self.norm['ID']].map(lambda x: bool(re.search(r'^C|^D|^G',x)))
            self.df = self.df[self.df['HSR']==True]
        elif mode=='ALL':
            self.df = self.df
        
        self.stations = list(set(self.df[self.norm['name']]))
        self.trainIDs = list(set(self.df[self.norm['ID']]))
        
        self.dict_IDTrain = {}

    def set_norm(self):
        """ 按照时刻表的表头进行相应的设定
        """
        self.norm = {}
        self.norm['ID'] = 'train_code'
        self.norm['name'] = 'station_name'
        self.norm['stopID'] = 'stop_id'
        self.norm['arriveT'] = 'arrive_time'
        self.norm['departT'] = 'depart_time'

    def get_df(self):
        return self.df
    
    def get_train(self, ID, colName='train_code'):
        """ 给定列车号，返回该列车的sub dataframe
        """
        return self.df[self.df[colName]==ID]

    def convert_trains(self):
        """ 将Dataframe表示的列车转换
        """
        self.hsr_stations = set()
        last_code =  self.df.iloc[0][self.norm['ID']]
        sub = []
        for row in self.df.itertuples():
            self.hsr_stations.add(getattr(row, self.norm['name']))
            if getattr(row, self.norm['ID']) == last_code:
                sub.append(row)
            else:
                self.dict_IDTrain[last_code] = sub
                last_code = getattr(row, self.norm['ID']) 
                sub = [row]
        
        self.dict_IDTrain[last_code] = sub
        self.hsr_stations = list(self.hsr_stations)
        #return dict_IDTrain
    
    
    def get_TrainCodes_of_station(self, station):
        """ 获取经过某车站的所有列车的列车号
            station: 车站名
        """
        if not self.dict_NameTraincodes:
            for row in self.df.itertuples():
                self.dict_NameTraincodes[ getattr(row, self.norm['name']) ].add(getattr(row, self.norm['ID']))

        #sub = self.df[self.df[self.norm['name']]==station]
        return list(self.dict_NameTraincodes[station])
    
    
    def get_graph(self, mode='all'):
        """ 由车站间的联通关系建 无向、无权 简单图
            mode:   1. direct: 只连接一辆车中两两直接相连
                    2. all: 一辆车中的所有节点都互联        
        """	
        G = nx.Graph()
        if not self.dict_IDTrain:
            self.convert_trains()   # 提取出每个列车的时刻表
        
        for ID in self.dict_IDTrain:
            train = self.dict_IDTrain[ID]  # 一个pandas列表
            for i in range(len(train)-1):  # 前一个
                name0 = getattr(train[i], self.norm['name'])
                for j in range(i+1,len(train)):  # 后一个
                    name1 = getattr(train[j], self.norm['name'])
                    if name0==name1:  ## 起点终点相同，环线，不添加
                        continue
                    G.add_edge(name0, name1)   #### 加边
                    G[name0][name1][ID] = 1   ##加车次信息
                    if mode=='direct':  # 只计算直连的车站对，跳出内循环
                        break

        return G
    

    def get_DiGraph(self,mode='all'):
        """ 给出两两车站间所有列车的信息， 有向图
            mode:   1. direct: 只计算两两直接相连的车站之间的旅行时间
                    2. all: 只要两车站同时被一列火车连接，就计算旅行时间
            return 有向图      
            (这张图里包含详细的信息，其他的图都可以由这张图进行生成)
        """
        if not self.dict_IDTrain:  ##还不存在需要的形式
            self.convert_trains()
        
        G = nx.DiGraph()  # 有向图
        for ID in self.dict_IDTrain:  # 遍历每趟列车
            train = self.dict_IDTrain[ID]  # 一个pandas列表
            # 0. 准备，把每一站的 到达时间，出发时间 全取出来备用
            list_adTs = []  ## 这一大段都是为了处理欧洲 arrival，departure时间不全的问题
            for row in train:
                at, dt = getattr(row, self.norm['arriveT']), getattr(row, self.norm['departT'])
                temp = []
                if re.sub(r'-|:','', at).isdigit():
                    temp.append(at)
                if re.sub(r'-|:','', dt).isdigit():
                    temp.append(dt)
                if not temp:
                    print('Error! invalid time for station:', getattr(row, self.norm['name']))
                list_adTs.append(temp)  ### temp也是一个列表，存arrival time和departure time 
                ## 这个list_atTs就把所有的时间按顺序存起来了
                
                
            for i in range(len(train)-1): # 前站
                name0 = getattr(train[i], self.norm['name'])
                for j in range(i+1,len(train)):  # 后站
                    name1 = getattr(train[j], self.norm['name'])
                    if name0==name1:
                        print('Same name error？%s:%s->%s'%(train[i].train_code,name0,name1))   
                        continue ## 环线的记录本身没意义
                    ### 计算两站之间的列车的开行时间，2019.09.28，采用一种新的计算方法，所有时间点两两求差的和
                    #### 1. 存储一系列有意义的 时间
                    list_t = [list_adTs[i][-1]] # 起点 选一个departure time 
                    for ij in range(i+1,j):
                        list_t += list_adTs[ij]
                    list_t.append(list_adTs[j][0]) # 终点 选一个arrival time

                    #### 2. 两两求差，计算旅行时间，自动确定是否隔天
                    travelT = 0
                    for i_ij in range(len(list_t)-1):
                        #######################################################
                        ###############  2019.10.06 这里计算太复杂，得改一下 ########################
                        travelT += get_deltaT(list_t[i_ij], list_t[i_ij+1], unit='min', mode='auto')
                        #######################################################
                        #######################################################
                    ### 计算两站之间列车的开行时间，完
                    info = {'train_code':ID,
                            'depart':list_adTs[i][-1],
                            'arrive':list_adTs[j][0],
                            'travel_time':travelT,
                            }
                    G.add_edge(name0,name1)
                    G[name0][name1][ID] = info  # 为边添加属性 列车号:起发、持续时间的图
                    
                    if mode=='direct':  # 只计算直连的车站对，跳出内循环
                        break
        return G                    

############### 2019.11.13 加，从服务的角度讲，两地之间的所有列车服务的记录 #######
def get_service_df(G_schedule, typ):
    """ 上述 列车，或飞机 建立的有向图转化成 两站 之间的服务
        typ: 'train', 'flight'
    """
    ### 先建立一个服务与id号之间的索引
    dict_serviceID = {}   ## 这是 详细信息（字符串型):序号
    dict_IDservice = {}  ## 这是 序号:详细信息(字典型)
    ii = 0
    for e in G_schedule.edges:
        dict_services = G_schedule.edges[e]
        for service in dict_services.values():
            service.update({'depart_station':e[0],'arrive_station':e[1],'type':typ})  
            dict_serviceID[str(service)] = ii
            dict_IDservice[ii] = service
            ii+=1
    
    all_services = []
    for ID in dict_IDservice:
        prefix = 'f' if typ=='flight' else 't'
        all_services.append(dict( dict_IDservice[ID], **{'id':prefix+str(ID)} ))
    
    df_service = pd.DataFrame(all_services, columns=['id','depart_station', 'arrive_station', 'depart', 'arrive', 'train_code', 'travel_time','type'])
    return df_service

import sqlite3
def get_service_db(df_service, db_name):
    """ 数据库形式保存 dataframe
    """
    con = sqlite3.connect(db_name)
    cursor = con.cursor()
    cursor.execute('DROP TABLE IF EXISTS service')
    cursor.execute('CREATE TABLE service ( id VARCHAR (20), depart_station VARCHAR(20), arrive_station VARCHAR(20), depart VARCHAR(20) , arrive VARCHAR(20), train_code VARCHAR(20), travel_time INT, type VARCHAR(20))')
    for row in df_service.itertuples():
        cursor.execute ("INSERT INTO service \
                        (id, depart_station, arrive_station, depart, arrive, train_code, travel_time, type) \
                        VALUES (? ,? ,? ,?,? ,? ,? ,?)" ,tuple(list(row[1:])))

    cursor.close() # close cursor
    con.commit() # commit transaction
    con.close() # close connection    



############### 2019.09.30 加 一些辅助的画图#####################################
from lib_plot import plotLine, plot_From_Locations, plot_plot
import matplotlib.pyplot as plt

def plot_trainPoints(list_stations, dict_locs,):
    list_locs = [dict_locs[name] for name in list_stations]
    m = plot_From_Locations(list_locs,s=2,fpath=None,x=900,y=600,dpi=100,color='r',marker='.')
    return m

def plot_stations(m, list_stations, dict_locs, name=None,color='blue',marker='D',s=2):
    list_locs = [dict_locs[name] for name in list_stations]
    list_x, list_y = zip(*list_locs)
    list_x, list_y = m(list_x,list_y)
    
    l1 = plt.scatter(list_x,list_y,c=color,zorder=4, alpha=0.5,marker=marker, s=s)
    return l1

def plot_trainpoints(m, list_trains, dict_locs, name=None,color='blue',marker='D',s=2):
    """ list_trains: 一列车的车站 
    """
    list_locs = []
    for train in list_trains:
        list_locs += [dict_locs[s] for s in train] ## 把车站的位置存成了列表
    list_locs = list(set(list_locs))    
    list_x, list_y = zip(*list_locs)
    list_x, list_y = m(list_x,list_y)
    
    l1 = plt.scatter(list_x,list_y,c=color,zorder=4, alpha=0.8,marker=marker, s=s)
    return l1

def plot_trainlines(m,list_trains, dict_locs, name=None,color='blue'):
    # 2. 再画线
    for train in list_trains:
        list_locs = [dict_locs[s] for s in train] ## 把车站的位置存成了列表
        list_x, list_y = zip(*list_locs)
        plot_plot(m, list_x, list_y,color=color,alpha=1,linewidth=0.2)
    # 3.如果想要标出那个点，
    if name:
        m.scatter(dict_locs[name][0], dict_locs[name][1], s=4, zorder=4,c='red')
        plt.text(dict_locs[name][0], dict_locs[name][1], name, fontsize='small') 
        

def plot_trainLines(list_trains, dict_locs, name=None):
    """ 画出列车的行车路线图
        list_trains:  一个 存有列车经过的车站顺序的列表 例如 [[s1,s2,s3], [s2,s3,s1]] 代表存储了两辆车的信息
        dict_locs: 车站名:位置 的字典
    """
    # 1. 先画点
    list_locs = []
    for train in list_trains:
        list_locs += [dict_locs[s] for s in train] ## 把车站的位置存成了列表
    list_locs = list(set(list_locs))
    m = plot_From_Locations(list_locs,s=2,fpath=None,x=900,y=600,dpi=100,color='r',marker='.')
    # 2. 再画线
    for train in list_trains:
        list_locs = [dict_locs[s] for s in train] ## 把车站的位置存成了列表
        list_x, list_y = zip(*list_locs)
        plot_plot(m, list_x, list_y,color='blue',alpha=1,linewidth=0.2)
#        for i in range(len(list_locs)-1):
#            lon1,lat1 = list_locs[i]
#            lon2,lat2 = list_locs[i+1]
#            plotLine(m,lon1,lat1,lon2,lat2,color="blue",lwd=0.5,lty="-",alpha=0.7,linewidth=1.5)
    # 3.如果想要标出那个点，
    if name:
        m.scatter(dict_locs[name][0], dict_locs[name][1], s=4, zorder=4,c='red')
        plt.text(dict_locs[name][0], dict_locs[name][1], name, fontsize='small') 
    

class Stations:
    """ 车站的相关信息，例如 name, location 等
    """
    def __init__(self):
        self.set_norm()
        
    def load_file(self,f):
        if f.endswith('.csv'):
            self.df = pd.read_csv(f,encoding='utf-8')
        elif f.endswith('.xls') or f.endswith('.xlsx'):
            self.df = pd.read_excel(f,encoding='utf-8')
        else:
            print('initialization failed. Unsupported file format! ')
            self.df = None  
        self.dict_NameLocation = {}
        
    def set_norm(self):
        """ 按照车站位置列表的表头进行相应的设定
        """
        self.norm = {}
        self.norm['name'] = 'name'
        self.norm['lon'] = 'lon'
        self.norm['lat'] = 'lat'
    
    def get_NameLoc_Index(self):
        """ 创建一个 name:[lon,lat] 的字典
        """
        IDs = self.df[self.norm['name']]
        if len(set(IDs))<len(IDs):
            print('Warning, attribute not unique')
        
        locations = list(zip(self.df[self.norm['lon']],self.df[self.norm['lat']]))
        self.dict_NameLocation = dict(zip(IDs, locations))
        return self.dict_NameLocation


    def get_distance(self, s1, s2, unit='km'):
        """ 获取两车站间的距离
            s1, s2: 车站名
        """
        if not self.dict_NameLocation:
            self.get_NameLoc()
        
        if self.if_have(s1) and self.if_have(s2):
            loc1 = self.dict_NameLocation[s1]
            loc2 = self.dict_NameLocation[s2]
            return haversine((loc1[1],loc1[0]), (loc2[1],loc2[0]))
        else:
            return -1  # 数据集中没有该车站的位置，返回一个不合逻辑的距离
        
    def if_have(self, s):
        """ 判断数据集中是否含有该车站
        """
        return s in set(self.df[self.norm['name']])

    def get_loc(self, s):
        """ 获取车站的位置，
            s: 车站名
        """
        if not self.if_have(s):
            print('No station %s!'%s)
        if not self.dict_NameLocation:
            self.get_NameLoc()
        return self.dict_NameLocation[s]

###############################################################################

def get_deltaT(t0, t1, unit='min', mode='auto',delta_day=None):
    """计算时间差， 自动确定是否隔天，（这里不考虑隔两天的情况）
       t: string. Two formats are supported:  1) "hh:mm"
                                              2) "hhmm"
       unit: 单位    1) "min"  int类型  
                    2) "h"    float类型
                    3) "h:m"  string类型 
    
       mode:   1."auto" 自动确定是否隔天;  2. "manual" 手动指定相差的天数
    """
    if not (isinstance(t0,str) and isinstance(t1,str)):
        print('Inputs are not strings.')
        return -1
    
    t0 = int(t0.replace(':',''))
    t1 = int(t1.replace(':',''))
    if mode=='manual' and delta_day:  ### 手动指定了相差的天数
        t1 = int(t1) + delta_day*2400
    else:   ### 没有指定相差的天数，则 t1小于t0时就 自动加一天
        if t1 < t0: # 隔天
            t1 = int(t1) + 2400
    
    h0, m0 = int(t0/100), int(t0%100)
    h1, m1 = int(t1/100), int(t1%100)
    
    delta = (h1*60+m1) - (h0*60+m0)
    if unit=='min':
        return delta  # int
    elif unit=='h':
        return delta/60
    elif unit=='h:m':
        return str(int(delta/60)).zfill(2) + ':' + str(delta%60).zfill(2)
    
    
    

def strT_to_floatT(t_str, unit='h'):
    """
    :param t_str:  "hh:mm"形式 或 "hhmm"形式
    :param unit:  'h' -- 以小时为单位， 'm'--以分钟为单位
    :return:  浮点数 xx.xx
    """
    t_str = t_str.replace(':','').zfill(4)
    if not t_str.isdigit():
        print(t_str)
        print('Error, invalid time format!')
        return None
        
    h, m = int(t_str[:2]), int(t_str[2:])
    if unit == 'h':
        return h + m/60
    elif unit == 'm':
        return h*60 + m
    else:
        print('Wrong unit!')
        return None