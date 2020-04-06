# -*- coding:utf-8 -*-
import requests,urllib
import re
import json
from bs4 import BeautifulSoup
import bs4
import os
from pyquery import PyQuery as pq
import pandas as pd

headers = {
    'Host': 'kyfw.12306.cn',
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
    'Accept': '*/*',
    'X-Requested-With': 'XMLHttpRequest',
    # 'If-Modified-Since': '0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    'Referer': 'https://kyfw.12306.cn/otn/leftTicket/init',
    'Accept-Encoding': 'gzip, deflate, sdch, br',
    'Accept-Language': 'zh-CN,zh;q=0.8'}


def grab(url):
    try:
        return requests.get(url, headers=headers, verify=False, timeout=15).text
    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
        #print(url)
        return url   # 超时之后返回原来的url
    
def grab_train_list():
    url = 'https://kyfw.12306.cn/otn/resources/js/query/train_list.js'
    r = grab(url)
    r = r.replace('var train_list =', '')
    data = json.loads(r)  # 包含31天
    print(data.keys())  
    selected_data = data['2019-07-01'] # C,D,G,K,O,T,Z
    list_out_data = []
    for tp in selected_data:  # 遍历种类
        if tp not in {'K'}:  #{'C','D','G','T','Z'}:
            continue
        for train in selected_data[tp]:
            train['station_train_code'] = train['station_train_code'].replace('(',' ').replace('-',' ').replace(')','')

            temp = {}
            temp['train_code'] = train['station_train_code'].split(' ')[0]
            temp['from_station'] = train['station_train_code'].split(' ')[1]
            temp['to_station'] = train['station_train_code'].split(' ')[2]
            temp['train_no'] = train['train_no'] 
            
            list_out_data.append(temp)
            
    #with open('train_list0701.json', 'w', encoding='utf-8') as fp:
    #    json.dump(list_out_data, fp, ensure_ascii=False, sort_keys=True, indent=2)  
    return list_out_data



#with open('train_list0701.json', 'r', encoding='utf-8') as tl:
#    list_Trains = json.load(tl)
list_Trains = grab_train_list()

list_out = []
list_failed = []
count=0
no_c=0
for train in list_Trains:
    count+=1
    train_code = train['train_code']
    url = 'http://www.jt2345.com/huoche/checi/%s.htm'%train_code
    #html = requests.get(url,headers = headers)
    try:
        response = urllib.request.urlopen(url)
    except urllib.request.HTTPError:
        print('No train %s'%train_code)
        no_c+=1
        list_failed.append(train_code)
        continue
    html = response.read()
    #Soup = BeautifulSoup(html.text, 'lxml')
    soup  = BeautifulSoup(html, 'html.parser',from_encoding="GBK")

    table = soup.find_all('table')[1]  # 有用的那组元素

    for i, child in enumerate(table): # 迭代p标签所有子孙节点
        if i>=3 and i%2==1:
            #print(i,child)   # 站次，车站，到达时间，开车时间，停留时间，里程
            #break
            if isinstance(child, bs4.element.Tag):
                row = []
                for p in child.find_all('td'):
                    row.append(p.string)
                    #print(p.string)
                if len(row)!=6:
                    pass
                    #print('Error')
                else:
                    row.insert(0,train_code)
                    #print(row)
                    list_out.append(row)
    if count%100==0:
        print(count,'have beeen processed.')
df = pd.DataFrame(list_out,columns=['train_code','stop_id','station_name','arrive_time','depart_time','stop_time','other'])
df.to_csv('China_Railway_Schedule_20190701K.csv',index=False)