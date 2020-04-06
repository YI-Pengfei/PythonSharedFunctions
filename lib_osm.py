"""
Funcitons to operate with OSM data.  https://planet.openstreetmap.org/

  - 2019.08.23 OSRM
  - 2019.08.15 OSM(XML) Parser.
  
"""

import os
os.system
import time
import subprocess

import geopy
import Levenshtein
import re
"""Part1, Filtering & extracting... 
Although "OSMRailway" code gives a lot of references to extract network, the process
of filter, creating database takes relatively a long time. 

An alternative way is to use commond line tools, first do a rough filter that reduces the data to a manageable level,
then process with python.
Two tools are candidates: 1. osmium tool  (https://docs.osmcode.org/osmium/latest/)
                          2. osmosis  (https://wiki.openstreetmap.org/wiki/Osmosis/Detailed_Usage_0.46#--tag-filter_.28--tf.29) 
"""

def osmFilter(infile, type='highway'):
    """ Rely on osmium command line tool
        do the basic filtering task.
    """
    key = 'highway'
    values = ['motorway', 'trunk', 'primary', 'secondary', 'tertiary']
    suffix = '_link'
    
    vs = []
    for v in values:
        vs += [v, v+suffix]
    values = vs
    t1 = time.time()

    print('Extraction starts--step1, filtering key:', key)
    middle_file1 = infile[:-8]+'-'+key+'.osm.pbf'  #####  加了一个key名
    os.system('osmium tags-filter -o %s %s %s' % (middle_file1, infile, key))
    print('Extract %s finished, time used %ds..' % (key, int(time.time()-t1)))

    print('Extraction starts, filtering values:')
    print(values)
    for v in values:
        outfile = middle_file1[:-8]+'-'+v+'.osm.pbf'
        os.system('osmium tags-filter -o %s %s %s=%s'%(outfile, middle_file1, key,v))
        print('Extract %s finished, time used %ds..'%(v,int(time.time()-t1)))

        outfile2 = outfile[:-8]+'-loc'+'.osm.pbf'
        add_loc2ways(outfile,outfile2)
        print('  Add location finished, time used %ds..'%(int(time.time()-t1)))
    print('Finihsed...')



def extractTransport(infile, keys, pairs, addLocation=False, removeTemp=True):
    """
    A substitute for Sebastian's "1ExtractTransport.py" program.
    Rely on osmium command line tool
    根据这个函数可以在将来更改要过滤的键/值，执行不同的过滤
    （在相同目录下生成infile-transport.osm.pbf文件）
    """
