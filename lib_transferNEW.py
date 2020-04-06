""" Dijkstra单源最短路径算法在 列车换乘策略中的改版
    Dijkstra算法参考： https://blog.csdn.net/heroacool/article/details/51014824
"""
import networkx as nx
from prettytable import PrettyTable
import pandas as pd
import copy
from lib_time import get_deltaT, strT_to_floatT
import heapq

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


def update_Candidate(source, dict_Candidate, dict_Sure, G_schedule, heap):
    """ 根据已经确定的source节点的信息更新所有的路径 (扫描由这个新添节点出发，是否可以使得某些已有的路径变得更短)
        dict_Candidate: 已经存在的路径，但未确定最短路径的 节点 及其 方案
    """
    list_updates = []
    neighbors =  set(nx.neighbors(G_schedule,source)) - set(dict_Sure.keys())
    list_scheme_of_source = dict_Sure[source]
    for name in neighbors: 
        list_scheme, travelT = get_scheme(source, name, G_schedule, list_scheme_of_source)
        if not list_scheme:  ## 并没有生成可用的方案 (两车站虽然连通，但是考虑真实列车时是不可达的)
            continue
        # 如果新添了路径，或者路径变更短了，更新方案
        if name not in dict_Candidate \
            or dict_Candidate[name][-1]['total_travelT']>travelT \
            or (dict_Candidate[name][-1]['total_travelT']==travelT and  len(dict_Candidate[name])>len(list_scheme)):
            dict_Candidate[name] = list_scheme
            heapq.heappush(heap, (dict_Candidate[name][-1]['total_travelT'],name))  # 加入堆###########
            list_updates.append(name)
    
    return list_updates


#def determine_StillSure(dict_Candidate, G_schedule, G_scheme_pre, prepareT=15, RESOLUTION=10):
#    """ 根据现在的情况，判断之前的方案还能不能继续使用，如果能，直接生成新的方案 （避免不必要的重复计算）
#        应该在得到originInfo 之后执行这个操作
#        return: dict_StillSure: 本次仍然确定的出行方案 (也即搜索最短路径时可以将其排除)
#    """
#    dict_Can_copy = copy.deepcopy(dict_Candidate)
#    for source in dict_Can_copy:
#        pass
def _update_scheme(part1,old_scheme,RESOLUTION):
    # 两部分方案相结合， old_scheme的前半部分用part1,后半部分的 total_travelT 要随之改变
    list_scheme = copy.deepcopy(part1+old_scheme[len(part1):])

    for row in list_scheme[len(part1):]:
        row['total_travelT'] -= RESOLUTION  
    return list_scheme   

def update_successors(root_scheme, G_scheme, dict_Sure, dict_StillSure, RESOLUTION, G_stationPair,heap):
    """ 如果一个目的车站的到达时间没有发生改变，则其子树的所有车站的到达时间都不会有变化，直接更新他们的出行方案
        root_scheme: 到达时间没有改变的根节点 (出行方案已经更新过)
        G_scheme: 树
    """
    root = root_scheme[-1]['arrive_station']
    set_successors = set() ## 以root为根的所有子节点
    dict_successors = dict(nx.bfs_successors(G_scheme,source=root))
    for name in dict_successors:
        set_successors.add(name)
        for successor in dict_successors[name]:
            set_successors.add(successor)
  
    set_successors = set_successors - set(dict_Sure.keys())- set(dict_StillSure.keys())
    for name in set_successors:
        if 'scheme' not in G_scheme.node[name]:
            #print(name)
            continue
        dict_StillSure[name] = _update_scheme(root_scheme, G_scheme.node[name]['scheme'], RESOLUTION)  
        heapq.heappush(heap, (dict_StillSure[name][-1]['total_travelT'],name))  # 加入堆 ###############


def update_Candidate_based_before(source, dict_Candidate, dict_Sure, G_schedule, G_scheme,dict_StillSure,G_stationPair, heap, prepareT=15,RESOLUTION=10):
    """ 先判断前一个时间戳的出行方案能否继续使用
        根据已经确定的source节点的信息更新所有的路径 (扫描由这个新添节点出发，是否可以使得某些已有的路径变得更短)
        G_scheme: 上一个时间戳的出行方案建立的图(树)，节点上的属性时出行方案
    """
 
    list_updates = []
    neighbors =  set(nx.neighbors(G_schedule,source)) - set(dict_Sure.keys())#-set(dict_StillSure.keys())
    list_scheme_of_source = dict_Sure[source]
    last_arriveT = list_scheme_of_source[-1]['arrive']  # 到站时间
    for name in neighbors: 
        if name in dict_StillSure:
            dict_Candidate[name] = dict_StillSure[name]   #####################
            del dict_StillSure[name]   ########################################
            continue                   ########################################
        
        old_scheme = G_scheme.node[name]['scheme'] if (name in G_scheme and 'scheme' in G_scheme.node[name]) else []  # 找到这个点原来的出行方案
        
        #print(len(old_scheme),len(list_scheme_of_source),name,source)
        len_source = len(list_scheme_of_source)  # 新的源点的换乘方案的长度
        ## 尝试使用原来的方案：一定是比之前的方案中schedule daley小了，  #  #  查看换乘时间是否仍然充足; d_t 可能是负数，没有用编好的 get_deltaT 函数
        if len(old_scheme)>len_source \
            and old_scheme[len_source]['depart_station'] == source \
            and old_scheme[len_source]['train_code'] != 'carDriving' \
            and strT_to_floatT(old_scheme[len_source]['depart'],unit='m') - strT_to_floatT(last_arriveT, unit='m') >= prepareT \
            and strT_to_floatT(old_scheme[len_source]['depart'],unit='m') - strT_to_floatT(last_arriveT, unit='m') < get_deltaT(old_scheme[len_source-1]['arrive'], old_scheme[len_source]['depart'], unit='min'):   
            
            list_scheme = _update_scheme(list_scheme_of_source, old_scheme, RESOLUTION)

            travelT = list_scheme[-1]['total_travelT']
            #dict_StillSure[name] = list_scheme ### 知道 name是stillSure之后，它的子树也是确定的了，注意要更新总旅行时间
            ###################################################################
            update_successors(list_scheme, G_scheme, dict_Sure, dict_StillSure, RESOLUTION, G_stationPair, heap)  # 更新所有子树上的旅行时间
            ###################################################################
        else:  # 生成新的方案
            list_scheme, travelT = get_scheme(source, name, G_schedule, list_scheme_of_source)
            if not list_scheme:  ## 并没有生成可用的方案 (两车站虽然连通，但是考虑真实列车时是不可达的)
                continue                
        # 如果新添了路径，或者路径变更短了，更新方案
        if name not in dict_Candidate \
            or dict_Candidate[name][-1]['total_travelT']>travelT \
            or (dict_Candidate[name][-1]['total_travelT']==travelT and  len(dict_Candidate[name])>len(list_scheme)):
            dict_Candidate[name] = list_scheme
            heapq.heappush(heap, (dict_Candidate[name][-1]['total_travelT'],name))  # 加入堆 ###############
            list_updates.append(name)                

