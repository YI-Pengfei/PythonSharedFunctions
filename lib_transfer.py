import networkx as nx
from prettytable import PrettyTable
from lib_time import get_deltaT, strT_to_floatT, floatT_to_strT


def get_driving_origins(G_HSRGrid,originGrid,str_startT):
    startT = strT_to_floatT(str_startT,unit='m')  ## min 
    dict_ChildInfo = {}
    carAccessHSR = list(nx.neighbors(G_HSRGrid,originGrid))  ## 1.5小时内开车到达的车站
    ### 组装一个初始的 dict_ChildInfo 字典
    for s in carAccessHSR: 
        int_arriveT = startT + round(G_HSRGrid[s][originGrid]['duration_s']/60) # min 为单位
        arriveT = str((int_arriveT%1440)//60).zfill(2)+':'+str(int((int_arriveT%1440)%60)).zfill(2)  # 字符串
        dict_ChildInfo[s] = {}
        dict_ChildInfo[s]['train_code'] = 'carDriving'
        dict_ChildInfo[s]['depart'] = str_startT
        dict_ChildInfo[s]['arrive'] = arriveT
        dict_ChildInfo[s]['travel_time'] = get_deltaT(str_startT, arriveT, unit='min') 
        dict_ChildInfo[s]['total_travelT'] = int_arriveT-startT ## 浮点数
 
    return dict_ChildInfo


def get_scheme(source, target, G_schedule, dict_parents, prepareT=15):
    """ 在起终点之间 找最早的一班列车==》 是到达时间最早(总旅行时间最短)
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
        ##################################
        ######################################################################
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


def get_accessHSRs(G_schedule, dict_parents, dict_accessed, set_excludes=set()):
    """ 由第N层已经到达的车站的信息，确定可到达的第N+1层的车站的信息
        G_schedule: 列车时刻表建立的有向图
        dict_parents: 第N层可到达的车站的信息 (例如已用的旅行时间，列车到站时间)
        dict_accessed: 汇总的前N层中到达各站最短的旅行时间
    """
    dict_ChildInfo = {}
    for s in dict_parents: # 父
        ####### 2019.10.11加
        if s in set_excludes:
            continue
        #######
        neighbors =  list(nx.neighbors(G_schedule,s))
        for n in neighbors: # 子
            ####### 2019.10.11加
            if s in set_excludes:
                continue
            #######
            info = get_scheme(s, n, G_schedule, dict_parents)
            if not 'train_code' in info:  ## 并没有产生有效的接续换乘策略
                continue
            ##############################################################################
            ##############################################################################
            #if (n in dict_accessed) and (info['total_travelT'] - dict_accessed[n]>=-0.01): ## 现在是以分钟为单位，应该不需要后边这个条件了
            if (n in dict_accessed) and (info['total_travelT'] - dict_accessed[n]>=-0.1): ## 现在是以分钟为单位，应该不需要后边这个条件了
                continue
            if (n not in dict_ChildInfo) or (dict_ChildInfo[n]['total_travelT'] > info['total_travelT']):
                dict_ChildInfo[n] = info              
    
    return dict_ChildInfo


def extend_accessHSRs(dict_ChildInfo, dict_accessed, G_stationPair ):
    """  接上步，在获取了第N+1层的车站的信息之后，计算一定时间内可开车到达的车站
         以便同城异站换乘
    """             
    dict_extendInfo = {}
    for name in dict_ChildInfo:
        if not name in G_stationPair:  ## 这个车站周围不存在 20分钟 车程就可到达的车站
            continue
        info = dict_ChildInfo[name]
        neighbors =  list(nx.neighbors(G_stationPair,name))  ## 20分钟车程可到的车站
        for n in neighbors:
            ######################## 2019.10.11 去掉了这个限制
            #if n in dict_ChildInfo: ##在前N层 或 第N+1层被访问过，略掉  n in dict_accessed or 
            #    continue
            temp_info = {}
            driveT = round(G_stationPair[name][n]['duration_min'])
            totalT = info['total_travelT']+driveT
            
            if (n not in dict_extendInfo) or (dict_extendInfo[n]['total_travelT'] > totalT): # 碰到了新的或更小的
                if n in dict_accessed and dict_accessed[n]<=totalT:
                    continue
                
                for k in info:
                    temp_info[k] = info[k]
                temp_info['middle'] = info['to']
                temp_info['middle_arrive'] = info['arrive']
                at = (strT_to_floatT(info['arrive'], unit='m')+ driveT)%1440
                temp_info['arrive'] = str(at//60).zfill(2)+':'+str((at%60)).zfill(2)
                temp_info['to'] = n
                temp_info['total_travelT'] = totalT 
                
                dict_extendInfo[n] =  temp_info
    
    return dict_extendInfo


###############################################################################
def construct_scheme(list_layerAccess, dest):
    """ 根据零散的 list_layerAccess，及目的地，生成出行方案
        倒着找，是最少旅行时间，最多换乘的
    """
     
    if dest in list_layerAccess[0]:
        scheme = list_layerAccess[0][dest]
        #dict_distScheme[dest] = scheme
        #print('Directly car driving accessible')
        return []
    
    scheme = []
    for i in range(len(list_layerAccess)):
        j = len(list_layerAccess) - i-1
        if dest in list_layerAccess[j]: ### 在这层里，
            info =  list_layerAccess[j][dest]
            last_station = info['from']
            scheme.insert(0,info)
            while j>1:
                j-=1
                info =  list_layerAccess[j][last_station]
                last_station = info['from']    
                scheme.insert(0,info)
            break
    
    if not scheme:
        #print('No transfer scheme for station %s'%dest)
        return []
    
    info =  list_layerAccess[0][last_station]   
    scheme.insert(0,info)
    out = []
    
    for i in range(len(scheme)):
        train_code = scheme[i]['train_code']
        source = scheme[i].get('from','--')
        if i+1<len(scheme):
            destination = scheme[i+1].get('from','--')
        else:
            destination=dest
        dt = scheme[i].get('depart','--')
        at = scheme[i].get('arrive','--')
        
        if 'middle' in scheme[i]:  ## 中间有乘车转站
            midT = scheme[i].get('middle_arrive','--')
            out.append([train_code,source,scheme[i]['middle'],dt,midT, get_deltaT(dt, midT, unit='min')])
            out.append(['carDriving',scheme[i]['middle'],destination,midT,at, get_deltaT(midT, at, unit='min')])
        else:
            travelT = scheme[i].get('travel_time')
            out.append([train_code,source,destination,dt,at,travelT])
        
    table = PrettyTable(["train_code", "source", "target", "departure time","arrival time","travel time"])

    for row in out:
        table.add_row(row)
    totalT = str(scheme[-1]['total_travelT']//60).zfill(2)+':'+str(scheme[-1]['total_travelT']%60).zfill(2)
    #print('Transfer scheme is as follow, travel time:',totalT)
    #print(table)
        
    return out    

def show_scheme(out):
    table = PrettyTable(["train_code", "source", "target", "departure time","arrival time","travel time"])

    for row in out:
        table.add_row(row)
    totalT = calculate_travelT_from_scheme(out)
    print('Transfer scheme is as follow, travel time:',totalT)
    print(table)

def get_all_schemes(list_layerAccess,dict_HSRLocs):
    dict_nameScheme = {}
    if not list_layerAccess:  #### 允许 list_layerAccess 中没有方案(初始化时没有)
        return dict_nameScheme
    #count = 0
    for name in dict_HSRLocs:
        scheme = construct_scheme(list_layerAccess, name)
        if scheme:
            dict_nameScheme[name]=scheme
        #if name in dict_nameScheme and len(dict_nameScheme[name])==2:  ## 无需换乘的情况
            #print(dict_nameScheme[name])
        #    count+=1
    
    return dict_nameScheme


################ 2019.10.11 ###################################################
def calculate_travelT_from_scheme(list_scheme):
    """ 由各段的换乘方案计算总的旅行时间
    """
    if len(list_scheme)==1:
        return list_scheme[0][5]
    totalT = 0
    for i in range(len(list_scheme)-1):
        travelT = list_scheme[i][5]
        schedule_delay = get_deltaT(list_scheme[i][4], list_scheme[i+1][3], unit='min')
        totalT += travelT+schedule_delay
    totalT += list_scheme[-1][5]
    #print("Total travel time",str(totalT//60).zfill(2)+':'+str(totalT%60).zfill(2))
    return totalT