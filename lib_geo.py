# -*- coding: utf-8 -*-
"""
Created on Fri Aug  2 10:46:04 2019
集成一些地理相关的操作函数，
1. 输入，输出文件相关的
   把一些点，线数据输出为shp格式，方便arcgis查看
2. 读取.shp文件，.nt文件
3. 计算经纬度表示的多边形的面积
@author: y1064
"""
import os # 导入必要模块
import pandas as pd
#import numpy as np
import geopandas as gpd
from shapely.geometry import Point, LineString
import shapely
shapely.speedups.enable()

from haversine import haversine
#import scipy.spatial as spatial
from rtree import index
import math
import sys
import pyproj
import networkx as nx

""" Part1, .shp file vs. GeoDataFrame 
	行政区边界框数据是这种格式
"""
def readSHP2gdf(f,encoding='utf-8'):
    """读shp文件到geodataframe  记不住geodataframe的命令
    """
    return gpd.GeoDataFrame.from_file(f,encoding=encoding)


def nodes2shp(dict_nodes,fpath=None):
    """将一系列点写为shp文件
    dict_nodes:  name:(lon,lat)
    """
    out = []
    for name in dict_nodes:
        p = Point(dict_nodes[name])
        out.append([name,p])
    df = gpd.GeoDataFrame(out,columns = ['name','geometry'])
    if fpath:
        #if  not os.path.exists(fpath):#如果路径不存在
        #    os.makedirs(main_path)
        df.to_file(fpath)
    return df

def edges2shp(dict_nodes,list_edges,fpath=None):
    """将一系列的边（线段）写为shp文件
    dict_nodes:  name:(lon,lat)  # 为线段的端点提供位置信息
    list_edges: [(name1,name2),.....]    #可以与graph兼容， list(G_city.edges)
    fpath: 要提供一个文件夹路径，因为写出来会有很多文件
    """
    out = []
    for l in list_edges:
        loc1 = dict_nodes[l[0]]
        loc2 = dict_nodes[l[1]]
        AB = LineString([tuple(loc1), tuple(loc2)])
        out.append([l[0],l[1],AB])
    df = gpd.GeoDataFrame(out,columns = ['from','to','geometry'])
    if fpath:
        df.to_file(fpath)
    return df    

""" Part2 .nt file (netCDF4)
	GDP数据是这种格式
"""
from netCDF4 import Dataset
def readCDF(f):
    data = Dataset(f, "r", format="NETCDF4")
    return data

def readCDF2gdf(f,value='GDP_PPP',time=2015, bound=(-180,180,-90,90)):
    """ 读取.nt文件(netCDF) 为GeoDataFrame 
        bound: 边界框 (left, right, down, up)
    """
    data = readCDF(f)
    ppp = data.variables[value][:]  # 对于GDP数据，ppp 是一个三维的array 
#    ppp_unit = data.variables[value].units
    lats = data.variables['latitude'][:]  
    lons = data.variables['longitude'][:]  
    times = data.variables['time'][:]
    
    gdp = ppp[list(times).index(time)].data  ## 抽出来 2015年
    out = []
    minx,maxx,miny,maxy = bound[0], bound[1], bound[2], bound[3]
    for row in range(len(lats)):
        for col in range(len(lons)):
            if gdp[row][col]>0 and (miny<=lats[row]<=maxy and minx<=lons[col]<maxx):  ## 
                out.append([row, col, lons[col], lats[row], gdp[row][col], Point((lons[col],lats[row]))])

    crs = {'init': 'epsg:4326'}
    return gpd.GeoDataFrame(out, crs=crs, columns=['row', 'col', 'x', 'y', 'value',  'geometry'])


""" Part3 .tiff文件 
    GPWv4 人口数据为这种格式  (https://sedac.ciesin.columbia.edu/data/collection/gpw-v4)
"""
import georasters
def read_tiff(f):
    return georasters.from_file(f)

