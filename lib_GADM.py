# -*- coding: utf-8 -*-
"""
处理GADM网站上的各国的边界框数据  https://gadm.org/download_world.html
暂时是按国家下载的
因为各国行政单位的粒度不同，所以需要选出粒度合适的行政单位，然后聚合为一个geodataframe以备处理
"""
import os
from collections import defaultdict, Counter
import geopandas as gpd

import matplotlib.pyplot as plt
from descartes import PolygonPatch

from rtree import index


def _determine_level(f):
    """确定应该读入第几级文件
    #string: 该shp文件中最低一级的行政单位的英文类型
    f: 该shp文件的文件名
    """
    df_Boundary = gpd.GeoDataFrame.from_file(f,encoding='utf-8')
    ## 分析文件名，得到第几级的信息
    level = int(f.split('.',-1)[0][-1])  # 整型
    if level == 0:
        return f   ### 只有这一级，就不用判断了
    ## 最低一级的行政单位的英文描述  有的文件没有 'ENGTYPE', 用TYPE代替
    adm_name =  Counter(list(df_Boundary['ENGTYPE_'+str(level)])).most_common(1)[0][0]
    if not adm_name:
        print(f,'no type')
        return None
        #adm_name = Counter(list(df_Boundary['TYPE_'+level])).most_common(1)[0][0]
    if 'District' in adm_name or 'district' in adm_name:
        return f
    elif 'County' in adm_name:
        return f
    elif 'Commune' in adm_name or 'Municipal' in adm_name: # 就加入它的前一级
        return f.split('.',-1)[0][:-1]+str(level-1)+'.shp'
    else:
        return None  # 否则就是 通过这个文件，判断不出哪个符合条件


def select_files(files,exclude = ['RUS', 'IRN']):  # 
    """ 筛选出特定等级的文件
    files: 一个文件夹下列出的所有文件
    exclude: 不包含的国家(俄罗斯，伊朗不要)
    """
    dict_CountryFiles = defaultdict(list)
    for f in files:
        levels = f.split(os.sep)  # 分出来上一级文件夹
        parent_path = levels[0]
        for l in levels[1:-1]:
            parent_path = os.path.join(parent_path,l)
        for ex in exclude:  # 俄罗斯，伊朗不要
            if ex in parent_path:
                continue
        dict_CountryFiles[parent_path].append(f)

    ###### 在一大堆候选文件中选出需要的那个等级
    files_selected = []
    for c in dict_CountryFiles:
        fs = dict_CountryFiles[c]
        for f in sorted(fs,reverse=False)[1:]:
            of = _determine_level(f)
            if of:
                print(of)
                files_selected.append(of)
                break
    return files_selected

def aggregate_files(files):
    """将多个文件中的内容聚合到同一个geodataframe中来
    """
    out = []
    for f in files:
        level = int(f.split('.',-1)[0][-1])  # 整型
        df_Boundary = gpd.GeoDataFrame.from_file(f,encoding='utf-8')
        for index,row in df_Boundary.iterrows():
            country = row['NAME_0']
            GID = row['GID_0']
            if level == 0:  # 只有国家一个粒度
                out.append([GID,country,row['NAME_0'],'Country',row['geometry']])
                break
            full_name = ''
            for l in range(1,level+1):  #
                full_name+=str(row['NAME_'+str(l)])+';'
            tp = row['ENGTYPE_'+str(l)]
            poly = row['geometry']
            
            out.append([GID,country,full_name,tp,poly])  # GID,Country,Name,Type, Geometry
    
    df = gpd.GeoDataFrame(out,columns = ['GID_0','Country','Name','Type','geometry'])
    return df    

def _plot_polygons(list_polygons):
    """绘制多边形边界
    list_polygons: 给定的多边形列表
    ### （绘制5000个多边形的时间合理）
    """
    (fx, fy) = (1200, 900)
    my_dpi = 100
    fig = plt.figure(figsize=(fx / my_dpi, fy / my_dpi), dpi=my_dpi) 
    ax = fig.gca()
    for p in list_polygons:
        ax.add_patch(PolygonPatch(p, fc="white", ec="black", alpha=0.8, zorder=2 ))
    ax.axis('scaled')
    plt.show()    
    

def plot_gdf(gdf, country=None):
    """由geodataframe绘制多边形图
        country: 是否指定某个国家
    """
    if country:
        gdf = gdf[gdf['Country']==country]
    polygons = gdf['geometry']
    
    _plot_polygons(polygons)
   
    
def get_bbox(gdf):
    # return min_x,max_x,min_y,max_y
    minx, maxx = 180, -180
    miny, maxy = 90,-90
    for k in gdf['geometry']:
        bbox = k.bounds
        minx, maxx = min(minx,bbox[0]), max(maxx,bbox[2])
        miny, maxy = min(miny,bbox[1]), max(maxy,bbox[3])

    return (minx,maxx,miny,maxy)

def create_rtree(gdf, file):
    """为边界框数据建立Rtree
    gdf: geodataframe 文件
    file: 注意是我后缀的文件名
    """
    if os.path.exists(file+'.idx'): # 文件已经存在，直接读取
        print('Rtree aready exist, ready for using...')
        return index.Index(file)
    rtree = index.Index(file)
    print('Creating rtree...')
    i=0
    for row in gdf.itertuples():
        rtree.insert(i, row.geometry.bounds, obj=(row.Name,row.geometry,row.GID_0))  # 以字典为对象貌似会出问题
        i+=1
    
    rtree.close()
    rtree = index.Index(file)
    print('Rtree complete...')
    return rtree


