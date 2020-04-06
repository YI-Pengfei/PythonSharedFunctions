"""

    matplotlib.colors: https://matplotlib.org/tutorials/colors/colormapnorms.html
"""

import matplotlib.pyplot as plt
import matplotlib
from matplotlib import collections
import matplotlib.image as mpimg
import numpy as np
import pandas as pd
from mpl_toolkits.basemap import Basemap
from matplotlib.patches import Polygon
import seaborn as sns
#from colour import Color
from collections import namedtuple  

from shapely.geometry import Point, LineString
from descartes import PolygonPatch
import geoplot as gplt

from matplotlib import colors as mcolors


from pylab import mpl  
mpl.rcParams['font.sans-serif'] = ['SimHei'] 

plt.rcParams['axes.unicode_minus']=False #用来正常显示负号

class Colorbar:
    def __init__(self,list_values,fromColor="white",toColor="red",n=5):
        """
            list_values: a list of values
            n: the number of colors/ value intervals.
        """
        f, t = Color(fromColor), Color(toColor)
        self.colorbar = list(f.range_to(t,n+1))
        sorted_values = sorted(list_values)    # 升序，小到大
        self.split_values = [sorted_values[round(len(sorted_values)/n*i)] for i in range(1,n)] + [max(list_values)] ## 排序等分 一个列表切了几刀

    def get_color(self, value):
        for i, v in enumerate(self.split_values):
            if value<=v:
                return str(self.colorbar[i+1])

###############################################################################
## 1. basemap画图相关     https://matplotlib.org/basemap/
def plot_map(lons, lats, text=None, shp_file=None):
    (fx, fy) = (900, 600)
    my_dpi = 150
    fig = plt.figure(figsize=(fx / my_dpi, fy / my_dpi), dpi=my_dpi)
    # 中国大部
    m = Basemap(llcrnrlon=80.33,
                  llcrnrlat=13.01,
                  urcrnrlon=138.16,
                  urcrnrlat=56.123,
                 resolution='l', projection='tmerc',
                lat_0 = 42.5,lon_0=120,)
    if shp_file:			
        shp_info = m.readshapefile(shp_file,'states',drawbounds=True) # CHN_adm1的数据是中国各省区域
				
    m.drawcoastlines(linewidth=0.5)
    m.drawcountries(linewidth=0.5)
    # 画出国境线（描边）
    #m.fillcontinents(color='y',lake_color='aqua') #
    # 填充大陆, 大陆颜色为珊瑚色， 湖泊颜色为水色
    #m.drawmapboundary(fill_color="#bee6fa")
    m.drawcounties()
    m.shadedrelief() #etopo绘制地形图，shadedrelief是浮雕图，默认是空白轮廓图
    # 画点
    xpt, ypt = m(lons, lats)  # 投影方式决定的，需要转换
    # m.scatter(xpt,ypt)#,'bo',s=3)
    m.scatter(xpt, ypt, c='black', s=5,zorder=4)
    plt.subplots_adjust(left=0, bottom=0, right=1, top=1,hspace=0.1,wspace=0.1)#左下为0右上为1时绘图区全屏
    if text:
        for i in range(len(text)):
            plt.text(xpt[i], ypt[i], text[i], fontsize=6, color='black', horizontalalignment="center",
                     verticalalignment="center", weight="normal", stretch="normal",
                     bbox=dict(facecolor="yellow", edgecolor='k', boxstyle='round', alpha=0.6, linewidth=0.1),
                     clip_on=True)
            #plt.text(xpt[i], ypt[i], text[i], fontsize='small') # xx-small
    return m
    """
    # nylat, nylon are lat/lon of New York
    nylat = 40.78; nylon = -73.98
    # lonlat, lonlon are lat/lon of London.
    lonlat = 51.53; lonlon = 0.08
    # draw great circle route between NY and London
    m.drawgreatcircle(nylon,nylat,lonlon,lonlat,linewidth=2,color='b')
    """

def plotLine(m,lon1,lat1,lon2,lat2,color="blue",lwd=0.5,lty="-",alpha=0.5,linewidth=0.15):
    # 两地之间画线
	lats=[lat1,lat2]
	lons=[lon1,lon2]
	x, y = m(lons,lats)
    #x, y = lons,lats
	mtext=plt.Line2D(x,y, linewidth=linewidth,zorder=1, linestyle=lty,color=color,alpha=alpha)
	plt.gcf().gca().add_artist(mtext)

