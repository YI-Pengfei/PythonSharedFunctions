"""
===从携程爬航班数据===
    0. 基础数据： 城市名与电码的映射 在 list_cities.py中
    1. 从网站 https://flights.ctrip.com/schedule/bjs..html  (bjs代表北京) 爬取 从北京出发 或 到达北京 的城市
    2. 输入起终点城市，获取航班信息
"""
from prettytable import PrettyTable
import requests
import json
import pandas as pd
import random
import sys
sys.path.append(r'E:/Gitlab/pythonsharedfunctions.git')
from lib_time import progress_bar
from list_cities import dict_cities
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

def grab_connectedCities(cityName):
    """ 给定城市名， 爬取 到达+出发 城市的名称
    """
    headers = {
    	"User-Agent": random.choice(userAgent),
    	"Content-Type": "application/json",# 声明文本类型为 json 格式
    	"referer": r"https://flights.ctrip.com/itinerary/oneway/hak-khn?date=2018-11-11"
    	}
    url = 'https://flights.ctrip.com/schedule/%s..html'%dict_cities[cityName]
    r = requests.get(url, headers=headers, timeout=10)
    print('页面响应码状态:', r.status_code)
    	
    soup = BeautifulSoup(r.text, 'html.parser')
    line_titles = soup.find_all('div', class_='m')
    
    pattern=re.compile(r'[\u4e00-\u9fa5]+') #匹配汉字方式
    out=[]
    for line in line_titles:
        out+=pattern.findall(str(line))    
    
    return list(set(out) - set(cityName))
        

def grab_flight(acity, dcity, df):
    date = '20190924'
    date = date[0:4]+'-'+date[4:6]+'-'+date[6:8]
    	
    headers = {
    	"User-Agent": random.choice(userAgent),
    	"Content-Type": "application/json",# 声明文本类型为 json 格式
    	"referer": r"https://flights.ctrip.com/itinerary/oneway/hak-khn?date=2018-11-11"
    	}
        
    url = 'http://flights.ctrip.com/itinerary/api/12808/products'
    request_payload = {"flightWay":"Oneway",
    		"classType":"ALL",
    		"hasChild":'false',
    		"hasBaby":'false',
    		"searchIndex":1,
    		"airportParams":[{"dcity":dict_cities.get(dcity),"acity":dict_cities.get(acity),"dcityname":dcity,"acityname":acity,"date":date}]}
    # 这里传进去的参数必须为 json 格式
    response = requests.post(url,data=json.dumps(request_payload),headers=headers).text
    routeList = json.loads(response).get('data').get('routeList')
    
    index = df.shape[0]
    if not routeList:
        return -1
    jj = 0
    for route in routeList:
        if len(route.get('legs')) == 1:  ### ==1 的是直达    ==2 的是中转
            #info = {}
            legs = route.get('legs')[0]
            flight = legs.get('flight')
            
            df.loc[index,'flightNumber'] = flight.get('flightNumber') # 航班号
            #df.loc[index,'airlineCode'] = flight.get('airlineCode')
            #df.loc[index,'airlineName'] = flight.get('airlineName')
            ### 出发机场的信息
            df.loc[index,'departureCityName'] = flight.get('departureAirportInfo')['cityName']
            df.loc[index,'departureCityTlc'] = flight.get('departureAirportInfo')['cityTlc']
            df.loc[index,'departureAirportName'] = flight.get('departureAirportInfo')['airportName']
            df.loc[index,'departureAirportTlc'] = flight.get('departureAirportInfo')['airportTlc']
            ### 到达机场的信息
            df.loc[index,'arrivalCityName'] = flight.get('arrivalAirportInfo')['cityName']
            df.loc[index,'arrivalCityTlc'] = flight.get('arrivalAirportInfo')['cityTlc']
            df.loc[index,'arrivalAirportName'] = flight.get('arrivalAirportInfo')['airportName']
            df.loc[index,'arrivalAirportTlc'] = flight.get('arrivalAirportInfo')['airportTlc']            
            ### 时间信息
            df.loc[index,'departureDate'] = flight.get('departureDate')[-8:-3]
            df.loc[index,'arrivalDate'] = flight.get('arrivalDate')[-8:-3]
            ### 票价信息
            df.loc[index,'punctualityRate'] = flight.get('punctualityRate')
            df.loc[index,'lowestPrice'] = legs.get('characteristic').get('lowestPrice')
            ### 飞行器信息
            df.loc[index,'craftKind'] = flight.get('craftKind')
            df.loc[index,'craftTypeCode'] = flight.get('craftTypeCode')
            df.loc[index,'craftTypeName'] = flight.get('craftTypeName')
            df.loc[index,'craftTypeKindDisplayName'] = flight.get('craftTypeKindDisplayName')
            jj+=1
            index+=1
    #print(df)
    return jj

#list_pairs = []
#for name in dict_cities:
#    out = grab_connectedCities(name)
#    pairs = list(zip([name]*len(out),out)) + list(zip(out,[name]*len(out)))
#    list_pairs+=pairs
#
#set_pairs = set(list_pairs)
#list_pairs = list(set_pairs)
#df = pd.DataFrame(list_pairs, columns=['fromCity','toCity'])
#df.to_csv('airCityPairs.csv')


df_cityPairs = pd.read_csv('airCityPairs.csv')

df = pd.DataFrame(columns=['flightNumber','departureCityName','arrivalCityName',
                           'departureDate','arrivalDate',
                           'departureAirportName','departureCityTlc','departureAirportTlc',
                           'arrivalAirportName','arrivalCityTlc','arrivalAirportTlc',
                           'craftKind', 'craftTypeCode', 'craftTypeName','craftTypeKindDisplayName',
                                           'punctualityRate','lowestPrice']) 

k=0
for acity, dcity in zip(df_cityPairs.fromCity, df_cityPairs.toCity):
    print(k, df_cityPairs.shape[0] , df.shape[0])
    if acity==dcity:
        continue
    n_results = grab_flight(acity,dcity,df)
    print(acity, dcity, n_results)
    k+=1
    #progress_bar(k,len(city.items())**2)
    
df.to_csv('China_Air_Schedule.csv.gz',compression='gzip',encoding='gbk')