# -*- coding: utf-8 -*-
"""
Created on Sun Aug 25 15:35:09 2019

@author: y1064
"""
from haversine import haversine
import networkx as nx
import math
import pandas as pd

import matplotlib.pyplot as plt
from matplotlib import collections

import copy

def _load_f2df(f):
    if f.endswith('.csv') or f.endswith('.csv.gz'):
        return pd.read_csv(f,encoding='utf-8')
    elif f.endswith('.xls') or f.endswith('.xlsx'):
        return pd.read_excel(f,encoding='utf-8')
    else:
        print('initialization failed. Unsupported file format! ')
        return None    

def createG_fromFile(f_links, source='IDfrom', target='IDto', attr='tempdistance_s'):
    """ Creat an undirected graph from csv file.
        f_links: csv/excel file with : fromID,toID, weight (edgelist Dataframe)
        attr: both string and list are supported, to provide much information.
                For example: attr='tempdistance_s' and attr=['tempdistance_s', 'dist'] are all supported.
    """
    df = _load_f2df(f_links)
    if attr:
        try:
            out = nx.from_pandas_edgelist(df, source,target, attr )  # 还可以有更多 例如: 'cost', 'XXX'
        except:
            out = nx.from_pandas_dataframe(df, source,target, attr )  # 还可以有更多 例如: 'cost', 'XXX'
        return out
    else: 
        try:
            out = nx.from_pandas_edgelist(df, source,target)  # 还可以有更多 例如: 'cost', 'XXX'
        except:
            out = nx.from_pandas_dataframe(df, source,target)  # 还可以有更多 例如: 'cost', 'XXX'
        return out


def saveG_toFile(G,f):
    """ Save a graph to csv file. 
        f: csv/excel file with : fromID,toID, weight (edgelist Dataframe)
    """
    df = nx.to_pandas_edgelist(G) # 至少包含 'source', 'target', ......
    df.to_csv(f)


def getLocation_fromFile(f, ID='ID', lon='lon', lat='lat'):
    """ 创建一个 name:[lon,lat] 的dictionary
        f: CSV file.
    """
    df = _load_f2df(f)
    IDs = df[ID]
    if len(set(IDs))<len(IDs):
        print('Warning, attribute not unique ')
    
    locations = list(zip(df[lon],df[lat]))
    
    return dict(zip(IDs,locations))


def saveLocation_toFile(dict_IDLoc, f, ID='ID', lon='lon', lat='lat',dict_other=None,othername='name'):
    """ 将位置信息保存到文件
        dict_IDLoc: 应包含 id:(lon,lat)
        附加支持 添加一列信息:  dict_other: 可以包含一个 id:其他信息 
                             othername:  指定 其他信息列 的列名
    """
    
    out = [[ID, *dict_IDLoc[ID]] for ID in dict_IDLoc] # id,lon,lat
    df = pd.DataFrame(out, columns=[ID,lon,lat])
    
    if dict_other:
        list_other = []
        for k in dict_IDLoc:
            list_other.append(dict_other[k]) if k in dict_other else list_other.append("")
    
        df[othername] = list_other   
    
    df.to_csv(f)


def generateInterpoints(link):
    # 为一段线段生成插值点
    # link: [(lon1,lat1), (lon2,lat2)]
    startx,starty = link[0][0], link[0][1]
    endx,endy = link[1][0], link[1][1]    
    #dist=math.sqrt((endx-startx)*(endx-startx) + (endy-starty)*(endy-starty)) ## ？？？ 经纬度的平方和开根号
    dist = haversine((starty,startx), (endy,endx))	
    if dist<2:  # 线段长度小于 0.2km,无需插值
        return link
    delta=int(math.ceil(dist/2)) # 间隔0.2km
    points = []
    for step in range(delta): ### 等间隔插值
        curx=float(endx-startx)*step/delta + startx
        cury=float(endy-starty)*step/delta + starty
        points.append([curx,cury])
    points.append([endx,endy])
    return points


def extendLinks(dict_NameLoc, ):
    pass


def get_travelT(G,o,d):
    if not o in G:
        #print(o,'not in graph')
        return -1
    if not d in G:
        #print(d,'not in graph')
        return -1
        
    try:
        t=nx.shortest_path_length(G, o, d, weight='tempdistance_s')
    except nx.NetworkXNoPath:
        t=-1
        print('Node %s not reachable from %s'%(d,o))
    return t

##### plot
def _get_lines(G, dict_IDLoc, attr=None):
    """
    输出：具有位置的列表，对应列表中点顺序的值
    """
    lines = []
    values = []
    for e in G.edges:
        if not (e[0] in dict_IDLoc and e[1] in dict_IDLoc):
            print('Location not found for %s,%s'%(e[0],e[1]))
            continue
        o_loc = dict_IDLoc[e[0]]
        d_loc = dict_IDLoc[e[1]]
        lines.append((o_loc,d_loc))
        if attr:
            values.append(G[e[0]][e[1]][attr])
        
    return lines, values


def cut_G(G, thres, attr='duration_s'):
    """  根据 时间门限 对图进行截取
        thres: 门限， s为单位， 例如 20 mins的门限输入应是 20×60
    """
    #G_copy = copy.deepcopy(G_copy)
    for e in list(G.edges):
        if G[e[0]][e[1]][attr]>thres:
            G.remove_edge(e[0],e[1])
    for n in list(G.nodes):
        if len(list(nx.neighbors(G,n)))==0:
            G.remove_node(n)    
    return G


def plot_G(G, dict_IDLoc,attr=None):
    """
        G 中存的是节点的id
        dict_IDLoc 中存的是节点的位置
    """
    
    lines, values = _get_lines(G, dict_IDLoc, attr=attr)
    if not values:
        colors = ['gray']*len(lines)
    else:
        colors = []
        for spd in values:
    #        if spd >= 300:
    #            colors.append("r")
    #        elif spd >=250:
    #            colors.append('g')
    #        elif spd >= 200:
    #            colors.append("b")
    #        elif spd >= 150:
    #            colors.append('y')
    #        else:
    #            colors.append("lightgray")  
            if abs(spd) >= 100:
                colors.append("r")
            elif abs(spd) >=50:
                colors.append('g')
            elif abs(spd) >= 15:
                colors.append("b")
            elif abs(spd) >= 2:
                colors.append('y')
            else:
                colors.append("lightgray") 
    #        if spd >= 100:
    #            colors.append("r")
    #        elif spd >=20:
    #            colors.append('g')
    #        elif spd == 1:
    #            colors.append("lightgray")
    #            
    #        elif spd >= -20:
    #            colors.append('y')
    #        else:
    #            colors.append("b") 
            
    fig,ax=plt.subplots(1,1,figsize=(12,7.5),dpi=100)
    lc = collections.LineCollection(lines, colors=colors, linewidths=0.5)

    ax.add_collection(lc)
    #for s in hsr_stations:
    #    if s not in dict_NameLoc:
    #        print(s)
    #        continue
    #    ax.scatter(dict_NameLoc[s][0],dict_NameLoc[s][1],c='green',s=3)
    list_locs = [dict_IDLoc[s] for s in G.nodes] 
    lons = [lon for lon,lat in list_locs]
    lats = [lat for lon,lat in list_locs]
    max_lon, min_lon = max(lons)+0.5, min(lons)-0.5 # margin 0.5
    max_lat, min_lat = max(lats)+0.5, min(lats)-0.5   
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)
    #ax.set_xlim(75,135)
    #ax.set_ylim(15,55)