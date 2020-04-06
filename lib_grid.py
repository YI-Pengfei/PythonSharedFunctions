# -*- coding: utf-8 -*-
"""
网格化的相关操作
"""
from haversine import haversine
import math

def get_nearestGrid(center,r,roundn=4):
    """ 给定一个位置，求最近的网格点
        center: 中心点的经纬度
        r: 网格点的分辨率,如:r=1/32，表示分辨率为1/32度
        roundn: 小数点后的位数
    """
    x,y = round(center[0]/r+0.5*r)*r, round(center[1]/r+0.5*r)*r  ## -17×0.05=-3.5500000000000003？？？
    return round(x,roundn),round(y,roundn)

def _grid_neighbor(grid, r,roundn=4):
    """ 由中心点，获得 上下左右，左上，左下，右上，右下 八个邻居节点的坐标
    
    """
    x,y = grid[0],grid[1]
    out = []
    for i in range(-1,2):
        for j in range(-1,2):
            if i==0 and j==0:
                continue
            ### 这还有一点儿问题， round的时候应该取比需要的位数更多的位数，
            ## 2019.10.07改
            out.append(get_nearestGrid((x+i*r,y+j*r),r)) ## 近似的时候总是出问题，还得运行一次找的程序
            #out.append( (round(x+i*r,roundn),round(y+j*r,roundn)) )    ## -3.55-0.05 = -3.5999999999999996
    return out
    
    

def get_gridArea_OSRM(center, r, thres_t, osrm):
    """ 获取指定 时间门限 内的所有可达 网格点      （由内而外的扫描，调用OSRM计算旅行时间）
        center: 中心点的经纬度
        r: 网格点的分辨率,如:r=1/32，表示分辨率为1/32度
        thres_t: 旅行时间门限，如 60 mins   
        osrm: lib_osm库中的OSRM类的对象
    """
    def _if_valid(p1,p2,steps):
        """  2019.09.27  好像是到了海边就不好使了,就只导航到海边
            所以添加一个起终点与路径规划的起终点的距离的判断
        """
        if not steps:
            return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 <= r**2)
        return ((steps[0][0]-p1[0])**2 + (steps[0][1]-p1[1])**2 <= r**2) and ((steps[-1][0]-p2[0])**2 + (steps[-1][1]-p2[1])**2 <= r**2)

    def calculate_t(p1,p2):
        ### 返回的开车时间duration是以s为单位的
        dis = round(haversine((p1[1],p1[0]), (p2[1],p2[0])),3)  ## 千米,精确到米

        steps1, duration1 = osrm.queryRoute(p1, p2)  ##duration是s为单位   ### 根据steps可以组装出实际路线和距离，暂时不需要
        if_valid1 = _if_valid(p1,p2,steps1)

        if duration1 != 0:  ## 结果不为0
            if dis/(duration1 / 3600) > 40 and if_valid1:  ## 速度基本合理，就不用反着算了，节省时间,,距离(km)/时间(min/60) = 速度(千米/h)
                return duration1, dis
        elif if_valid1:  # 虽然是0,但是起终点距离很近，也可以接受
            return duration1, dis

        steps2, duration2 = osrm.queryRoute(p2, p1)
        if_valid2 = _if_valid(p2, p1, steps2)
        if if_valid2:  ## 反着算起终点
            duration = min([duration1, duration2, dis / 5 * 3600])  ## 5km/h的步速， 正， 反， 取一个最小的，正常情况下有路径就不是-1,所以是安全的
            return duration, dis

        return -1, dis


            
    
    ## 简单地，先将 center近似到一个网格点
    gridLoc = get_nearestGrid(center,r)
    duration,dis = calculate_t(center,gridLoc)

    dict_accessed = {}  ## 存储访问过的节点
    
    dict_childrenInfo = {gridLoc:{'distanceLBS_m':dis,'duration_s':duration }}
    while dict_childrenInfo:
        set_children = []
        for g in dict_childrenInfo: ## 求下一层
            set_children += _grid_neighbor(g, r)

        dict_accessed.update(dict_childrenInfo) ## 合并到其中
        dict_childrenInfo={} ## 清空，准备下次使用
        
        set_children = set(set_children) - set(dict_accessed.keys()) ## 把内层去掉        
        #print(set_children)

        for g in set_children:
            ####  中国边界框限制，正常情况下应该不需要
            #if not (73.4997347<=g[0]<=134.7754563 and 17.7<=g[1]<= 53.560815399999996):
            #    continue
            ####
            duration,dis = calculate_t(center,g)
            if duration!=-1 and duration<=thres_t: # 只有旅行时间有效，且小于 时间门限的格点，才会被加入其中
                dict_childrenInfo[g] = {'distanceLBS_m': round(dis*1000), 'duration_s':round(duration) }
    
    return dict_accessed
    
    