def plot_plot(m, list_x, list_y,color='blue',alpha=1,linewidth=0.2):
    """ basemap上画线
    """
    list_x, list_y = m(list_x,list_y)
    l1 = plt.plot(list_x,list_y,c=color,zorder=4, alpha=alpha,linewidth=linewidth)
    #plt.legend(handles=[l1],labels=['up'],loc='best')

def plot_From_Locations(list_locs,s=1,fpath=None,x=1200,y=900,dpi=150,shp_file=None,m=None,color='r',marker='.',bbox=None):
    """输入：一系列坐标点的列表
    给定fpath则保存图片到文件, s为散点的大小
    bbox: 显示范围: min_lon, max_lon, min_lat, max_lat
    """
    lons = [lon for lon,lat in list_locs]
    lats = [lat for lon,lat in list_locs]
    max_lon, min_lon = max(lons)+0.5, min(lons)-0.5 # margin 0.5
    max_lat, min_lat = max(lats)+0.5, min(lats)-0.5
    print(max_lon, min_lon, max_lat, min_lat)
    if bbox:
        min_lon, max_lon = bbox[0],bbox[1]
        min_lat, max_lat = bbox[2],bbox[3]        
    
    #min_lon, max_lon = -7,2#-10,28
    #min_lat, max_lat = 50,58#35,65
    centlon,centlat=min_lon+(max_lon-min_lon)/2,min_lat+(max_lat-min_lat)/2 
    if not m:  ### 给定m的情况下可以沿着之前画过的图继续画
        (fx, fy) = (x, y)
        my_dpi = dpi
        fig = plt.figure(figsize=(fx / my_dpi, fy / my_dpi), dpi=my_dpi)
        m = Basemap(
            lon_0=centlon,lat_0=centlat,lat_ts=centlat,
            llcrnrlon = min_lon,
            llcrnrlat = min_lat,
            urcrnrlon = max_lon,
            urcrnrlat = max_lat, projection='tmerc',
            rsphere=6371200., resolution='l',epsg=4326)
#    m = Basemap(
#            lat_0 = 42.5,lon_0=120,
#            llcrnrlon=80.33,
#            llcrnrlat=13.01,
#            urcrnrlon=138.16,
#            urcrnrlat=56.123,
#            rsphere=6371200., resolution='l',epsg=4326
#            )
#    m.fillcontinents(color='#D3D3D3',lake_color='#AFEEEE') #  'lightblue':            '#ADD8E6',
    # 填充大陆, 大陆颜色为珊瑚色， 湖泊颜色为水色
#    m.drawmapboundary(fill_color="#bee6fa")
    if shp_file:			
        shp_info = m.readshapefile(shp_file,'states',drawbounds=True) # CHN_adm1的数据是中国各省区域

    m.drawcoastlines(linewidth=0.25)
    m.drawcountries(linewidth=0.25)
    #m.shadedrelief() #etopo绘制地形图，shadedrelief是浮雕图，默认是空白轮廓图
#    plt.scatter(lons,lats, color=color,zorder=3,s=s,marker=marker) #
    # 下边还可以扩展画连边

    # 还可以选择是保存还是显示
    if fpath:
        plt.savefig(fpath+'.png',dpi=300) # 指定分辨率
        plt.close()
        return 0
    else:
        #plt.show()
        #pass  # 不显示的话之后还可以继续画线什么的
        return m

