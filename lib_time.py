# -*- coding: utf-8 -*-
"""
    2019.08.23 progress bar
"""
import sys
import time
from dateutil.parser import parse



class MeasureT:
    def __init__(self):
        self.start = time.time()
        self.end = None

#    def __enter__(self):
#        self.start = time.time()
#        return self
#
#    def __exit__(self, exc_type, exc_val, exc_tb):
#        self.end = time.time()
#        print("Total time taken: %s" % self.duration())

    def duration(self, string=""):
        self.end = time.time()
        print(string+". Total time taken: %2f s" %float(self.end-self.start))
        #return str((self.end - self.start) * 1000) + ' milliseconds'


def progress_bar(num, total):
    rate = float(num)/total
    ratenum = int(100*rate)
    r = '\r[{}{}]{}%'.format('*'*ratenum, ' '*(100-ratenum),ratenum)
    sys.stdout.write(r)
    sys.stdout.flush()
    
#i,n=0,100
#for i in range(n):
#    time.sleep(0.1)
#    progress_bar(i+1,n)
    

#### 计算列车运行时间时常用
def get_delta_t(t_start,t_end,day_sign=0,):
    """
    用来计算hh:mm的时间差
    :param t_start: "hh:mm"形式
    :param t_end: "hh:mm"形式
    :param day_sign: 是否隔天的标识
    :return: 以分钟为单位的时间差
    """
    a = parse('2018-01-01/%s:00'%t_start)
    b = parse('2018-01-%d/%s:00'%(1+day_sign,t_end))
    #(b-a).days
    #(b-a).seconds
    return (b-a).total_seconds()/60


def strT_to_floatT(t_str, unit='h'):
    """
    :param t_str:  "hh:mm"形式 或 "hhmm"形式
    :param unit:  'h' -- 以小时为单位， 'm'--以分钟为单位
    :return:  浮点数 xx.xx
    """
    t_str = t_str.replace(':','').zfill(4)
    if not t_str.isdigit():
        print(t_str)
        print('Error, invalid time format!')
        return None
        
    h, m = int(t_str[:2]), int(t_str[2:])
    if unit == 'h':
        return h + m/60
    elif unit == 'm':
        return h*60 + m
    else:
        print('Wrong unit!')
        return None


def floatT_to_strT(t_float, unit='h'):
    """
    :param t_float:  浮点数 xx.xx 小时.
    :param unit:  'h' -- 以小时为单位， 'm'--以分钟为单位
    :return:  hh:mm 形式
    """
    i = int(t_float)
    z = t_float - i
    if unit=='h':
        return str(i).zfill(2)+':'+str(round(z*60)).zfill(2)  # round是四舍五入取整
    elif unit == 'm':
        return '00:'+str(i).zfill(2)

### 2019.08.23
def get_deltaT(t0, t1, unit='min', mode='auto',delta_day=None):
    """计算时间差， 自动确定是否隔天，（这里不考虑隔两天的情况）
       t: string. Two formats are supported:  1) "hh:mm"
                                              2) "hhmm"
       unit: 单位    1) "min"  int类型  
                    2) "h"    float类型
                    3) "h:m"  string类型 
    
       mode:   1."auto" 自动确定是否隔天;  2. "manual" 手动指定相差的天数
    """
    if not (isinstance(t0,str) and isinstance(t1,str)):
        print('Inputs are not strings.')
        return -1
    
    t0 = int(t0.replace(':',''))
    t1 = int(t1.replace(':',''))
    if mode=='manual' and delta_day:  ### 手动指定了相差的天数
        t1 = int(t1) + delta_day*2400
    else:   ### 没有指定相差的天数，则 t1小于t0时就 自动加一天
        if t1 < t0: # 隔天
            t1 = int(t1) + 2400
    
    h0, m0 = int(t0/100), int(t0%100)
    h1, m1 = int(t1/100), int(t1%100)
    
    delta = (h1*60+m1) - (h0*60+m0)
    if unit=='min':
        return delta  # int
    elif unit=='h':
        return delta/60
    elif unit=='h:m':
        return str(int(delta/60)).zfill(2) + ':' + str(delta%60).zfill(2)