## 计算多边形的面积
import pyproj    
import shapely.ops as ops
from functools import partial

def get_area(geom,unit='km2'):
    """通过转换投影，获取多边形的面积， 单位： 平方千米
    geom: 多边形
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



#############################################################################
####  城市边界框多边形的主要用途是将其他网格化的数据聚合到多边形上，获得城市范围内的
####  某个特性，如人口，GDP... 下列程序给出了多线程下将人口数据聚合到城市多边形里的方法
####  应用该程序，未来将很容易进行其他类似的聚合操作
#############################################################################
import sys
sys.path.append(r'E:/pythonlibs')
import lib_GADM
from lib_file import list_all_files
import lib_tiff as ltiff

from multiprocessing import Pool
import time
from shapely.geometry import Point

def execute(func, todolist, rtree, threads):
    """
    func: 将带人口的点聚合进城市多边形的程序
    todolist: 所有的带人口的点(dataframe的每一行)
    todolist, rtree, dict_NamePolyCount  都是func要用到的参数
    
    threads: 线程数
    """
    data=[0,len(todolist),time.time(),threads]
    def update(a):    
        data[0]=data[0]+1
        curt=time.time()
        elapsedt=curt-data[2]
        leftt=elapsedt*(data[1]-data[0])/data[0]
        
        print("Processing %d/%d, time spent: %0.1fs, time left: %0.1fs" % (data[0], data[1], elapsedt, leftt))
        
    pool = Pool(threads)
    mulresAsync = []
    for i in range(len(todolist)):
        mulresAsync.append(pool.apply_async(func, args=(todolist[i], rtree), callback=update))
    pool.close()
    pool.join()
    
    return [x.get() for x in mulresAsync]

def func(item, rtree):  # DataFrame的一条，只能传进来列表
    #### 传进去字典就会出问题？？？？？？
    lon, lat = item[-2], item[-1]
    value = item[-3]
    if value<=0:
        return None
    possible_Cities = [n for n in rtree.intersection((lon,lat,lon,lat),objects=True)]
    # print('Number of possible cities:',len(possible_Cities))
    for item in possible_Cities:
        obj = item.object
        name, poly = obj[0], obj[1]
        if poly.contains(Point(lon, lat)):  #判断城市多边形是否包含这个坐标点
            return [name, value]


#if __name__=='__main__':
#    __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
#    starttime = time.time()
#    region = 'CH' 
#    outPath = 'E:/Code/Data/PopulationOut/'
#    
#    if region == 'EU':
#        ## 挑选粒度适中的boundary数据
#        files = list_all_files('E:/Code/Data/GADM_Boundary','.shp')
#        files = lib_GADM.select_files(files)
#    elif region == 'CH':
#        files = ['E:/Code/Data/gadm36_CHN_shp/gadm36_CHN_2.shp']
#        
#    gdf = lib_GADM.aggregate_files(files)
#    ####  城市多边形    名字：[多边形，人口计数]
#    dict_NamePolyCount = {} # {(NAME):[Poly,count]}
#    for row in gdf.itertuples():
#        dict_NamePolyCount[row.Name] = [row.geometry,0]    
#    ## 城市边界多边形创建rtree
#    file = outPath + 'rtree_'+region
#    rtree = lib_GADM.create_rtree(gdf, file)  # object 是边界的name
#    rtree_bounds = rtree.get_bounds() # 左下右上
#    
#    ## 网格数据，转化成Dataframe
#    f_pop = 'E:/Code/Data/GPWv4_Population/gpw_v4_population_count_rev11_2015_2pt5_min.tif'
#    if region == 'EU':
#        min_x = max(-12, rtree_bounds[0])  #  再往左是葡萄牙的那些岛，意义不大
#    elif region == 'CH':    
#        min_x = rtree_bounds[0]
#        
#    bound = (min_x, rtree_bounds[2], rtree_bounds[1], rtree_bounds[3])
#    df_pop = ltiff.read_tiff2df(f_pop,bound = bound)  # 左右下上
#    df_pop = df_pop[df_pop['value']>0]  
#
#    todos = [item for item in df_pop.itertuples(name=None)]
#    L = execute(func, todos, rtree, 10)
#    # 组装结果
#    for l in L:
#        if not l:
#            continue
#        name, value = l[0], l[1]
#        if name not in dict_NamePolyCount:
#            print('no name')
#        else:
#            dict_NamePolyCount[name][1] += value
#    
#    endtime = time.time()
#    print('time used:',endtime-starttime)
#    
#    rtree.close()
#    
#    ## 制作GeoDataframe
#    out = []
#    for row in gdf.itertuples():
#        name = row.Name
#        population = dict_NamePolyCount[name][1]
#        if region=='EU' and row.geometry.bounds[2]<-12:  #### 经度小于-12的是葡萄牙的小岛，忽略 
#            continue
#        out.append([row.GID_0, row.Country, name, row.Type, population, row.geometry])
#    
#    gdf_out = gpd.GeoDataFrame(out, columns=['GID_0', 'Country', 'Name', 'Type', 'Population', 'geometry'])
#    gdf_out.crs = {'init' :'epsg:4326'} # WGS-84  设置投影
#
#    ### 等面积投影，计算多边形面积  (这步比较花时间)
#    area = gdf_out['geometry'].map(lambda p: get_area(p))
#    gdf_out.insert(4,'area',area)
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