def get_gridArea(center, r, distance):
    """ 给定一个距离门限distance (km)，确定在该半径内的网格点    (由外而内：先确定了边界框，在确定的格点)
        center: 中心点的经纬度
        r: 网格点的分辨率,如:r=1/32，表示分辨率为1/32度
        distance: 距离门限，如200km
    """
    ## 简单地，先将 center近似到一个网格点
    gridLoc = get_nearestGrid(center,r)
    ## 确定上界，计算垂直方向， 1/r 度对应的距离
    delta_y =haversine((gridLoc[1],gridLoc[0]),(gridLoc[1]+r , gridLoc[0]))
    delta_x =haversine((gridLoc[1],gridLoc[0]),(gridLoc[1], gridLoc[0]+r)) 
    n_y = math.ceil(distance/delta_y)+1 ## 需要向上、向下多少个网格
    n_x = math.ceil(distance/delta_x)+1 ## 需要向左、向右多少个网格
    
    out_grids = []
    for dx in range(-n_x,n_x+1):
        for dy in range(-n_y,n_y+1):
            x = gridLoc[0] + dx*r
            y = gridLoc[1] + dy*r
            if haversine((y,x),(center[1],center[0]))<=distance:
                out_grids.append((x,y))
    return out_grids


### 加对GWPv4数据的相关操作
## 网格数据，转化成Dataframe
""" 例子：一种必要的操作是从高分辨率的数据中降为低分辨率的数据，聚合/降采样
    如 将2.5min的数据聚合成5min的数据，就是4个网格合成一个
"""
#f_pop = OS+'/Code/Data/GPWv4_Population/gpw_v4_population_count_adjusted_to_2015_unwpp_country_totals_rev11_2020_2pt5_min.tif'#OS+'Data/GPWv4_Population/gpw_v4_population_count_rev11_2000_2pt5_min.tif'
    
#bound = (rtree_bounds[0], rtree_bounds[2], rtree_bounds[1], rtree_bounds[3])
#df_pop = lib_tiff.read_tiff2df(f_pop,bound = bound)  # 左右下上
#df_pop = df_pop[df_pop['value']>0]  

#### 20191118 添加 降采样  从2.5min分辨率的网格点降为5min #####################
#dict_lowgrid_info = {}
#for row in df_pop.itertuples():
#    center = (row.x, row.y)
#    value = row.value
#
#    lowgrid = lib_grid.get_nearestGrid(center,r=1/12,roundn=4)   ##### 1/12降为 5min的分辨率
#    
#    if lowgrid in dict_lowgrid_info:
#        dict_lowgrid_info[lowgrid]['value']+=value
#    else:
#        info = {'value':value, 'x':lowgrid[0], 'y':lowgrid[1]}   # 顺序要保持 value,x,y
#        dict_lowgrid_info[lowgrid] = info

#df_pop_new = pd.DataFrame(list(dict_lowgrid_info.values()))
#########################################################################