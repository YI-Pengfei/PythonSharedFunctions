"""
	2019.09.19 对于已经做好的欧洲铁路列车时刻表，这个库的作用主要是读取XML格式的时刻表数据
	Created on Sat May 25 10:19:24 2019
	每个车次是一个类对象，成员包括 车站 对象，外链时区信息，位置信息等辅助信息
	@author: pengfei
"""
import re
from prettytable import PrettyTable
import sys
sys.path.append(r'/run/media/pengfei/OTHERS/pythonlibs')
from haversine import haversine
import pandas as pd
from collections import defaultdict
#import xml.etree.ElementTree as ET
import lxml.etree as ET
import xml.dom.minidom as minidom

class Train:
    def __init__(self):
        self.meta = {}
        self.basic_data = defaultdict(dict) # 存一系列车站的信息，一定要确保进来的都是字符串类型
        self.merged = []
        self.possible = []  # 记录高度相似的列车
        # basic_data中的时间是utc时间，输出为XML时改为utc时间
        pass
    def load_data(self,dict_header, list_stations, list_stationInfo,list_adInfo, list_times,dict_loc):
        """
        :param dict_header: 表头，指示该车的信息,要求table_number是列表类型
        :param list_stations: 车站名列表
        :param list_stationInfo: 车站名对应的信息
        :param list_adInfo: 车站名对应的停车/发车信息
        :param list_times: 时刻,已经是清理过的了
        """
        if not isinstance(dict_header,dict):
            print('sdfffffffffffffffffffff')
            return -1
        self.daySign = dict_header.get('daySign','1234567')
        self.trainType = dict_header.get('trainType','')
        self.trainNumber = (dict_header.get('trainNumber',[]) if dict_header.get('trainNumber',[])!=[""] else [])
        self.refNumber = dict_header.get('refNumber',[])
        
        for i in range(len(list_stations)):
            name = list_stations[i]
            ad_sign = list_adInfo[i]
            time = list_times[i] # list_times已经是清理过的，字符串类型
            if time=='nan' or time=='':
                continue
            utc = dict_loc[name]['UTC']
            self.basic_data[name]['UTC']=utc # 都是字符串型
            if ad_sign == 'a.':
                self.basic_data[name]['arrive'] = local_to_utc(int(time),utc) # 存为UTC时间
            elif ad_sign == 'd.':
                self.basic_data[name]['depart'] = local_to_utc(int(time),utc)
            # 取出这个车站对应的信息
            stationInfo = ( eval(list_stationInfo[i]) if list_stationInfo[i]!='nan' else {})
            if stationInfo.get('number',[]) and stationInfo.get('font','n')=='i': # 只给斜体字的添加ref
                numbers = []
                for n in stationInfo['number']:
                    numbers.append(str(n).replace(',',''))
                # 将引用的表号放进去
                if 'ref' not in self.basic_data[name]:
                    self.basic_data[name]['ref'] = numbers   
                else:
                    self.basic_data[name]['ref'] += numbers  
                
    def add_meta(self, file_name, table_number, country, trainID):
        self.meta['id'] = str(trainID)  # 转化为字符串
        self.meta['tableNumber'] = str(table_number)
        self.meta['country'] = country
        self.meta['fileName'] = file_name
    """ 弃用，直接在load_data时加进去
    def add_utc(self,):
        # 为各车站添加时区信息
        # dict_loc是以车站名为key的字典
        for s in self.basic_data:
            if s not in dict_loc:
                print(s)
                continue
            self.basic_data[s]['UTC']=str(dict_loc[s]['UTC']) # 都是字符串型
    """
    def to_element(self):
        # 输出这个列车的信息为XML的element，输出的时间是UTC时间
        rstr = r"[\=\(\)\,\/\\\:\*\?\"\<\>\|\' ']"
        train = ET.Element('train')
        # 元数据信息
        for m in self.meta:  # 将元数据信息设置为属性
            train.set(m,replace_special(self.meta[m]))
        if self.merged:
            merged_list = [dict(t) for t in {tuple(d.items()) for d in self.merged}]
            #print(self.merged,type(self.merged))
            for item in merged_list:
                merged = ET.Element('merge_with')
                for m in item:
                    merged.set(m,item[m])
                train.append(merged)

        if self.possible:
            possible_list = [dict(t) for t in {tuple(d.items()) for d in self.possible}]
            for item in possible_list:
                possible = ET.Element('possibly_connected_with')
                for m in item:
                    possible.set(m,item[m])
                train.append(possible)
        
        train.set('daySign',self.daySign) # 可用的天，属性
        if self.trainType:
            train.set('trainType',re.sub(rstr,'',self.trainType)) #  把数字，字母之外的其他字符去掉
        # 为train添加子元素 车号
        for tn in self.trainNumber:
            elem = ET.SubElement(train,"trainNumber")  # 列车号上含有特殊字符，去掉
            elem.text = re.sub(rstr,'',str(tn)) #  把数字，字母之外的其他字符去掉
        # 为train添加子元素 引用表号
        for rn in self.refNumber:
            elem = ET.SubElement(train,"refNumber") 
            elem.text = str(rn) #         
        # 创建新的元素，station
        stop_id = 0
        for name in self.basic_data:
            station = ET.Element('station') # 创建新的元素，tag为station
            station.set('stop_id',str(stop_id))
            stop_id+=1
            station.set('name',name) # 设置车站名属性
            for attrib in self.basic_data[name]:
                utc = self.basic_data[name]['UTC'] # 取出时区信息
                if attrib=='arrive':
                    if int(self.basic_data[name][attrib])!=-1:
                        time = utc_to_local(int(self.basic_data[name][attrib]),int(utc)) # 转为本地时间
                        station.set(attrib,str(time).zfill(4)) # 为元素添加属性
                elif attrib=='depart':
                    if int(self.basic_data[name][attrib])!=-1:
                        time = utc_to_local(int(self.basic_data[name][attrib]),int(utc)) # 转为本地时间
                        station.set(attrib,str(time).zfill(4)) # 为元素添加属性
                elif attrib=='ref': #引用表号为一个列表
                    for r in self.basic_data[name][attrib]:
                        ref = ET.SubElement(station,attrib) # 为station添加一个子元素ref
                        ref.text = r # 引用表号为“123”  
                else: # 剩下的属性，直接添加为属性
                    station.set(attrib,str(self.basic_data[name][attrib]))
            # station element做好之后，添加到train element中
            train.append(station)
        return train

    def load_element(self,train):
        # 从element对象解析成类对象,外边传进来的是本地时间，进里面后转换为UTC时间
        self.daySign = train.get('daySign','1234567')
        self.trainType = train.get('trainType','')
        if 'TGV' in self.trainType:
            self.trainType='TGV'  # 纠正192页的问题
            #print(self.trainType)

        self.meta = {}
        self.meta['fileName'] = train.get('fileName','')
        self.meta['tableNumber'] = train.get('tableNumber','')
        self.meta['country'] = train.get('country','')
        self.meta['id'] = train.get('id','')
        self.trainNumber = []
        for tn in train.findall('trainNumber'):
            self.trainNumber.append(tn.text)
        # 如果是合并过的，读进来合并的信息
        for item in train.findall('merge_with'):
            self.merged.append(item.attrib)
        # 如果是跟另外的列车高度相似，读进来信息
        for item in train.findall('possibly_connected_with'):
            self.possible.append(item.attrib)
            
        self.refNumber = []
        for rn in train.findall('refNumber'):   
            self.refNumber.append(rn.text)  
        ###### 关键的地方来了，self.basic_data
        self.basic_data = defaultdict(dict)
        for station in train.findall('station'):
            s = station.get('name')
            utc = int(station.get('UTC')) # 整型
            at = local_to_utc(int(station.get('arrive','-1')),utc) # 统一成utc
            dt = local_to_utc(int(station.get('depart','-1')),utc)
            # 一切顺利的话，将本车站的信息装入basic_data
            if at!=-1:
                self.basic_data[s]['arrive'] = at  
            if dt!=-1:
                self.basic_data[s]['depart'] = dt   
            self.basic_data[s]['UTC'] = utc 
            # refs: 
            refs = []
            for r in station.findall('ref'):
                refs.append(r.text)
            if refs:
                self.basic_data[s]['ref'] = refs
            if station.get('table_from'):
                self.basic_data[s]['table_from'] = station.get('table_from')
        
        self.stations = list(self.basic_data.keys())
    
    def generate_aligntype(self):
        # 用于**合并操作**的形式，按时间顺序排列车次,没有转化为分钟制，只是加了隔天的余量
        self.align_type = {}  # {“车站;到发“：时刻,.......}
        self.name_utc = {}
        last_t = 0 # 处理隔天的情况
        plus = 0 # 时间增量，处理隔天的情况
        for name in self.basic_data:
            utc = self.basic_data[name]['UTC']
            # 处理到站时间
            at = self.basic_data[name].get('arrive',-1)
            if at!=-1:
                if at < last_t: # 隔天了
                    plus+= 2400 # 加一个24小时
                last_t = at
                # 将 车站名，时刻，发车/到站 加入其中
                self.align_type[name+";"+'a.'] = at+plus
                self.name_utc[name+";"+'a.'] = utc
            # 处理发车时间
            dt = self.basic_data[name].get('depart',-1)
            if dt!=-1:
                if dt < last_t: # 隔天了
                    plus += 2400 # 加一个24小时
                last_t = dt
                self.align_type[name+";"+'d.'] = dt+plus  
                self.name_utc[name+";"+'d.'] = utc
        name_t = list(self.align_type.items())
        self.running_period = [name_t[0][1],name_t[-1][1]]

    def compare_similarity(self, train_obj, commonN, difT=0, maxT=25):
        if self.trainNumber!=[] and train_obj.trainNumber!=[]: # 两者都是有列车号的，
            if not (set(self.trainNumber)&set(train_obj.trainNumber)): # 而二者的列车号不一致
                return 100000 # 不能合并        
        if not (len(set(self.stations) & set(train_obj.stations))>=commonN): # 没有公共的车站
            return 100000 
        count = 0
        count_ad = 0
        dif = 0
        common_stations = set(self.stations) & set(train_obj.stations)
        for name in common_stations:
            selfAT = self.basic_data[name].get('arrive',-1)
            selfDT = self.basic_data[name].get('depart',-1)
            objAT = train_obj.basic_data[name].get('arrive',-1)
            objDT = train_obj.basic_data[name].get('depart',-1)  
            
            if selfAT != -1 and objAT != -1:
                if not abs(t_to_mins(selfAT) - t_to_mins(objAT)) <= difT:
                    return 100000
                else:
                    count += 1
                    dif += abs(t_to_mins(selfAT) - t_to_mins(objAT))
            elif selfDT != -1 and objDT != -1:
                if not abs(t_to_mins(selfDT) - t_to_mins(objDT)) <= difT:
                    return 100000
                else:
                    count += 1
                    dif += abs(t_to_mins(selfDT) - t_to_mins(objDT))
            elif selfAT != -1 and objDT != -1 and abs(t_to_mins(selfAT) - t_to_mins(objDT)) <= maxT:  # 到发车时间差门限
                count_ad = 1
                dif += abs(t_to_mins(selfAT) - t_to_mins(objDT))
            elif selfDT != -1 and objAT != -1 and abs(t_to_mins(selfDT) - t_to_mins(objAT)) <= maxT:  # 到发车时间差门限
                count_ad = 1
                dif += abs(t_to_mins(selfDT) - t_to_mins(objAT))
            else:
               #print('\033[1;35mTime difference is larger than %d \033[0m! '%difT)  
               return 100000
           
        if count_ad+count<commonN:
            return 10000
        
        return dif/(count+count_ad)

        
    def merge_with(self, train_obj, commonN=1,difT=0,maxT=25):
        """
        与另一列火车合并，主要是用速度进行限制
        commonN: 相同车站的个数
        difT: 相同车站间相差的时间
        speedL: 最高时速的限制
        """
        # 与另一个对象合并
        # 1. 首先，执行一次准备合并的操作，获得准备合并的数据
        #if self.trainNumber!=[] and train_obj.trainNumber!=[]: # 两者都是有列车号的，
        #    if not (set(self.trainNumber)&set(train_obj.trainNumber)): # 而二者的列车号不一致
        #        return None # 不能合并
        
        self.generate_aligntype()
        train_obj.generate_aligntype()       
        # 条件，至少有 commonN个相同的车站
        
        if not (len(set(self.stations) & set(train_obj.stations))>=commonN): 
            print('\033[1;33m Could not merge, the number of common stations is less than %d \033[0m!'%commonN)
            return None
        # 判断是否相隔一天，如果是，调整到同一天
        common_stations = list(set(self.stations) & set(train_obj.stations))
        name = common_stations[0] # 取一个车站就够判断的了
        t_self = (self.align_type[name+';a.'] if name+';a.' in self.align_type else self.align_type[name+';d.'])
        t_obj = (train_obj.align_type[name+';a.'] if name+';a.' in train_obj.align_type else train_obj.align_type[name+';d.'])
        
        if abs(t_to_mins(t_self+2400) - t_to_mins(t_obj))<60: # 试图调整到同一天
            for k in self.align_type:
                self.align_type[k] = self.align_type[k]+2400
        elif abs(t_to_mins(t_self) - t_to_mins(t_obj+2400))<60: # 试图调整到同一天
            for k in train_obj.align_type:
                train_obj.align_type[k] = train_obj.align_type[k]+2400 
        ##### 3月30日，加一个判断是否相隔一天的，结束  
        ##### 用basic_data 判断是否可以合并
        
        count = 0
        count_ad = 0
        for name in common_stations:
            selfAT = self.basic_data[name].get('arrive',-1)
            selfDT = self.basic_data[name].get('depart',-1)
            objAT = train_obj.basic_data[name].get('arrive',-1)
            objDT = train_obj.basic_data[name].get('depart',-1)  
            
            if selfAT!=-1 and objAT!=-1 and abs(t_to_mins(selfAT) - t_to_mins(objAT))<=difT:
                count += 1
            elif selfDT!=-1 and objDT!=-1 and abs(t_to_mins(selfDT) - t_to_mins(objDT))<=difT:
                count += 1   
            elif selfAT!=-1 and objDT!=-1 and (maxT>t_to_mins(objDT)-t_to_mins(selfAT)>=0):  # 到发车时间差门限
                count_ad = 1
            elif selfDT!=-1 and objAT!=-1 and (maxT>t_to_mins(selfDT)-t_to_mins(objAT)>=0):  # 到发车时间差门限
                count_ad = 1  # 时间是合理的，加1
            else:
               #print('\033[1;35mTime difference is larger than %d \033[0m! '%difT)  
               return None  
        if count+count_ad < commonN:
            print('\033[1;32mCould not merge, two unrelated trains!!\033[0m')
            return None  
                       
        # 3. 开始将一个合向另一个 self.meta['id']
        if len(set(self.stations))>len(set(train_obj.stations)):
        #if int(self.meta['id'])<int(train_obj.meta['id']): # 以id小的作为基准
            bench = self.align_type # 以短的向长的里边合并
            compare = train_obj.align_type
        else:
            bench = train_obj.align_type
            compare = self.align_type  
        for s in compare:
            if not s in bench: # bench中没有该车的信息，填进去
                bench[s] = compare[s]
            #elif abs(t_to_mins(bench[s]) - t_to_mins(compare[s]))>difT: # 有相同的车站，但是发车时间却相差巨大
            #    print('Unsafety merge, large time differences!!')
            #    return None
        # 排序
        ordered_t = sorted(bench.items(), key=lambda item:(item[1],item[0])) 
        ####再加一段，判断相邻的车站，相同的时间却名称不同的问题
        new_t = [ordered_t[0]]
        for i in range(1,len(ordered_t)):
            pre_t = new_t[-1][1]
            cur_t = ordered_t[i][1]
            if pre_t == cur_t: # 时刻相同，
                continue
            new_t.append(ordered_t[i])

        #self.merge_record.append(train_obj.trainID)      
        return new_t # 返回了一个合理的排序后的时刻表    

    def update_status(self, ordered_t, location_dict,train_obj,SPEED_LIMIT=300):
        # 以合并后的数据更新本对象内的内容
        # ordered_t 是 元组 类型 (车站，时间)
        # 不光是更新车站，而且也更新其他内容
        new = defaultdict(dict)
        # 1. 先初始化一次，时刻全设为-1
        for k in ordered_t:
            name = k[0].split(';')[0]
            new[name]['arrive'] = -1
            new[name]['depart'] = -1
        # 2. 装入时间数据
        for k in ordered_t:
            name = k[0].split(';')[0]           
            ad_sign = k[0].split(';')[1]
            t = k[1]
            if ad_sign == 'a.':
                new[name]['arrive'] = t #%2400
            elif ad_sign == 'd.':
                new[name]['depart'] = t #%2400
        # 3.判断数据的合理性
        last_t = 0
        for name in new: # 一定是升序的，而且发车时间不晚于到站时间
            if new[name]['depart']!=-1 and new[name]['arrive']>new[name]['depart']:
                print(new) ##################
                print('Error, unreasonable a/d time!')
                #self.merge_record.pop()  ##### 4月23日加
                return -2
            if new[name]['depart']!=-1 and new[name]['depart']<=last_t:
                print(new) ##################
                print('Error, unreasonable a/d time!')
                #self.merge_record.pop()
                return -2
            if new[name]['arrive']!=-1 and new[name]['arrive']<=last_t:
                print(new) ##################
                print('Error, unreasonable a/d time!')
                #self.merge_record.pop()
                return -2  
            last_t = max(new[name]['arrive'],new[name]['depart'])  
        # 用 速度判断合理性，不合理不合并
        ######## 2019年4月4日，加 用速度判断合理性，不合理不合并 ############## 
        basic_data = defaultdict(dict)   # 清空内容，重新填充
        for name in new:
            basic_data[name]['arrive'] = min(new[name]['arrive'] % 2400, new[name]['arrive'])
            basic_data[name]['depart'] = min(new[name]['depart'] % 2400, new[name]['depart'])
            if name not in location_dict:
                print('No location for station: ',name)
                #self.merge_record.pop()
                return -2
            station = location_dict[name]
            utc = station['UTC']
            basic_data[name]['UTC'] = utc   
        speeds = self.speed_check(basic_data,location_dict)
        if max([s[-1] for s in speeds]) > SPEED_LIMIT:  # 
            print("\033[1;32mSpeed check failed...\033[0m'",max([s[-1] for s in speeds]))
            #self.merge_record.pop()
            return -2
        ######## 结束， 2019年4月4日，加 用速度判断合理性，不合理不合并 ############## 
        ### 加上一些元数据
        self.merged.append(train_obj.meta)
        self.merged+=train_obj.merged  # 万一是已经合并了很多次
        self.refNumber = list(set(self.refNumber + train_obj.refNumber)-set([self.meta['tableNumber'],train_obj.meta['tableNumber']]))
        self.trainNumber = list(set(self.trainNumber + train_obj.trainNumber))
        
        refnumbers = [ref['tableNumber'] for ref in self.merged] # 得到 已经合并的表号
        for name in basic_data:
             # 车站的引用表号，    
            basic_data[name]['ref'] = []
            if name in self.basic_data and 'ref' in self.basic_data[name]:
                basic_data[name]['ref'] += self.basic_data[name]['ref']
            if name in train_obj.basic_data and 'ref' in train_obj.basic_data[name]:
                basic_data[name]['ref'] += train_obj.basic_data[name]['ref']
            # 应该去掉已经合并好的表号
            basic_data[name]['ref'] = set(basic_data[name]['ref'])-set([self.meta['tableNumber'],train_obj.meta['tableNumber']])-set(refnumbers)
            # 判断一下这个车站是从谁那复制过来的
            if name in self.basic_data and name in train_obj.basic_data: # 两者都有，保持不变
                #if 'table_number' in self.basic_data[name]:
                #    basic_data[name]['table_number'] = self.basic_data[name]['table_number']
                basic_data[name]['table_from'] = "both"
                continue # 两者都有，无需添加标记
            elif name in self.basic_data and name not in train_obj.basic_data:
                if 'table_from' in self.basic_data[name]:
                    basic_data[name]['table_from'] = self.basic_data[name]['table_from']
                else:
                    basic_data[name]['table_from'] = self.meta['tableNumber'] # 自带的
            elif name not in self.basic_data and name in train_obj.basic_data:
                basic_data[name]['table_from'] = train_obj.meta['tableNumber'] # 从别的地方来的               


        self.basic_data = defaultdict(dict)   # 清空内容，重新填充
        self.basic_data = basic_data
        #self.basic_data = new
        # 更新车站列表
        self.stations = list(self.basic_data.keys())
        self.generate_aligntype()
        self.sign_merge_train = True
        return 1 
    
    def update_when_failed(self,train_obj,commonN=2, difT=0):
        # 对于高度相似的列车，而合并却失败的情况，添加一个高度相似的标识
        ### 加上一些元数据
      
        if not (len(set(self.stations) & set(train_obj.stations))>=commonN): # 没有公共的车站
            return None
        count = 0

        common_stations = set(self.stations) & set(train_obj.stations)
        for name in common_stations:
            selfAT = self.basic_data[name].get('arrive',-1)
            selfDT = self.basic_data[name].get('depart',-1)
            objAT = train_obj.basic_data[name].get('arrive',-1)
            objDT = train_obj.basic_data[name].get('depart',-1)  
            
            if selfAT != -1 and objAT != -1:
                if not abs(t_to_mins(selfAT) - t_to_mins(objAT)) <= difT:
                    return None
                else:
                    count += 1
            elif selfDT != -1 and objDT != -1:
                if not abs(t_to_mins(selfDT) - t_to_mins(objDT)) <= difT:
                    return None
                else:
                    count += 1
           
        if count>=commonN:
            if train_obj.meta not in self.possible:
                self.possible.append(train_obj.meta)
            #self.possible = list(set(self.possible))
            
            if self.meta not in train_obj.possible:
                train_obj.possible.append(self.meta)
            #train_obj.possible = list(set(train_obj.possible))
            return 1
        
    
    def speed_check(self,basic_data,location_dict):
        # 读进来的basic_data中是utc时间,,输出列车的运行时速
        names = list(basic_data.keys())
        last_t = -1
        last_name = ''
        
        speeds = []
        for i in range(len(names)):
            s = names[i]
            #utc = basic_data[s]['UTC']
            # 在做一切处理之前已经将时间转化为统一的utc时间
            at = basic_data[s].get('arrive',-1) 
            dt = basic_data[s].get('depart',-1)
                    
            # 1. 取一个当前时间（首选是到站时间）
            if max(at,dt) == -1: # a/d time都为-1,有问题
                print('Error, a/d time all invalid.')
                print(at,dt)
                print(basic_data)
                return -1
            elif min(at,dt) == -1: # 该站只有一个有效时间
                cur_t = max(at,dt)                    
            elif min(at,dt) != -1: # 有两个有效时间，取到站时间
                cur_t = at

            speed = cal_speed(location_dict, last_name, s, last_t, cur_t)
            if speed:
                speeds.append([last_name,s,speed])
            if speed and (speed>270):
                print('speed:',speed,';',last_name,';',s,';',last_t,';',cur_t,';', self.meta['fileName'],';', self.meta['country'])              
            # 赋值给last_t，准备下一次合理性检查
            if min(at,dt) == -1: # 该站只有一个有效时间
                last_t = max(at,dt)                    
            elif min(at,dt) != -1: # 有两个有效时间，取发车站时间
                last_t = dt
            last_name = s 
       
        return speeds        

    def show(self,file=None):
        # 命令行中输出表格(或输出到文件)
        # 显示的是当地时间
        # 显示 self.basic_data
        table = PrettyTable(["station","arrival","departure"])
        for name in self.basic_data:
            if not self.basic_data[name]:
                print('No a/d time in ',name)
                continue            
            at = -1
            dt = -1
            if 'arrive' in self.basic_data[name] and self.basic_data[name]['arrive']!=-1:
                at = utc_to_local(self.basic_data[name]['arrive'],self.basic_data[name]['UTC'])
            if 'depart' in self.basic_data[name] and self.basic_data[name]['depart']!=-1:
                dt = utc_to_local(self.basic_data[name]['depart'],self.basic_data[name]['UTC'])
            
            table.add_row([name, at, dt])
            
        if file:
            f = open (file,'a')
            print(table,file = f)
            f.close()
        else:
            #print(self.trainType+self.trainNumber+':'+str(self.daySign)+'---merged:'+str(self.sign_merge_train))
            print(table)                    
    