def wordmap(lons, lats, text=None):
    (fx, fy) = (900, 600)
    my_dpi = 150
    fig = plt.figure(figsize=(fx / my_dpi, fy / my_dpi), dpi=my_dpi)
    ax = fig.add_subplot(1, 1, 1)
    # setup mercator map projection.
    m = Basemap(#llcrnrlon=-180.,
                #llcrnrlat=-60.,
                #urcrnrlon=180.,
                #urcrnrlat=90.,
                #rsphere=(6378137.00, 6356752.3142),
                resolution='l',
                lat_0=0., lon_0=0., lat_ts=0.,
                projection='robin',
                )
    m.drawcoastlines(linewidth=0.5)
    m.fillcontinents()
    #m.drawmapboundary(fill_color="#bee6fa")
    # draw parallels
    m.drawparallels(np.arange(-90, 90, 30), labels=[1, 1, 0, 1])
    # draw meridians
    m.drawmeridians(np.arange(-180, 180, 60), labels=[1, 1, 0, 1])
    m.shadedrelief() #etopo绘制地形图，shadedrelief是浮雕图，默认是空白轮廓图
    
    lons,lats = m(lons,lats)
    
    m.scatter(lons, lats, s=1, zorder=3,c='red')
    if text:
        for i in range(len(text)):
            plt.text(lons[i], lats[i], text[i], fontsize='small') # xx-small

def plot_Linestrings(list_linestring, list_values=None):
    """ 由 Linestring(shapely对象)列表 画图
    """
    def plot_line(ax, linestring,c='black'):
        x, y = linestring.xy
        ax.plot(x, y, color=c, linewidth=0.5, solid_capstyle='round', zorder=1)

    (fx, fy) = (900, 600)
    my_dpi = 150
    if list_values!=None: 
        colors = Colorbar(list_values=list_values)

    fig = plt.figure(figsize=(fx / my_dpi, fy / my_dpi), dpi=my_dpi)    
    ax = fig.add_subplot(111)
    for i,line in enumerate(list_linestring):
        c=colors.get_color(list_values[i]) if list_values!=None else 'black'
        plot_line(ax,line,c=c)
        #dilated = line.buffer(0.0001)
        #patch1 = PolygonPatch(dilated, fc='blue', ec='blue', alpha=0.5, zorder=2)
        #ax.add_patch(patch1)


def plot_lines(list_lines, ax=None, list_values=None,colors=None):
    """ 使用LineCollection高效地画线
        list_lines: a list of ((lon1,lat1), (lon2,lat2))
        list_values: 根据值分配线段的颜色
    """
    if not colors:
        if list_values:
            colobar = Colorbar(list_values=list_values)  #生成色棒 
        colors = [colobar.get_color(v) for v in list_values] if list_values!=None else ['grey']*len(list_lines)
    
    if not ax:
        (fx, fy) = (12,7.5)
        my_dpi=100
        fig,ax=plt.subplots(1,1,figsize=(fx,fy),dpi=my_dpi)  
    lc = collections.LineCollection(list_lines, colors=colors, linewidths=0.8, alpha=0.5)
    ax.add_collection(lc)
    #ax.set_xlim(75,135)
    #ax.set_ylim(15,55)
    #plt.show()
    return ax
   
###############################################################################
## seaborn画图相关
def sns_setting(style="darkgrid",xlabel=None,ylabel=None,fx=900,fy=600,my_dpi=150):
    sns.set(style=style)
    (fx, fy) = (900, 600)
    my_dpi = 150
    fig = plt.figure(figsize=(fx / my_dpi, fy / my_dpi), dpi=my_dpi)
    ax = fig.add_subplot(1, 1, 1)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel,fontsize=15)
    #return ax


def barplotFromDict(dictData,n=None,x=1200,y=600,dpi=150,xlabel=None,ylabel=None,label=None,reverse=True,color='r',alpha=1,sort=True,fpath=None):	
    # 画条形图；dictData是一个字典，键是条的名称，值是条的值
    # n:如果数据较多，可以选择只画前n项
    (fx,fy)=(x,y)
    my_dpi=dpi
    fig=plt.figure(figsize=(fx/my_dpi, fy/my_dpi), dpi=my_dpi)
    #ax = fig.add_subplot(1,1,1)
    if sort:
        sorted_dictData = sorted(dictData.items(),key=lambda item:item[1],reverse=reverse)
    else:
        sorted_dictData = dictData.items()
    if n:
        sorted_dictData = sorted_dictData[:n+1]
    keys = [k for k,v in sorted_dictData] # keys 是横轴显示的文本
    values = [v for name,v in sorted_dictData] # values是数据
    rects=plt.bar(range(len(values)), values, color=color,alpha=alpha,label=label)
    index=list(range(len(values)))
    index=[float(c) for c in index]
    plt.xticks(index,keys, rotation=90)
    if xlabel:
        plt.xlabel(xlabel)# X轴标题
    if ylabel:
        plt.ylabel(ylabel)

    # 还可以选择是保存还是显示
    if fpath:
        plt.savefig(fpath+'.png',dpi=my_dpi,bbox_inches = 'tight') # 指定分辨率
        plt.close()
        return 0




