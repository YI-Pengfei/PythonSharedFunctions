#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 11 14:55:44 2020

@author: pengfei
"""
import numpy as np
import math

def compute_reverse_DF(samples,bins=50):
    """ 计算反 频率分布函数
    """
    max_x = round(np.log10(max(samples)))
    min_x = int(np.log10(min(samples)))
    xs=np.logspace(min_x,max_x,bins)  ## x轴， 起始 10^0, 末尾， 10^7, 共八个数
    count = [0]*len(xs)
    ratio = xs[1]/xs[0]  ### 等比数列
    
    for s in samples:
        for i in range(len(xs)):
            if 1<=s/xs[i]<ratio:
                count[i]+=1/len(samples)
#    return xs,count  

    start = 0
    end = len(count)
    for i in range(len(count)):
        if count[i]!=0:
            start=i
            break
    for i in range(len(count)-1,0,-1):
        if count[i]!=0:
            end=i
            break   
    return xs[start:end+1], count[start:end+1]

def compute_reverse_CDF(samples,bins=50):
    """ 计算 反累积频率分布函数
    """
    cumulative_freqs = []
    xs, freqs = compute_reverse_DF(samples,bins=bins)
    for i in range(len(freqs)):
        cumulative_freqs.append(sum(freqs[i:]))
    return xs, cumulative_freqs

n = 101
  
x = np.linspace(0,10,n)
noise = np.random.randn(n)
y = 2.5 * x + 0.8 + 2.0 * noise
  
def self_func(x,y,steps=100, alpha=0.01):
    """最小二乘拟合"""
    w = 1
    b = 1
    alpha = 0.01
    for i in range(steps):
    #    y_hat = w*x + b
        y_hat = b/(x**w)  ###写拟合曲线的标准公式
        dy = 2.0*(y_hat - y)
        dw = dy*x
        db = dy
        w = w - alpha*np.sum(dw)/n
        b = b - alpha*np.sum(db)/n
        e = np.sum((y_hat-y)**2)/n
    #print (i,'W=',w,'\tb=',b,'\te=',e)
    print ('self_func:\tW =',w,'\n\tb =',b)
    #  plt.scatter(x,y)
    #  plt.plot(np.arange(0,10,1), w*np.arange(0,10,1) + b, color = 'r', marker = 'o', label = 'self_func(steps='+str(steps)+', alpha='+str(alpha)+')')
    return b,w
  



## 双对数画图
#xs, ys = compute_reverse_CDF(list_pop)
#
#plt.loglog(xs, ys,'.')
#plt.xlabel('Population size ($p*$)')
#plt.ylabel('Cumulative frequency ($P(p>p*)$)')