#        for name in dict_StillSure:
#            if name not in dict_Candidate or dict_Candidate[name][-1]['total_travelT']>dict_StillSure[name][-1]['total_travelT']:  # 新添了路径或路径更短了，添加/更新
#                dict_Candidate[name] = dict_StillSure[name]
#                list_updates.append(name)    


    return list_updates


def update_Candidate_cardriving(source, dict_Candidate, dict_Sure, G_stationPair, dict_StillSure, heap):
    """ 功能上与 update_Candidate 类似， 但是注意这里输入的图变为了 G_stationPair --> 两车站间驾车需要的时间
        （所以也就是说，update_Candidate 更新的是 从source出发，“乘坐火车”的路径，
                    而 本函数 更新的是 从source出发，“驾车”的路径）--> 模仿同城不同站换乘的情况
    """
    list_updates = []
    if source not in G_stationPair:  # 不存在短时间内驾车可达的车站，无需执行任何操作
        return []

    list_scheme_of_source = dict_Sure[source]
    last_arriveT = list_scheme_of_source[-1]['arrive']  # 到站时间
    past_travelT = list_scheme_of_source[-1]['total_travelT']  # 已用的总旅行时间
    neighbors =  set(nx.neighbors(G_stationPair,source)) - set(dict_Sure.keys()) - set(dict_StillSure.keys())  # 还是把确定的去掉 #####

    for name in neighbors:
        if name in dict_StillSure:
            dict_Candidate[name] = dict_StillSure[name]   #####################
            del dict_StillSure[name]      #####################################
            continue  #########################################################
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
            heapq.heappush(heap, (dict_Candidate[name][-1]['total_travelT'],name))  # 加入堆 ###############
            list_updates.append(name)

    return list_updates



def add_shortest2Sure(dict_Sure, dict_Candidate, dict_StillSure, heap):
    """ 在dict_Candidate中选出"一个"路径最短的节点（及其换乘信息）添加到dict_Sure中
    """
    # 2019.10.14改，在 dict_Candidate和 dict_StillSure两者中选择一个 最短的节点
    ## 弹出一个最短时间
    #while True:
    #tempT, tempname = heapq.heappop(heap)
    #print(tempname,tempT)
    tempname = ''
    tempT = 10**6
    for name in dict_Candidate:
        travelT = dict_Candidate[name][-1]['total_travelT']
        if travelT<tempT:
            tempname  = name  ## 选出一个最短路径的点，更新所有
            tempT = travelT
    
    for name in dict_StillSure:
        travelT = dict_StillSure[name][-1]['total_travelT']
        if travelT<tempT:
            tempname  = name  ## 选出一个最短路径的点，更新所有
            tempT = travelT        
#            
    if tempname in dict_Sure:
        #print(tempname, dict_Sure[tempname][-1]['total_travelT'], tempT)
        #print(dict_Sure[tempname])
        #print(dict_StillSure[tempname])
        print('该车站已存在')    ## 该车站已存在为什么还会发现它？？
        pass
    if tempname in dict_Candidate:
        dict_Sure[tempname] = dict_Candidate[tempname] # 添加到 确定 中
        del dict_Candidate[tempname]  # 并将其从 备选 中删除
        #break
    elif tempname in dict_StillSure:
        dict_Sure[tempname] = dict_StillSure[tempname] # 添加到 确定 中
        del dict_StillSure[tempname]  # 并将其从 备选 中删除  
        #break
#    #print('shorest path for %s found.'%tempname)
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
        if delta_t>24*60 or delta_t<prepareT:  # 接续换乘等待时间不太长，也不太短
            continue
        this_during = info['travel_time']  # 本次列车的运行时间，min
        travelT = past_travelT + delta_t + this_during  # 已用 + 换乘 + 本次
        if travelT< min_travelT:
            min_travelT = travelT
            out_info.update(info)

            out_info['total_travelT'] = travelT
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