def distplot(list_data,label=None,axlabel=None,bins=None):
    sns.distplot(list_data,bins=bins, hist = True, kde = True, 
                rug = False, vertical = False,
                color = 'b', label = label, axlabel = axlabel)
    #plt.legend()        


def jointplotFromLists(list1,list2,list1Name,list2Name,kind='reg',x=900,y=600,dpi=150):
    (fx,fy)=(x,y)
    my_dpi=dpi
    fig=plt.figure(figsize=(fx/my_dpi, fy/my_dpi), dpi=my_dpi)
    df = pd.DataFrame(list(zip(list1,list2)),columns=[list1Name,list2Name])
    sns.jointplot(x=df[list1Name], y=df[list2Name], #设置xy轴，显示columns名称
                  data = df,  #设置数据
                  #color = 'b', #设置颜色
                  #s = 50, edgecolor = 'w', linewidth = 1,#设置散点大小、边缘颜色及宽度(只针对scatter)
                  #stat_func=sci.pearsonr,
                  kind = kind,#设置类型：'scatter','reg','resid','kde','hex'
                  #stat_func=<function pearsonr>,
                  space = 0.1, #设置散点图和布局图的间距
                  size = 6, #图表大小(自动调整为正方形))
                  ratio = 5, #散点图与布局图高度比，整型
                  marginal_kws = dict(bins=15, rug =False), #设置柱状图箱数，是否设置rug
                  )



###############################################################################
## geoplot画图相关
##### 画城市人口数 可用
#import geoplot as gplt
#import geoplot.crs as gcrs
#gplt.choropleth(
#    gdf_population, hue='Population', projection=gcrs.AlbersEqualArea(),
#    edgecolor='white', linewidth=1,
#    cmap='Greens', legend=True,
##    scheme='fisherjenks',
##    legend_labels=[
##        '<3 million', '3-6.7 million', '6.7-12.8 million',
##        '12.8-25 million', '25-37 million'
##    ]
#)


######   画凸包的
Point = namedtuple('Point', 'x y')
class ConvexHull(object):
    def __init__(self):
        self._points = []
        self._hull_points = []

    def _add(self, point):
        self._points.append(point)

    def add_list(self, list_x, list_y):
        """ 以列表形式一次性添加数据
            list_x: x坐标的列表
            list_y: y坐标的列表
        """
        for i in range(len(list_x)):
            self._add(Point(list_x[i], list_y[i]))

    def _get_orientation(self, origin, p1, p2):
        '''
        Returns the orientation of the Point p1 with regards to Point p2 using origin.
        Negative if p1 is clockwise of p2.
        :param p1:
        :param p2:
        :return: integer
        '''
        difference = (
            ((p2.x - origin.x) * (p1.y - origin.y))
            - ((p1.x - origin.x) * (p2.y - origin.y))
        )

        return difference

    def compute_hull(self):
        '''
        Computes the points that make up the convex hull.
        :return:
        '''
        points = self._points

        # get leftmost point
        start = points[0]
        min_x = start.x
        for p in points[1:]:
            if p.x < min_x:
                min_x = p.x
                start = p

        point = start
        self._hull_points.append(start)

        far_point = None
        while far_point is not start:
            # get the first point (initial max) to use to compare with others
            p1 = None
            for p in points:
                if p is point:
                    continue
                else:
                    p1 = p
                    break

            far_point = p1

            for p2 in points:
                # ensure we aren't comparing to self or pivot point
                #if p2 is point or p2 is p1:
                if any([p2 is point, p2 is p1]):
                    continue
                else:
                    direction = self._get_orientation(point, far_point, p2)
                    if direction > 0:
                        far_point = p2

            self._hull_points.append(far_point)
            point = far_point

    def get_hull_points(self):
        if self._points and not self._hull_points:
            self.compute_hull()

        return self._hull_points

    def display(self, s=0.2, texts=None,xlabel="",ylabel="",fpath=None):
        """ 显示所有的散点，突出显示凸包
            texts: 可选地给定散点的文本信息
        """
        # all points
        (fx, fy) = (900, 600)
        my_dpi = 100
        fig = plt.figure(figsize=(fx / my_dpi, fy / my_dpi), dpi=my_dpi)

        x,y = zip(*self._points)
        plt.scatter(x, y, marker='D', linestyle='None', s=s)  # 画所有的点
        # hull points
        hx,hy = zip(*self._hull_points)  # 画凸包点
        plt.plot(hx, hy,c='red')
        #plt.title('Convex Hull')
        #plt.show()
        ### 上述是基本的散点和凸包线的绘制，为了更加生动，下面提供的是凸包点及其文本信息
        hull_ps  = self._hull_points[:-1]
        for i in range(len(hull_ps)):
            plt.scatter(hull_ps[i].x,hull_ps[i].y, marker='D', linestyle='None', c='red') # 凸包散点
        if texts: # 如果有文本信息
            for p in hull_ps:
                idx = self._points.index(p)  # 找该点在列表中的索引号
                plt.text(p.x,p.y,texts[idx],fontsize=14)

        #plt.plot([min(x),max(x)],[min(x),max(x)])  #### 画参考线
        #plt.xlabel('$t_{ij} (mins)$',fontsize=12)
        #plt.ylabel(r'$log(w_{ij}/\left (C N_{i}^{\alpha}N_{j}^{\beta} \right ))$',fontsize=12)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        #plt.xlim(0,150 )
        #plt.ylim(0,100)   
        if fpath:
            plt.savefig(fpath+'.png',dpi=100) # 指定分辨率
            plt.close()
            return 0
        else:
            #plt.show()
            #pass  # 不显示的话之后还可以继续画线什么的
            plt.show()