#    keys = ["bus", "tram", "rail", "subway", "railway", "public_transport", "station", "aerialway"]
#    pairs = {
#            "site": ["stop_area","stop_area_group"], 
#            "building": ["train_station","station"],
#            "route": ["bus","tram","train","railway","light_rail","rail","subway","ferry"],
#            "highway": ["bus_stop","tram_stop","forward_stop","backward_stop"], 
#            "ferry": ["yes"],
#            "amenity": ["ferry_terminal","bus_station"],
#            }

    t1 = time.time()
    tempfiles = []
    print('Step 1, key filtering. Extraction starts.....')
    for k in keys:  # 只限制 键
        print('        %s..'%k)
        outfile = infile[:-8]+'-'+k+'.osm.pbf'
        os.system('osmium tags-filter -o %s %s %s'%(outfile, infile, k))
        print('Extract %s finished, time used %ds..'%(k,int(time.time()-t1)))
        tempfiles.append(outfile)

    print('Step 2-1, key filtering...')
    to_removes = []
    for k in pairs:  #  键值对中只限制 键
        print('        %s..'%k)
        outfile = infile[:-8]+'-'+k+'.osm.pbf'
        os.system('osmium tags-filter -o %s %s %s'%(outfile, infile, k))
        print('Extract %s finished, time used %ds..'%(k,int(time.time()-t1)))
        to_removes.append(outfile)        

    print('Step 2-2, key-value filtering...')
    for k in pairs:  # 键值对中，加入对于 值 的限制
        values = pairs[k]
        temp_file = infile[:-8]+'-'+k+'.osm.pbf'   # 以中间文件作为输入，加上值限制
        for v in values:
            outfile = infile[:-8]+'-'+k+'-'+v+'.osm.pbf'
            os.system('osmium tags-filter -o %s %s %s=%s'%(outfile, temp_file, k,v))
            print('Extract %s=%s finished, time used %ds..'%(k,v,int(time.time()-t1)))
            tempfiles.append(outfile)
        print('Remove temp file %s'%temp_file)
        os.remove(temp_file)
    
    outfile = infile[:-8]+'-transport.osm.pbf'
    merge_files(tempfiles, outfile)  # 合并文件，有序且去重的

    if removeTemp:  # 不保留中间生成的文件
        for f in tempfiles:  # 删除中间生成的文件
            print('Remove temp file %s' % f)
            os.remove(f)

    if addLocation:  ### 如果要往原文件的way中添加位置，则执行
        outfile2 = outfile[:-8]+'-loc'+'.osm.pbf'
        add_loc2ways(outfile,outfile2)        
        print('Add location finished, time used %ds..'%(int(time.time()-t1)))
    print('Finish! Total time used: %ds' %int(time.time()-t1))


