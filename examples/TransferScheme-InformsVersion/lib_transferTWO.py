""" 为兼容航空特制的 包---> 有对应的主程序
    Dijkstra单源最短路径算法在 列车换乘策略中的改版
    Dijkstra算法参考： https://blog.csdn.net/heroacool/article/details/51014824
"""
import networkx as nx
from prettytable import PrettyTable
import pandas as pd
import copy
from lib_time import get_deltaT, strT_to_floatT


def get_driving_origins(G_HSRGrid,originGrid,str_startT):
    """ 确定从家里出发，驾车可达的源车站
        return: 
    """
    startT = strT_to_floatT(str_startT,unit='m')  ## min 
    dict_ChildInfo = {}
    carAccessHSR = list(nx.neighbors(G_HSRGrid,originGrid))  ## 1.5小时内开车到达的车站
    ### 组装一个初始的 dict_ChildInfo 字典
    for s in carAccessHSR: 
        int_arriveT = startT + round(G_HSRGrid[s][originGrid]['duration_s']/60) # min 为单位
        arriveT = str((int_arriveT%1440)//60).zfill(2)+':'+str(int((int_arriveT%1440)%60)).zfill(2)  # 字符串
        dict_ChildInfo[s] = {'train_code': 'carDriving',
                             'depart_station': '--', 'arrive_station': s,
                             'depart': str_startT, 'arrive': arriveT,
                             }

        dict_ChildInfo[s]['travel_time'] = get_deltaT(str_startT, arriveT, unit='min') 
        dict_ChildInfo[s]['total_travelT'] = dict_ChildInfo[s]['travel_time']
 
    return dict_ChildInfo


def update_Candidate(source, dict_Candidate, dict_Sure, G_schedule):
    """ 根据已经确定的source节点的信息更新所有的路径 (扫描由这个新添节点出发，是否可以使得某些已有的路径变得更短)
        dict_Candidate: 已经存在的路径，但未确定最短路径的 节点 及其 方案
    """
    ##### 2019.11.10 新添，限制最大换乘次数为2
    modes = set([s['train_code'] for s in dict_Sure[source]]) - {'carDriving'}
    if len(modes)>=3:  ## Car之外的交通方式多于3段，证明换乘次数超过了2次
        return []

    ###### 2019.10.16 加 根据source类型，设置不同的prepareT
    if G_schedule.nodes[source]['type']=='station': # 车站，准备时间为15mins
        prepareT = 15
    else:                                           # 机场，准备时间为60mins
        prepareT = 60   
        
    list_updates = []
    neighbors =  set(nx.neighbors(G_schedule,source)) - set(dict_Sure.keys())
    list_scheme_of_source = dict_Sure[source]
    for name in neighbors: 
        list_scheme, travelT = get_scheme(source, name, G_schedule, list_scheme_of_source, prepareT=prepareT)
        if not list_scheme:  ## 并没有生成可用的方案 (两车站虽然连通，但是考虑真实列车时是不可达的)
            continue
        # 如果新添了路径，或者路径变更短了，更新方案
        if name not in dict_Candidate \
            or dict_Candidate[name][-1]['total_travelT']>travelT \
            or (dict_Candidate[name][-1]['total_travelT']==travelT and  len(dict_Candidate[name])>len(list_scheme)):
            dict_Candidate[name] = list_scheme
            list_updates.append(name)
    
    return list_updates



def update_Candidate_cardriving(source, dict_Candidate, dict_Sure, G_stationPair, dict_StillSure):
    """ 功能上与 update_Candidate 类似， 但是注意这里输入的图变为了 G_stationPair --> 两车站间驾车需要的时间
        （所以也就是说，update_Candidate 更新的是 从source出发，“乘坐火车”的路径，
                    而 本函数 更新的是 从source出发，“驾车”的路径）--> 模仿同城不同站换乘的情况
    """
    list_updates = []
    if source not in G_stationPair:  # 不存在短时间内驾车可达的车站，无需执行任何操作
        return []

    list_scheme_of_source = dict_Sure[source]
    ### 2019.10.16加，这个车站本身就是驾车到达的，不要再驾车去其他车站了，直接返回
    if list_scheme_of_source[-1]['train_code']=='carDriving':
        return []        

    last_arriveT = list_scheme_of_source[-1]['arrive']  # 到站时间
    past_travelT = list_scheme_of_source[-1]['total_travelT']  # 已用的总旅行时间
    neighbors =  set(nx.neighbors(G_stationPair,source)) - set(dict_Sure.keys()) - set(dict_StillSure.keys())  # 还是把确定的去掉 #####

    for name in neighbors:
        driveT = round(G_stationPair[source][name]['duration_min'])  # 从source到name
        totalT = past_travelT + driveT
        if name not in dict_Candidate or dict_Candidate[name][-1]['total_travelT']>totalT:  # 新添了路径或路径更短了，添加/更新
            # 生成这段的出行方案
            info = {'train_code': 'carDriving',
                    'depart_station': source, 'arrive_station': name,
                    'depart': last_arriveT}

            int_arriveT = strT_to_floatT(last_arriveT, unit='m') + driveT  # min 为单位
            info['arrive'] = str((int_arriveT%1440)//60).zfill(2)+':'+str(int((int_arriveT%1440)%60)).zfill(2)  # 字符串
            info['travel_time'] = driveT
            info['total_travelT'] = totalT
            
            #if name not in dict_Candidate or len(dict_Candidate[name])>len(list_scheme_of_source + [info]):  ## 2019.10.14 改
            dict_Candidate[name] = list_scheme_of_source + [info]
            list_updates.append(name)

    return list_updates



def add_shortest2Sure(dict_Sure, dict_Candidate):
    """ 在dict_Candidate中选出"一个"路径最短的节点（及其换乘信息）添加到dict_Sure中
    """
    tempname = ''
    tempT = 10**6
    for name in dict_Candidate:
        travelT = dict_Candidate[name][-1]['total_travelT']
        if travelT<tempT:
            tempname  = name  ## 选出一个最短路径的点，更新所有
            tempT = travelT
            
    if tempname in dict_Sure:
        print('该车站已存在')    
        print(dict_Sure[tempname], dict_Candidate[tempname] )
        pass
    dict_Sure[tempname] = dict_Candidate[tempname] # 添加到 确定 中
    del dict_Candidate[tempname]  # 并将其从 备选 中删除
    #print('shorest path for %s found.'%tempname)
    return tempname


def get_scheme(source, target, G_schedule, list_scheme_of_source, prepareT=15):
    """
    在起终点之间所有的列车中，选择使得总旅行时间最短的列车
    :param source: 出发车站
    :param target: 目的车站
    :param G_schedule: 列车时刻表建的有向图
    :param list_scheme_of_source: 节点source的最短旅行方案
    :param prepareT: 准备时间 15mins
    :return: 输出 (从源点出发的)方案列表，及总旅行时间
    """
    last_arriveT = list_scheme_of_source[-1]['arrive']  # 前车的到站时间
    past_travelT = list_scheme_of_source[-1]['total_travelT']  # 在以前已经用掉的旅行时间

    all_trains = G_schedule[source][target]

    min_travelT = 10**6  # 设置一个足够大的旅行时间
    out_info = {'depart_station':source,'arrive_station':target}
    for ID in all_trains:
        info = all_trains[ID]

        departT = info['depart']
        delta_t = get_deltaT(last_arriveT, departT, unit='min')  # 前车到站时间 和 下趟车出发时间 的比较
        ##################################
        ######################################################################
        if delta_t>3*60 or delta_t<prepareT:  # 接续换乘等待时间不太长，也不太短   最长纯等待时间 3h
            continue
        this_during = info['travel_time']  # 本次列车的运行时间，min
        travelT = past_travelT + delta_t + this_during  # 已用 + 换乘 + 本次
        if travelT< min_travelT:
            min_travelT = travelT
            out_info.update(info)

            out_info['total_travelT'] = min_travelT
            #out_info['total_travelT_h'] = str(travelT//60).zfill(2)+':'+str((travelT%60)).zfill(2)  # 字符串
    if not 'train_code' in out_info:  ## 并没有产生有效的接续换乘策略(正常情况下不会出现)
        return [],10**6
    
    list_schemes = list_scheme_of_source+[out_info]
    return list_schemes, out_info['total_travelT']

###########
def create_G_scheme(dict_Sure):
    """ 由生成的方案建图
    """    
    G_scheme = nx.DiGraph()
    for name in dict_Sure:
        G_scheme.add_node(name,scheme=dict_Sure[name])
        if len(dict_Sure[name])==1:
            continue
        for i in range(len(dict_Sure[name])-1,0,-1):
            G_scheme.add_edge(dict_Sure[name][i-1]['arrive_station'],dict_Sure[name][i]['arrive_station'])

    return G_scheme

def show_scheme(list_scheme):
    """ 显示出行方案
    """
    #out = dict_Sure[name]
    out = list_scheme
    table = PrettyTable(["train_code", "source", "target", "departure","arrival","during time","total time"])
    totalT = out[-1]['total_travelT']
    for row in out:
        row = [row['train_code'],row['depart_station'],row['arrive_station'],row['depart'],row['arrive'],row['travel_time'],row['total_travelT']]
        table.add_row(row)
    
    print('Transfer scheme is as follow, travel time:',str(totalT//60).zfill(2)+':'+str((totalT%60)).zfill(2))  # 字符串)
    print(table)

def save_scheme(dict_Sure):
    """ 将出行方案保存为dataframe
    """
    dict_Sure = dict(sorted(dict_Sure.items(), key=lambda item:item[1][-1]['total_travelT'], reverse=False))
    list_temp = []
    for name in dict_Sure:
        list_scheme = dict_Sure[name]
        for row in list_scheme:
            row = [row['train_code'],row['depart_station'],row['arrive_station'],row['depart'],row['arrive'],row['travel_time'],row['total_travelT']]
            list_temp.append( [name]+ row )
    
    df = pd.DataFrame(list_temp, columns=['destination', 'train_code', 'depart_station', 'arrive_station', 'depart', 'arrive', 'travel_time', 'total_travelT'])
    return df