###############################################################################
### 加colorbar的散点图
def scatter_with_colorbar(list_x,list_y, list_value, s=3, vmin=None, vmax=None, marker='s'):
    cm = plt.cm.get_cmap('RdYlBu')
    vmax=vmax if vmax else max(list_value)
    vmin=vmin if vmin else min(list_value)
    sc = plt.scatter(list_x, list_y, c=list_value, vmin=vmin, vmax=vmax, s=s, cmap=cm,zorder=2,marker=marker,alpha=0.9)
    plt.colorbar(sc)

    
#####################################################################################
class ImPlot:
    def __init__(self,file=None,region='China'):
        self.setting(region)
        self.baseboard = mpimg.imread(file) if file else None
        self.array = None
    
    def setting(self,region='China'):
        fig, self.ax=plt.subplots(1,1,figsize=(6,6),dpi=150)
        if region=='China':
            self.extent=(73.4997347, 134.7754563, 17.7, 53.560815399999996)  # x0,x1,y0,y1
        elif region=='Europe':
            self.extent=(-10.5575303,40.227580100000004, 34.0,71.3848787 )  ## (34.0, -10.5575303, 71.3848787, 40.227580100000004) 
        self.ax.set_xlim(self.extent[0], self.extent[1])  # 中国大陆
        self.ax.set_ylim(self.extent[2], self.extent[3])    
        self.ax.axis('equal')
        self.ax.axis('off')
   
    def load_polygon(self, lons, lats, facecolor='red', edgecolor='k'):
        """  加载多边形
            要求输入的数据格式为：
            lons: 一个lon列表
            lats:一个lats列表
        """
        for i in range(len(lats)):
            self.ax.fill(eval(lons[i]),eval(lats[i]),facecolor="red",edgecolor="k",alpha=1.0, linewidth=0.1)
            
    def load_array(self, array, extent):
        """ 加载array,
            extent: 设定边界范围 [minx,maxx,miny,maxy]  例如: [90,120,30,45] 
        """
        self.array = np.ma.masked_where(array<0.005,array) ## 掩码数组
        self.array_extent = extent
    
    def plot_points(self, x,y,marker='x',color='red',alpha=0.5,s=2,text=None):
        """画点，可以是多个点
        """
        plt.scatter(x,y,zorder=4, alpha=alpha,s=s,facecolors=color, edgecolors=color,marker=marker)
        if text: ## 如果给定了点的名字，加入名字
            for i in range(len(text)):
                plt.text(x[i]+0.3, y[i], text[i]) # xx-small            , fontsize='small'

    def plot_line(self, x,y, color="blue",alpha=1,linewidth=1):
        """画线
        """
        plt.plot(x,y,color=color,alpha=alpha, linewidth=linewidth )
      
        
    def imshow(self, fpath=None, extent=None):
        if isinstance(self.baseboard,np.ndarray):
            self.ax.imshow(self.baseboard,extent=self.extent, alpha=1)
        if isinstance(self.array, np.ma.core.MaskedArray):
            img = self.ax.imshow(self.array, extent=self.array_extent, 
                  origin='lower', interpolation='None', 
                  cmap='viridis',alpha=0.9,zorder=1,
                  norm=matplotlib.colors.LogNorm(vmin=0.1, vmax=np.max(self.array)),
                  #norm=matplotlib.colors.PowerNorm(gamma=0.5),  # 0.5
                 aspect='auto')  ## interpolation="bicubic" # 'viridis'
            plt.colorbar(img, orientation='vertical')