def add_loc2ways(infile, outfile):
    """ 向way中添加节点位置
        The out data can be processed with pyosmium like :
            for n in w.nodes:
                n.lon,n.lat
    """ 
    t1 = time.time()
    commond = 'osmium add-locations-to-ways --overwrite -o %s %s'%(outfile, infile)
    p = subprocess.Popen(commond, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
        print(line)
    print('Add location to ways finish, time used:',time.time()-t1)


def merge_files(list_files, outfile):
    """ 合并文件，是有序且去重的
    """
    files = ''
    for f in list_files:  # 连接所有生成的中间文件
        files += f+' '
    files = files.rstrip()
    os.system('osmium merge %s -o %s'%(files, outfile))  # 有序且去重的    

def convert_format(infile, outfile):
    """ 转换文件格式
    """
    os.system('osmium cat -o %s %s'%(outfile, infile))


def filterStations(X):
    """过滤火车站
    X: pyosmium object
    """
    ### 需要去除的osm对象
    excudes = ["subway", "light_rail", "tram", "bus", "monorail"]  # monorail 单轨    
    for k in excudes:
        if k in X.tags:
            if X.tags.get(k) in ["yes"]:
                return False    
    if "railway" in X.tags:
        if X.tags.get("railway") in ["abandoned","disused","ligh_rail","subway"]:
            return False
    if "station" in X.tags:
        if X.tags.get("station") in ["light_rail","subway", "monorail"]:
            return False 
    ### 需要保留的osm对象    
    keep=False
    if "railway" in X.tags:
        if X.tags.get("railway") in ["stop","station","halt","stop_position"]:
            keep=True
            
    #if "site" in X.tags:
    #    if X.tags.get("site") in ["stop_area","stop_area_group"]:
    #        keep=True

    return keep

def filterRailways(X):
    """ 过滤火车轨道 
        X: pyosmium object 只过滤way就行了
    """
    ### 不是火车铁路轨道的去除，废弃的去除
    excudes = ["subway", "light_rail", "tram", "bus", "monorail"]  # monorail 单轨    
    for k in excudes:
        if k in X.tags:
            if X.tags.get(k) in ["yes"]:
                return False    
    for c in ['route', 'railway']:
#        if c in X.tags:
#            if X.tags.get(c) in ["abandoned","disused","ligh_rail","subway"]:
#                return False    
        if c in X.tags and X.tags.get(c,'')=='rail':
            return True


def convert_maxspeed(inmaxspeed):
    """
        inmaxspeed: string , '160 kph', '90mph', '120'
    """
    spd = re.sub(r'\D','',inmaxspeed)  # remove non-digit
    if spd == '':  ### 没有一个有效的值
        return -1
    if 'mph' in inmaxspeed:
        return round(float(spd)*1.60934,2)
    else:
        return round(float(spd),2)

###############################################################################
"""
    PART2, Geocoding(address-->location) rely on Nominatim, 
"""

def geocode(name, maxResults=3,bbox=[(-90,-180),(90,180)],tolerance=0.8, mode='local',Type='station'):
    """ geocode
    :param name:       station name to query
    :param maxResults: the number of results return from Nominatim, the more it returns, the more chances to get the results you want
    :param bbox:       bounding box
    :param tolerance:  Levenshtein ratio the measure the similarity between result and query
    :param mode:       'local'  'online'
    :param Type:       Type to query, can be None. For example: 'station'
    :return:           OsmResult object
    """
    url = 'localhost/nominatim'
    if Type:
        query = name+'+['+Type+']'
    else:
        query = name
    
    if mode=='local':  ## 本地服务器
        g = geopy.geocoders.Nominatim(domain=url,scheme='http',bounded=True, view_box = bbox,timeout=None) 
    if mode=='online': ###
        g = geopy.geocoders.Nominatim(bounded=True, view_box = bbox,timeout=None)        

    list_r = g.geocode(query, exactly_one=False, limit=maxResults, language='en',addressdetails=True) # ,namedetails=True
    if not list_r: ## 没有结果
        return None 
    for r in list_r:
        o = _get_r(name, r, tolerance)
        if o: 
            return o


def geocodeGoogle():
    ### 基本上不能用
    api_key = 'AIzaSyAVwjaaOBKbssuyQsvyqQAQDwfuzO1PKCA'        
    g = geopy.geocoders.GoogleV3(api_key=api_key, timeout=None, domain='maps.googleapis.com')


def _get_r(name, r, tolerance):
    ##
    if not r:
        return None
    o = OsmResult(r.raw)
    if name in o.synonyms or _clean_name(name) in o.synonyms:  # Exact match --> perfect!
        return o
    else:   # with tolerance
        for n in o.synonyms:
            d1 = Levenshtein.ratio(n, name)
            d2 = Levenshtein.ratio(n, _clean_name(name))
            if d1>=tolerance or d2>=tolerance:
                o.set_confidence(max(d1,d2))
                return o
    return None


def _clean_name(name):
    #name = name.replace('(',' (').replace(')',') ')
    #name = re.sub(' +',' ',name)
    if name.endswith("Hbf"):
        return name.replace("Hbf","Hauptbahnhof")
    return name
        
        
class OsmResult:

    def __init__(self, json_content):
        # create safe shortcuts
        self._address = json_content.get('address', {})
        self.raw = json_content
        self.confidence = -1
        
    def set_confidence(self, conf):
        self.confidence = conf

    def get_confidence(self):
        if self.confidence>0:
            return self.confidence
    
    def to_dict(self,name=None,utc=None,country=None):
        if not name:
            name = self.name
        out = {name:{}}
        synonyms = ''
        for s in self.synonyms:
            synonyms+=s+';'
        out[name] = {'lon':self.lon,'lat':self.lat,'synonyms':synonyms}
        if utc:
            out[name]['UTC']=utc
        if country:
            out[name]['country']=country
        
        return out
        
    @property
    def lat(self):
        lat = self.raw.get('lat')
        if lat:
            return float(lat)
    @property
    def lon(self):
        lon = self.raw.get('lon')
        if lon:
            return float(lon)
    @property
    def address(self):
        return self.raw.get('display_name')
    @property
    def name(self):
        return self.raw['namedetails']['name']
    @property
    def country(self):
        if not self._address:
            return 'nan'
        return self._address.get('country')
    @property
    def synonyms(self):
        if 'namedetails' in self.raw:
            return set(self.raw['namedetails'].values())
        else:
            return [self.raw['display_name']]


###############################################################################
"""
    PART3, parse osm xml.
"""
import lxml.etree as ET
from shapely.geometry import Point
from shapely.geometry import MultiPoint
from shapely.geometry import LineString
from shapely.geometry import MultiLineString
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon

import pandas as pd
import numpy as np
import re

class OSMXML:
    def __init__(self):
        pass
    def load_data(self, osmfile):
        """加载.osm格式的文件到内存，直接组装好每个对象
        """
        self.tree = ET.parse(osmfile)
        self.root = self.tree.getroot()
        
        self.osm_objs = self.root.findall("./*")
        #self.nodes = self.root.findall('./node')
        #self.ways = self.root.findall('./way')
        #self.relations = self.root.findall('./relation')
        self.set_members = set()  # 记录作为成员的osm objects...

    def create_geometry(self):
        self.dict_IDInfo = {}
        for o in self.osm_objs:
            if o.tag=='node':
                ID, p, type_, names = self.parseN(o)
            elif o.tag=='way':
                ID, p, type_, names = self.parseW(o)
            elif o.tag=='relation':
                ID, p, type_, names = self.parseR(o)

            if p:  # 得有位置，没位置没意义
                self.dict_IDInfo[ID] = {'geometry':p, 'names':names, 'type':type_}
    
    
    def create_df(self):
        out = []
        
        for ID in self.dict_IDInfo:
            if ID in self.set_members:  # 删除成员
                continue
            
            location = self.dict_IDInfo[ID]['geometry']
            type_ = self.dict_IDInfo[ID]['type']
            if type_=='useless':
                continue
            names = self.dict_IDInfo[ID]['names']
            for name in names:
                out.append([name, ID, location[0], location[1], type_])
            
        return pd.DataFrame(out,columns=['name', 'id', 'lon', 'lat', 'type'])

    
    def parseN(self,n):
        ID = int(n.attrib['id'])
        lat = float(n.attrib['lat'])
        lon = float(n.attrib['lon'])
        
        type_, names = self.parseTag(n)
        return ID, (lon,lat), type_, names
    
    def parseW(self,w):
        ID = int(w.attrib['id'])
        points = []
        set_names = set()
        for n in w.findall('nd'):
            nid = int(n.attrib['ref'])
            
            if not nid in self.dict_IDInfo:
                print("no way member ID:",nid)
                continue
                
            n_names = self.dict_IDInfo[nid]['names']
            set_names = set_names.union(n_names)   # 成员的名字添加到way中
            points.append(self.dict_IDInfo[nid]['geometry'])
            self.set_members.add(nid)  ## 待删除的成员
                
        type_, names = self.parseTag(w)
        set_names.union(names)
                
        return ID, self._represent_point(points), type_, set_names
        ## 判断是否是封闭多边形
        #if points[0] == points[-1]:
        #    return ID, Polygon(points)
        #else:
        #    return ID, LineString(points)
    
    def parseR(self,r):
        ID = int(r.attrib['id'])
        points = []
        set_names = set()
        for m in r.findall('member'):
            if m.attrib['type']=='way':
                m_id = int(m.attrib['ref'])
            elif m.attrib['type']=='node':
                m_id = int(m.attrib['ref'])
            elif m.attrib['type']=='relation':
                m_id = int(m.attrib['ref'])
            
            if not m_id in self.dict_IDInfo:
                print('no relation member:',m_id)
                continue
            
            m_names = self.dict_IDInfo[m_id]['names']
            set_names = set_names.union(m_names)   # 成员的名字添加到relation中
            points.append(self.dict_IDInfo[m_id]['geometry'])
            self.set_members.add(m_id)  ## 待删除的成员

        type_, names = self.parseTag(r)
        set_names.union(names)
        return ID, self._represent_point(points), type_, set_names
    
    def parseTag(sef,o):
        """解析tag
        o: osm object
        """
        set_names = set()
        type_ = ""
        for tag in o.findall('tag'):  
            if 'railway'== tag.attrib['k']:
                type_ = tag.attrib['v']   ## station, stop, halt
            
            if 'name' in tag.attrib['k']:
                value = tag.attrib['v']                    
                if re.search('\d.*(км|km|კმ|Km|KM)',value):   # 没有有用的标签
                    return "useless", set()
                set_names.add(value)        
        
        return type_, set_names
        
    
    def query(self,ID):
        return self.root.find('*[@id="%d"]'%ID)
    
    #def name(self,name):
    #    n.find('tag[@k="name"]').attrib
    
    def _represent_point(self, points):
        return None if len(points)==0 else list(map(np.median,zip(*points)))

        
def get_represent_point(points):
    return None if len(points)==0 else list(map(np.median,zip(*points)))
###############################################################################
"""
    PART4, fuzzy match 
"""
from fuzzywuzzy import fuzz, process

def fuzzy_merge(df1, df2, key1, key2, threshold=90, limit=2):
    '''
    df_1 is the left table to join
    df_2 is the right table to join
    key1 is the key column of the left table
    key2 is the key column of the right table
    threshold is how close the matches should be to return a match
    limit is the amount of matches will get returned, these are sorted high to low
    '''
    s = df2[key2].tolist()

    m = df1[key1].apply(lambda x: process.extract(x, s, limit=limit))   #将函数应用到由各列或行形成的一维数组上。DataFrame的apply方法
    df1['matches'] = m
    m2 = df1['matches'].apply(lambda x: ','.join([i[0] for i in x if i[1] >= threshold]))
    df1['matches'] = m2

    return df1


###############################################################################
"""
    PART5, OSRM
"""
import simplejson
import urllib.request

class OSRM:
    """
    OSRM路径规划
    注意：所有的经纬度位置 都是 (lon,lat)的形式
    """
    def __init__(self, region='China'):
    	pass
#        sudoPassword = '1358'
#        filePaths = {'China': '/data/OSRM-Data/ChinaData/china-latest.osrm',
#                     'Europe': '/data/OSRM-Data/EuropeData/europe-latest.osrm'  }
#        filePath = filePaths[region]
#        command = 'osrm-routed '+filePath +'&'  ## --algorithm=MLD   ## 指定algorithm时 欧洲数据会出错

        #d = os.system('echo %s|sudo -S %s' % (sudoPassword, command)) 
        #print('OSRM successfully started..') if d==0 else print('OSRM failed')

    def queryRoute(self,source,destination,host="127.0.0.1:5000"):        
        """ location: (lon,lat)
            返回的时间以 s 为单位
        """
        lon1,lat1=source
        lon2,lat2=destination
        url="http://"+host+"/route/v1/driving/"
        url+="%f,%f;"%(lon1,lat1)
        url+="%f,%f"%(lon2,lat2)
        url+="?steps=false&geometries=geojson"
        XURL=-1
        try:
            XURL=urllib.request.urlopen(url)
            L=simplejson.load(XURL)
            
            coords=L["routes"][0]["geometry"]["coordinates"]
            duration=float(L["routes"][0]["duration"])
            steps=[]
            for (lon,lat) in coords:            
                steps.append((lon,lat))
            
            steps.append((coords[-1][0],coords[-1][1]))
        except urllib.error.HTTPError:
            steps=[]
            duration=-1
        if XURL!=-1:
            XURL.close()    

        return steps, duration
## 用法
#Beijing = (116.36575426379041, 39.9196349206612)
#Guangzhou = (113.29426558032033,23.112904118079268)
#(116.420991, 39.901642) (116.4, 39.95)
#steps,traveltime=osrm.queryRoute(Guangzhou,Beijing,"127.0.0.1:5000",)
#print("Travel time (in minutes):",traveltime)
#print("Points along route:",route)
