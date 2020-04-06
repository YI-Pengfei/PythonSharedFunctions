import sys
sys.path.append(r'/run/media/pengfei/OTHERS/pythonlibs')
from lib_osm import filterStations

import osmium as o
import time


keepd={}
keepd["r"]=set()
keepd["w"]=set()
keepd["n"]=set()


class RelationFilter(o.SimpleHandler):
    def __init__(self,):
        o.SimpleHandler.__init__(self)    
    
    def relation(self, r):        
        keep=filterStations(r)        
        if keep or r.id in keepd["r"]:        
            keepd["r"].add(r.id)
            for m in r.members:
                keepd[m.type].add(m.ref)

class WayFilter(o.SimpleHandler):
    def __init__(self,):
        o.SimpleHandler.__init__(self)    

    def way(self, w):
        keep=filterStations(w)                
        
        if keep or w.id in keepd["w"]:        
            keepd["w"].add(w.id)
            for m in w.nodes:
                keepd["n"].add(m.ref)

class NodeFilter(o.SimpleHandler):
    def __init__(self,):
        o.SimpleHandler.__init__(self)    

    def node(self, n):        
        keep=filterStations(n)                                    
        
        if keep or n.id in keepd["n"]:        
            keepd["n"].add(n.id)

class Convert(o.SimpleHandler):

    def __init__(self, writer):
        o.SimpleHandler.__init__(self)
        self.writer = writer

    def node(self, n):
        if n.id in keepd["n"]:
            self.writer.add_node(n)

    def way(self, w):
        if w.id in keepd["w"]:
            self.writer.add_way(w)

    def relation(self, r):
        if r.id in keepd["r"]:
            self.writer.add_relation(r)



sfrom = '/home/pengfei/Europe/europe-latest-transport.osm.pbf'
sto = '/home/pengfei/Europe/europe-latest-transport-station.osm.pbf'
#sfrom = '/run/media/pengfei/OTHERS/OSMData/China/china-latest-transport.osm.pbf'
#sto = '/run/media/pengfei/OTHERS/OSMData/China/china-latest-transport-station.osm.pbf'
t1 = time.time()
print("Start to extract railway stations..")
tf = RelationFilter()
tf.apply_file(sfrom)    
print("RelationFilter finish, R:%d W:%d N:%d"%(len(keepd["r"]),len(keepd["w"]),len(keepd["n"])))
print("Time used: %ds"%int(time.time()-t1))

tf = WayFilter()
tf.apply_file(sfrom)    
print("WayFilter finish, R:%d W:%d N:%d"%(len(keepd["r"]),len(keepd["w"]),len(keepd["n"])))
print("Time used: %ds"%int(time.time()-t1))

tf = NodeFilter()
tf.apply_file(sfrom)    
print("NodeFilter finish, R:%d W:%d N:%d"%(len(keepd["r"]),len(keepd["w"]),len(keepd["n"])))
print("Time used: %ds"%int(time.time()-t1))

#try:
#    os.remove(sto)
#except OSError:
#    pass

writer = o.SimpleWriter(sto)
handler = Convert(writer)
handler.apply_file(sfrom)
writer.close()