##################################################################################
def replace_special(string):
    string = str(string)
    return string.replace('&','&amp;').replace('>','&gt;').replace('<',"&lt;").replace('"','&quot;').replace("'",'&apos;')
# ================================ 小的功能函数 ===========================
def t_to_mins(time):
    #将　小时:分钟　表示的时间转换为　分钟　的形式
    if time<0:
        time+=2400
    h = int(time/100)
    m = int(time%100)
    return h*60 + m 

def mins_to_t(mins):
    # 将 分钟 形式的时间转换为 小时：分钟 的形式
    h = int(mins/60)
    m = mins%60
    time = h*100+m
    if time>=2400:
        time-=2400
    return time

def local_to_utc(time,utc):
    # 将时间转化为utc时间
    if time==-1:
        return time # -1代表不可用，无需处理
    time-=100*utc
    if time<0:
        time+=2400
    return time

def utc_to_local(time,utc):
    # utc时间转本地时间
    if time==-1:
        return time # -1代表不可用，无需处理    
    time+=100*utc
    if time>2400:
        time-=2400
    return time

def cal_speed(location_dict, pre_name, cur_name, pre_t, cur_t):
    # t2在后， t1在前， 但不一定t1<t2,因为时区不同,隔天问题在此解决
    if pre_t==-1: # 前车时间无效
        return None
    # 校正隔天的问题
    if cur_t < pre_t:
        cur_t+=2400
    travel_t = t_to_mins(cur_t) - t_to_mins(pre_t)
        
    locations = location_dict
    if pre_name not in locations:
        #print(name1,"not in ",country)
        return None
    if cur_name not in locations:
        #print(name2,"not in ",country)
        return None
    
    dis = haversine((locations[pre_name]['lat'], locations[pre_name]['lon']), (locations[cur_name]['lat'], locations[cur_name]['lon']))
    speed = dis/(travel_t/60)
    return speed # km/h

