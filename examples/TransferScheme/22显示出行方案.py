# -*- coding: utf-8 -*-
"""
Created on Sat Sep 28 14:58:37 2019

@author: y1064
"""

import sys
sys.path.append(r'E:/Gitlab/pythonsharedfunctions.git')
import pandas as pd
from collections import defaultdict, Counter
import lib_file
from lib_timetable import Timetable

import lib_time

import matplotlib.pyplot as plt
from prettytable import PrettyTable
import prettytable
import lib_time  ### 关于时间的相应操作在这个包里
from lib_time import get_deltaT, strT_to_floatT, floatT_to_strT


def construct_scheme(list_layerAccess, dest):
    """ 根据零散的 list_layerAccess，及目的地，生成出行方案
        倒着找，是最少旅行时间，最多换乘的
    """
     
    if dest in list_layerAccess[0]:
        scheme = list_layerAccess[0][dest]
        #dict_distScheme[dest] = scheme
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
        print('Unaccessible station!')
        return None
    
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
        out.append([train_code,source,destination,dt,at])
        
    table = PrettyTable(["train_code", "source", "target", "departure time","arrival time"])
    #table.set_style(prettytable.MSWORD_FRIENDLY)
    for row in out:
        table.add_row(row)
    totalT = str(scheme[-1]['total_travelT']//60).zfill(2)+':'+str(scheme[-1]['total_travelT']%60).zfill(2)
    print('Transfer scheme is as follow, travel time:',totalT)
    print(table)
        
    return out

s=construct_scheme(list_layerAccess, '西安')