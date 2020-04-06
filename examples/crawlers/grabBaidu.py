"""
===从百度爬词条===
"""
from prettytable import PrettyTable
import requests
import json
import pandas as pd
import random
import sys
sys.path.append(r'E:/Gitlab/pythonsharedfunctions.git')
from lib_time import progress_bar
import lib_file
from lib_time import MeasureT
from bs4 import BeautifulSoup
import re
#from pyecharts import GeoLines,Style

userAgent = [
			"Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36",
			"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.36 Safari/535.7",
			"Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:16.0) Gecko/16.0 Firefox/16.0",
			"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/534.55.3 (KHTML, like Gecko) Version/5.1.3 Safari/534.53.10",
			"Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 2.0.50727; Media Center PC 6.0)",
			"Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 1.0.3705; .NET CLR 1.1.4322)",
			"Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1500.55 Safari/537.36",
			"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1309.0 Safari/537.17"
			"Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:2.0b13pre) Gecko/20110307 Firefox/4.0b13pre",
			"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0",
			"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11"
		]

def grab_BaiduItem(key):
    """ 爬取百度百科的词条
    """
    headers = {
    	"User-Agent": random.choice(userAgent),
    	"Content-Type": "application/json",# 声明文本类型为 json 格式
    	"referer": r"https://baike.baidu.com/item/%E6%B2%88%E9%98%B3%E5%8C%97%E7%AB%99" ## 沈阳北站
    	}
    url = 'https://baike.baidu.com/item/%s'%key
    r = requests.get(url, headers=headers, timeout=10)
    r.encoding = "utf-8"
    print('页面响应码状态:', r.status_code)
    	
    soup = BeautifulSoup(r.text, 'html.parser')
    
    line_names = [l.text.strip() for l in soup.find_all('dt', class_='basicInfo-item name')]
    line_values = [l.text.strip() for l in soup.find_all('dd', class_='basicInfo-item value')]

    dict_info = dict(zip(line_names, line_values))    
       
    return dict_info

ttt = MeasureT()     
path = 'E:/Code/需求与辐射模型/transfer/多车站'
files = lib_file.list_all_files(path)
names = [f.split('\\')[-1].split('.png')[0] for f in files]

dict_HSRLocs = lib_file.pickle_load('../需求与辐射模型/dict_HSRLocs.pkl')

dict_nameBaiduInfo = {}
for i,name in enumerate(list(dict_HSRLocs.keys())):
    info = grab_BaiduItem(name+'站')
    dict_nameBaiduInfo[name] = info
    if i%10==0:
        ttt.duration(str(i)+' processed')

lib_file.json_save(dict_nameBaiduInfo, '车站信息.json')