###############################################################################
def convert_XML2CSV(file,dict_nameCountry=None):
    """将XML格式的欧铁时刻表数据转换为CSV文件
    file: XML格式的时刻表
    dict_nameCountry: 车站-国家的字典
    Train对象中basic_data是一列车的时刻信息
            .meta是页数，伪id
            .trainType, .trainNumber
    
    """
    tree = ET.parse(file)
    trains = tree.findall('train')
    temp = []
    for train in trains:
        t = Train()
        t.load_element(train)
        train_code = t.meta['id']
        
        train_type = t.trainType
        train_number = str(t.trainNumber[0]) if t.trainNumber else ''
        
        i = 0
        for s in t.basic_data:
            
            country=dict_nameCountry[s] if dict_nameCountry else ''
            
            at = t.basic_data[s].get('arrive','--')
            dt = t.basic_data[s].get('depart','--')
            if type(at)==int:
                at = str(at).zfill(4)[:2] +':'+ str(at).zfill(4)[2:]
            if type(dt)==int:
                dt = str(dt).zfill(4)[:2] +':'+ str(dt).zfill(4)[2:]
            utc = t.basic_data[s].get('UTC')
            stop_id = i
            i+=1
        
            temp.append([train_code, stop_id,s,at,dt,utc,train_type+train_number,country])
    
    df = pd.DataFrame(temp,columns=['train_code','stop_id','station_name','arrive_time','depart_time','time_zone','true_train_code','country'])
    return df
    #df.to_csv('Europe_Railway_Schedule.csv',index=False) 