#        if isinstance(self.array2, np.ndarray):
#            img = self.ax.imshow(self.array2, extent=self.array2_extent, 
#                  origin='lower', interpolation='None', 
#                  alpha=0.9,zorder=4,  ## cmap='viridis',
#                  norm=matplotlib.colors.PowerNorm(gamma=0.5),
#                 aspect='auto')  ## interpolation="bicubic" # 'viridis'
##
#
        if extent:    ## 有手动设置的边界
            self.ax.set_xlim(extent[0], extent[1])
            self.ax.set_ylim(extent[2], extent[3])          
        
        if fpath:
            plt.savefig(fpath+'.png',dpi=100) # 指定分辨率
            plt.close()
            return 0
        else:
            #plt.show()
            #pass  # 不显示的话之后还可以继续画线什么的
            plt.show()
######################################################
# 通过组合这些简单的颜色、线型，可以满足基本的作图需求
colors = ['b','g','r','c','m','y','k',]  # 简单的颜色
linestyles = ['-','--','-.',':']  # plt.plot的线型
# 点型
markers = [',', 'o', '^', 'v', '<', '>', 's', '+', 'x', 'D', 'd', ## 's' 是方块
    '1','2', '3','4',  # 三脚架朝上下左右
    'h', 'H','p',  # 六角形五角形
     '|', '_']  # 垂线水平线

#colors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)  ### 这里边有足够数量的颜色可供使用
#
## Sort colors by hue, saturation, value and name.
#by_hsv = sorted((tuple(mcolors.rgb_to_hsv(mcolors.to_rgba(color)[:3])), name)
#                for name, color in colors.items())
#colors = list(colors.keys())

