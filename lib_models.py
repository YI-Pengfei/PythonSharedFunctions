# -*- coding: utf-8 -*-
"""
Created on Sun Jun 30 15:53:50 2019

@author: y1064
"""

import numpy as np
import rasterio
import rasterio.features
import rasterio.warp
import matplotlib.pyplot as plt
from haversine import haversine
import math
from collections import defaultdict

def gravity(loc1,loc2,value1,value2,latlon=False):
    """
    给定两地位置(lon,lat)，及人口数 value，
    使用重力模型计算travel demond
    默认输入的是lon,lat,haversine接收的是latlon
    """
    loc1,loc2 = (loc1[1],loc1[0]), (loc2[1],loc2[0])
    dis = haversine(loc1, loc2)
    ln_res = math.log(value1)+math.log(value2)-2*math.log(dis) # -20 充当一个系数
    return math.exp(ln_res) * pow(10,-4)


class Models:
    """一个应用辐射模型计算流矩阵的类"""
    def __init__(self):
        self.names = []
        self.dict_NameLocation = {}
        self.dict_NameValue = {}
        self.dict_NamepairDistance = defaultdict(dict)

    def load_data(self, dict_NameLocation, dict_NameValue):
        """
        加载数据
        :param dict_NameLocation: 节点名：位置坐标
        :param dict_NameValue:    节点名：值 (可以是人口数，人口密度，GDP等)
        :return:
        """
        self.dict_NameValue = dict_NameValue
        self.dict_NameLocation = dict_NameLocation
        # 计算距离
        self.names = list(self.dict_NameValue.keys())
        for i in range(len(self.names)):
            for j in range(i+1,len(self.names)):
                i_loc = self.dict_NameLocation[self.names[i]]
                j_loc = self.dict_NameLocation[self.names[j]]
                d = haversine((i_loc[1],i_loc[0]), (j_loc[1],j_loc[0]))
                self.dict_NamepairDistance[self.names[i]][self.names[j]] = d
                self.dict_NamepairDistance[self.names[j]][self.names[i]] = d
        # 对每一个name_i，排序它与其他节点的距离，由小到大
        for name_i in self.dict_NamepairDistance:
            sorted_Distance_j = sorted(self.dict_NamepairDistance[name_i].items(),key=lambda x:x[1])
            self.dict_NamepairDistance[name_i] = {k:v for k,v in sorted_Distance_j}

    def calculate_gravity(self, Threshold=None):
        """由引力模型计算流
        :param Threshold:  距离门限，超过该门限的节点对不计算相关性
        :return: out_T 嵌套字典，
        """
        out_T = defaultdict(dict)
        for i in range(len(self.names)):
            for j in range(i):
                name_i, name_j = self.names[i], self.names[j]
                value_i, value_j = self.dict_NameValue[name_i], self.dict_NameValue[name_j]
                dis_ij = self.dict_NamepairDistance[name_i][name_j]
                if Threshold and dis_ij>Threshold:
                    continue

                T = value_i*value_j/(dis_ij**2)   # 引力模型公式
                out_T[name_i][name_j] = T#math.log(T,10)

        return out_T


    def calculate_radiation(self,Ratio_Tij_Ti=0.1):
        """ 由辐射模型计算流
        对每个源，到所有目的地的radiation只需要一次遍历即可完成，详见20191123的daily report 
        :param Ratio_Tij_Ti: # 通勤人数与源点的人口数的比值(一般认为二者成正比)
        :return: dict_IDIDRadiation 嵌套字典
        """
        dict_distance = self.dict_NamepairDistance
        dict_IDPop = self.dict_NameValue
        totalPop = sum(dict_IDPop.values())
        dict_IDIDRadiation = {}
        for orgID in dict_IDPop:
            orgPop = dict_IDPop[orgID]
            dict_orgID_distance = dict_distance[orgID]  ## 挑出这个点与其他各个点的距离的字典 (是不包含与自身的)
            list_distance_id = sorted(list(zip(dict_orgID_distance.values(), dict_orgID_distance.keys())))
            sum_pop = 0
            dict_destID_radiation = {}
            for i in range(len(list_distance_id)):
                distance, destID = list_distance_id[i]  ## 由近及远取点
                destPop = dict_IDPop[destID]
                sum_pop +=destPop
                Sij = sum_pop - destPop  ### 辐射模型中的Sij (去掉源和目的地的人口)
                Ti = Ratio_Tij_Ti*orgPop  ### 辐射模型中的Ti， 跟源点的人口数成比例，设为0.1
                correction_factor =1/(1-orgPop/totalPop)  ## 对 finite system 的修正参数
#                radiation = Ti*orgPop*destPop/((orgPop+Sij)*(orgPop+destPop+Sij))
                radiation = correction_factor*Ti*orgPop*destPop/((orgPop+Sij)*(orgPop+destPop+Sij))
                dict_destID_radiation[destID] = radiation
            dict_IDIDRadiation[orgID] = dict_destID_radiation

        return dict_IDIDRadiation