def read_tiff2df(f, bound=(-180,180,-90,90)):
    """读tiff文件为DataFrame
        bound: 边界框 (left, right, down, up)
    """
    minx,maxx,miny,maxy = bound[0], bound[1], bound[2], bound[3]
    data = georasters.from_file(f)
    df = data.to_pandas()  #  row, col, value, x, y
    df = df[df['value']>0]
    if bound == (-180,180,-90,90):
         return df
    else:
         return df[(df['x']>=minx)&(df['x']<=maxx)&(df['y']>=miny)&(df['y']<=maxy)]
     
def read_tiff2gdf(f, bound=(-180,180,-90,90)):
    """读tiff文件为GeoDataFrame
        bound: 边界框 (left, right, down, up)
    """
    df = read_tiff2df(f, bound)
    geometry = [Point(xy) for xy in zip(df.x, df.y)]
    #df = df.drop(['x', 'y'], axis=1)
    crs = {'init': 'epsg:4326'}
    return gpd.GeoDataFrame(df, crs=crs, geometry=geometry) #  row, col, value, x, y, geometry
    


""" Part4, 对多边形、GeoDataframe的相关操作
"""
import pyproj    
import shapely.ops as ops
from functools import partial

def bounded_gdf(gdf, bound):
    """ 选出边界框内的GeoDataFrame 
    """
    minx,maxx,miny,maxy = bound[0], bound[1], bound[2], bound[3]
    return gdf[(gdf['x']>=minx)&(gdf['x']<=maxx)&(gdf['y']>=miny)&(gdf['y']<=maxy)]


def get_area(geom,unit='m2'):
    """通过转换投影，获取多边形的面积， 单位： 平方米
    geom: 以经纬度longitude, latitude表示的多边形
    """
    geom_area = ops.transform(
        partial(
            pyproj.transform,
            pyproj.Proj(init='EPSG:4326'),
            pyproj.Proj(
                proj='aea',  #  Albers Equal Area Projection
                lat_1=geom.bounds[1],
                lat_2=geom.bounds[3])),
        geom)
    
    if unit=='m2':
        return geom_area.area  # area in m^2
    elif unit=='km2':
        return geom_area.area/10**6  # area in km^2
    

def add_area2gdf(gdf, unit='km2'):
    """ 为GeoDataframe添加一列 面积 列
        unit: 面积的单位, 平方米 或 平方千米
    """
    areas = [get_area(geo,unit) for geo in gdf.geometry]  # 用 map函数更加耗时
    gdf['area'] = areas
    return gdf
#    ### 计算人口密度
#    density = []
#    for row in gdf_out.itertuples():
#        density.append(row.Population/row.area)
#    gdf_out.insert(4,'density',density)
#
#    #### 保存为文件
#    gdf_out.to_file(outPath + region+"populations.shp", encoding='utf-8')
#    
#    endtime = time.time()
#    print('time used:',endtime-starttime)
    

def save_gdf2SHP(gdf, file):
    """ gdf: GeoDataFrame
        file: 输出的文件名，后缀为.shp
    """
    gdf.to_file(file, encoding='utf-8')


def transform_polygon(poly):
    """将多边形从54009 world Mollweide的投影中转换为WGS84投影"""
    x, y = poly.exterior.coords.xy

    transformer = pyproj.Transformer.from_crs('esri:54009','epsg:4326')
    xs,ys=transformer.transform(x, y)
    new_poly = Polygon(list(zip(xs,ys)))
    return new_poly

def get_bound(poly):
    """返回多边形的边界框"""
    x, y = poly.exterior.coords.xy  # (left, bottom, right, top)
    return (min(x),min(y),max(x),max(y))


def rowcol2lonlat(row,col,RESOLUTION=1/120):
    """将读入的ndarray转换成坐标形式的
        RESOLUTION: 1/120 表示30sec
    """
    lat = 90-(0.5+row)*RESOLUTION
    lon = -180+(0.5+col)*RESOLUTION
    return lon,lat