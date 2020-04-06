"""
过滤铁路网，railway=rail
带有 "maxspeed" 信息
生成 _links.csv 和 _nodes.csv


"""
import osmium as o
import time
import sys
import networkx as nx
sys.path.append(r'/run/media/pengfei/OTHERS/pythonlibs')
import lib_osm
import lib_graph
import shapely.wkb as wkblib
import pandas as pd

wkbfab = o.geom.WKBFactory()

class WayFilter(o.SimpleHandler):
    def __init__(self,):
        o.SimpleHandler.__init__(self)    
        self.G = nx.Graph()
        self.dict_IDLoc = {}
        
    def way(self, w):
        if lib_osm.filterRailways(w): # 是有效的铁轨    railway=rail
            maxspd = w.tags.get('maxspeed','100')  # default maxspeed=100km/h
            maxspd = lib_osm.convert_maxspeed(maxspd)

            ids = []
            for n in w.nodes:
                ids.append(n.ref)            
                loc = (n.lon,n.lat)  # throws an exception if the coordinates are missing
                self.dict_IDLoc[n.ref] = loc
            
            if len(ids)>=2:
                for i in range(len(ids)-1):
                    self.G.add_edge(ids[i],ids[i+1],maxspeed=maxspd)



t1 = time.time()
sfrom = '/run/media/pengfei/OTHERS/OSM/OSMData/China/china-latest-transport.osm.pbf'
tf = WayFilter()
tf.apply_file(sfrom,locations=True)    

f = '/run/media/pengfei/OTHERS/OSM/OSMData/China/china-latest-rail-links.csv'
lib_graph.saveG_toFile(tf.G,f)

out = [[ID, *tf.dict_IDLoc[ID]] for ID in tf.dict_IDLoc] # id,lon,lat
df = pd.DataFrame(out, columns=['ID','lon','lat'])
f_nodes = '/run/media/pengfei/OTHERS/OSM/OSMData/China/china-latest-rail-nodes.csv'
df.to_csv(f_nodes)