# -*- coding: utf-8 -*-
"""
Functions to process gridded GPWv4 data (https://sedac.ciesin.columbia.edu/data/collection/gpw-v4)
rely on georasters (https://github.com/ozak/georasters)
"""
import georasters as gr
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def read_tiff(f):
    return gr.from_file(f)

def read_tiff2df(f,bound = (-180,180,-90,90)):
    """
    读tiff文件为dataframe, 
    bound:  边界框
    """
    minx,maxx,miny,maxy = bound[0], bound[1], bound[2], bound[3]
    data = gr.from_file(f)
    df = data.to_pandas()    
    if bound == (-180,180,-90,90):
         return df
    else:
         return df[(df['x']>=minx)&(df['x']<=maxx)&(df['y']>=miny)&(df['y']<=maxy)]
     
def df2array(df):
    """
    read dataframe as array  这只对分辨率为1degree的有效
    """
    min_r,max_r = min(df.row), max(df.row)
    min_c,max_c = min(df.col), max(df.col)
    arr = np.empty([max_r-min_r+1,max_c-min_c+1])
    for row in df.itertuples():
        if row.value>0:
            arr[row.row-min_r][row.col-min_c] = row.value    
    return arr
    

def plot(df, my_dpi=100,fx=600,fy=400):
    """use imshow to plot dadaframe
    logarithm transformation was done in order to show population density.
    """
    arr = df2array(df)
    arr[arr <=0] = np.nan  # 小于0的全替换为0 
    my_dpi = my_dpi
    (fx, fy) = (fx, fy)
    fig = plt.figure(figsize=(fx / my_dpi, fy / my_dpi), dpi=my_dpi) 
    #plt.tight_layout()  #自动调整subplot间的参数
    minx,maxx,miny,maxy = min(df.x), max(df.x), min(df.y), max(df.y)
    plt.imshow(np.log(arr+1),cmap=plt.cm.jet,extent=(minx,maxx,miny,maxy))  # logarithm transformation
    plt.axis('off') # 关闭坐标轴

#def plot_from_arr(arr, my_dpi=100,fx=600,fy=400):
#    arr[arr <=0] = np.nan  # 小于0的全替换为0 
#    my_dpi = my_dpi
#    (fx, fy) = (fx, fy)
#    fig = plt.figure(figsize=(fx / my_dpi, fy / my_dpi), dpi=my_dpi) 
#    plt.imshow(np.log(arr+1),cmap=plt.cm.jet)  # logarithm transformation
#    plt.axis('off')