# Have colormaps separated into categories:  
# http://matplotlib.org/examples/color/colormaps_reference.html 
cnames = {
'aliceblue':            '#F0F8FF',
'antiquewhite':         '#FAEBD7',
'aqua':                 '#00FFFF',
'aquamarine':           '#7FFFD4',
'azure':                '#F0FFFF',
'beige':                '#F5F5DC',
'bisque':               '#FFE4C4',
'black':                '#000000',
'blanchedalmond':       '#FFEBCD',
'blue':                 '#0000FF',
'blueviolet':           '#8A2BE2',
'brown':                '#A52A2A',
'burlywood':            '#DEB887',
'cadetblue':            '#5F9EA0',
'chartreuse':           '#7FFF00',
'chocolate':            '#D2691E',
'coral':                '#FF7F50',
'cornflowerblue':       '#6495ED',
'cornsilk':             '#FFF8DC',
'crimson':              '#DC143C',
'cyan':                 '#00FFFF',
'darkblue':             '#00008B',
'darkcyan':             '#008B8B',
'darkgoldenrod':        '#B8860B',
'darkgray':             '#A9A9A9',
'darkgreen':            '#006400',
'darkkhaki':            '#BDB76B',
'darkmagenta':          '#8B008B',
'darkolivegreen':       '#556B2F',
'darkorange':           '#FF8C00',
'darkorchid':           '#9932CC',
'darkred':              '#8B0000',
'darksalmon':           '#E9967A',
'darkseagreen':         '#8FBC8F',
'darkslateblue':        '#483D8B',
'darkslategray':        '#2F4F4F',
'darkturquoise':        '#00CED1',
'darkviolet':           '#9400D3',
'deeppink':             '#FF1493',
'deepskyblue':          '#00BFFF',
'dimgray':              '#696969',
'dodgerblue':           '#1E90FF',
'firebrick':            '#B22222',
'floralwhite':          '#FFFAF0',
'forestgreen':          '#228B22',
'fuchsia':              '#FF00FF',
'gainsboro':            '#DCDCDC',
'ghostwhite':           '#F8F8FF',
'gold':                 '#FFD700',
'goldenrod':            '#DAA520',
'gray':                 '#808080',
'green':                '#008000',
'greenyellow':          '#ADFF2F',
'honeydew':             '#F0FFF0',
'hotpink':              '#FF69B4',
'indianred':            '#CD5C5C',
'indigo':               '#4B0082',
'ivory':                '#FFFFF0',
'khaki':                '#F0E68C',
'lavender':             '#E6E6FA',
'lavenderblush':        '#FFF0F5',
'lawngreen':            '#7CFC00',
'lemonchiffon':         '#FFFACD',
'lightblue':            '#ADD8E6',
'lightcoral':           '#F08080',
'lightcyan':            '#E0FFFF',
'lightgoldenrodyellow': '#FAFAD2',
'lightgreen':           '#90EE90',
'lightgray':            '#D3D3D3',
'lightpink':            '#FFB6C1',
'lightsalmon':          '#FFA07A',
'lightseagreen':        '#20B2AA',
'lightskyblue':         '#87CEFA',
'lightslategray':       '#778899',
'lightsteelblue':       '#B0C4DE',
'lightyellow':          '#FFFFE0',
'lime':                 '#00FF00',
'limegreen':            '#32CD32',
'linen':                '#FAF0E6',
'magenta':              '#FF00FF',
'maroon':               '#800000',
'mediumaquamarine':     '#66CDAA',
'mediumblue':           '#0000CD',
'mediumorchid':         '#BA55D3',
'mediumpurple':         '#9370DB',
'mediumseagreen':       '#3CB371',
'mediumslateblue':      '#7B68EE',
'mediumspringgreen':    '#00FA9A',
'mediumturquoise':      '#48D1CC',
'mediumvioletred':      '#C71585',
'midnightblue':         '#191970',
'mintcream':            '#F5FFFA',
'mistyrose':            '#FFE4E1',
'moccasin':             '#FFE4B5',
'navajowhite':          '#FFDEAD',
'navy':                 '#000080',
'oldlace':              '#FDF5E6',
'olive':                '#808000',
'olivedrab':            '#6B8E23',
'orange':               '#FFA500',
'orangered':            '#FF4500',
'orchid':               '#DA70D6',
'palegoldenrod':        '#EEE8AA',
'palegreen':            '#98FB98',
'paleturquoise':        '#AFEEEE',
'palevioletred':        '#DB7093',
'papayawhip':           '#FFEFD5',
'peachpuff':            '#FFDAB9',
'peru':                 '#CD853F',
'pink':                 '#FFC0CB',
'plum':                 '#DDA0DD',
'powderblue':           '#B0E0E6',
'purple':               '#800080',
'red':                  '#FF0000',
'rosybrown':            '#BC8F8F',
'royalblue':            '#4169E1',
'saddlebrown':          '#8B4513',
'salmon':               '#FA8072',
'sandybrown':           '#FAA460',
'seagreen':             '#2E8B57',
'seashell':             '#FFF5EE',
'sienna':               '#A0522D',
'silver':               '#C0C0C0',
'skyblue':              '#87CEEB',
'slateblue':            '#6A5ACD',
'slategray':            '#708090',
'snow':                 '#FFFAFA',
'springgreen':          '#00FF7F',
'steelblue':            '#4682B4',
'tan':                  '#D2B48C',
'teal':                 '#008080',
'thistle':              '#D8BFD8',
'tomato':               '#FF6347',
'turquoise':            '#40E0D0',
'violet':               '#EE82EE',
'wheat':                '#F5DEB3',
'white':                '#FFFFFF',
'whitesmoke':           '#F5F5F5',
'yellow':               '#FFFF00',
'yellowgreen':          '#9ACD32'}
