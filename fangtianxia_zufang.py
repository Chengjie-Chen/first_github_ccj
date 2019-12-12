# -*- coding: utf-8 -*-
"""
Created on Fri Oct 18 14:47:45 2019

@author: Chengjie-Chen
"""

from selenium import webdriver
from selenium.webdriver.common.by import By 
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait 
from bs4 import BeautifulSoup
import requests
import csv
import pymysql
import re
import pandas as pd
import pyecharts 
from pyecharts import options as opts
import openpyxl 
import datetime as dt
import time

'''
写在前面的话---
代码想要改进的方向：
1、房天下租房房源排行网页翻页机制较复杂，暂时搞不懂；
2、借助运维工具操作浏览器可以实现翻页，但是爬取效率不高；
3、爬取失败风险的问题：现代码是先爬取所有目标网页的源码，后解析，最后再存储，中途若任何一步失败将前功尽弃；
4、可以爬取更多字段，最后做一些可视化分析等。

问题先放着，大神路过欢迎给予指点，python小菜鸟在此先谢过！
有空再钻研，后更……

'''


'''直接获取网页内容'''
def get_html_1():  
    header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36"}
    result_html=[]
    page=1
    try:
        while page<=10:
            url="https://gz.zu.fang.com/house/i3%s/?" % page
            url_data={'_rfss':'05','rfss':'2-c8922f820fbe083cb2-05'}
            print('第'+str(page)+'页链接为：'+url)
            html=requests.get(url,params=url_data,headers=header,timeout=30)#请求超时时间为30秒
            html.raise_for_status()#如果状态不是200，则引发异常
            html.encoding=html.apparent_encoding #配置编码
            #print(html.headers.items)
            Soup = BeautifulSoup(html.text,'lxml')
            data = Soup.find('div', {'class': 'houseList'}).find_all('dd', {'class': 'info rel'})
            result_html.extend(data)
            #print(result_html)
            page += 1
        return result_html
    except:
        print("产生异常")


browser = webdriver.Chrome() #启动浏览器
wait = WebDriverWait(browser, 10) 
result_html=[]

'''借助自动运维工具获取网页内容'''
def get_html(page): 
    try: 
        url ='https://gz.zu.fang.com/'
        browser.get(url) 
        i=1
        while i<=page:
            if i>1:
                next_page_button=browser.find_element_by_link_text ('下一页') 
                next_page_button.click()
                time.sleep(5)
            print('正在爬取第'+str(i)+'页（'+browser.current_url+')信息……')
            html=browser.page_source #获取当前网页源码
            #print(html)
            Soup = BeautifulSoup(html,'lxml')#解析网页源码
            #print(Soup)
            data = Soup.find('div', {'class': 'houseList'}).find_all('dd', {'class': 'info rel'})#提取网页源码有用部分
            #print(data)
            result_html.extend(data)
            print('爬取第'+str(i)+'页信息成功！累计信息总数：'+str(len(result_html))+'条')
            i += 1
        print('最终爬取信息总数：'+str(len(result_html))+'条')
        browser.close()
        return result_html
    except: 
        print('连接超时，重新开始爬取……')
        time.sleep(1)
        get_html(page)


'''解析页面内容，抽取有用信息'''
def get_info(data):
    #all_fang_info={}
    fieldnames=['楼盘排名', '楼盘区域','楼盘名称','楼盘评分','楼盘售价(元/平方米)','楼盘热度(评论数)','楼盘卖点']
    all_fang_info ={'标题':[], '地区':[],'街道':[],'小区名称':[],'租金(元/月)':[],'交通':[],'租房类型':[],'房型':[],'面积':[],'朝向':[],'房天下链接':[]}
    for fang_info in data:
            title=fang_info.find('p', {'class': 'title'}).find('a').get_text().replace(" ","-")
            link_info=fang_info.find('p', {'class': 'title'})
            link=re.findall(r'/chuzu/.+\.htm',str(link_info))
            #print(link)
            if link:
                all_fang_info['房天下链接'].append(link[0])
            else: 
                all_fang_info['房天下链接'].append('信息缺失')
            #all_fang_info['房天下链接'].append(link[0])
            #print(rank)
            all_fang_info['标题'].append(title)
            name_infos=fang_info.find('p', {'class': 'gray6 mt12'}).find_all('span')
            infos=[]
            for name_info in name_infos:
                info=name_info.get_text()
                infos.append(info)
            all_fang_info['地区'].append(infos[0])
            all_fang_info['街道'].append(infos[1])
            if len(infos)<3:
                all_fang_info['小区名称'].append('信息缺失')
            else: 
                all_fang_info['小区名称'].append(infos[2])
            #楼盘售价
            prices=fang_info.find('span', {'class': 'price'})
            if prices:
                price=float(prices.get_text())
            else:
                price='价格待定'
            #print(price)
            all_fang_info['租金(元/月)'].append(price)
            tranports=fang_info.find('span', {'class': 'note subInfor'})
            if tranports:
                tranport=tranports.get_text()
            else:
                tranport='信息缺失'
            all_fang_info['交通'].append(tranport)
            points=fang_info.find('p', {'class': 'font15 mt12 bold'}).get_text().replace("\r\n","").replace(" ","")
            #print(points.split('|'))
            all_fang_info['租房类型'].append((points.split('|'))[0])
            all_fang_info['房型'].append((points.split('|'))[1])
            #p = re.compile(r'\d+')
            mj=re.findall(r'\d+',(points.split('|'))[2])
            all_fang_info['面积'].append(float(mj[0]))
            if len(points.split('|'))<4:
                all_fang_info['朝向'].append('信息缺失')
            else:
                all_fang_info['朝向'].append((points.split('|'))[3])
    #print(all_fang_info)
    df=pd.DataFrame(all_fang_info)
    #print(df)
    return df

if __name__ == "__main__":
    
    tick=dt.datetime.now()
    all_fang = get_html(100)  # 返回网页内容列表
    df_fangs_zufang=get_info(all_fang)
    tock=dt.datetime.now()
    print('爬虫获取租房房源信息数据，用时：%s秒' % str((tock-tick).seconds))
    df_fangs_zufang.to_excel('./spider_learning/广州租房信息（房天下）_100页（全）.xlsx',columns=['标题','地区','街道','小区名称','租金(元/月)','交通','租房类型','房型','面积','朝向','房天下链接'],index=0)
    print('保存数据完成：'+str(dt.datetime.now()))
    '''
    #数据可视化
    bar = pyecharts.charts.Bar()
    bar.set_global_opts(title_opts=opts.TitleOpts(title="热度最高的广州新盘", subtitle="评论热度",pos_left='center',pos_top='top'),xaxis_opts=opts.AxisOpts(name_rotate=0,name="楼盘名称",axislabel_opts={"rotate":45,'fontSize':10}),datazoom_opts=opts.DataZoomOpts() ,legend_opts=opts.LegendOpts(pos_left='left'),toolbox_opts=opts.ToolboxOpts()) #把字体倾斜45度以显示全x轴
    bar.add_xaxis(list(df_fangs_gz['楼盘名称']))
    bar.add_yaxis('评论数',list(df_fangs_gz['楼盘热度(评论数)']))
    print(list(df_fangs_gz['楼盘热度(评论数)']))
    bar.render('./spider_learning/广州楼盘热度分析.html')
    '''
