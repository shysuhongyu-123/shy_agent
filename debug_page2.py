# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup

url = 'https://jd.gzhu.edu.cn/info/1096/2426.htm'
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
r.encoding = 'utf-8'
soup = BeautifulSoup(r.text, 'lxml')

with open('debug_output2.txt', 'w', encoding='utf-8') as f:
    # 面包屑导航
    f.write('=== 面包屑/位置导航 ===\n')
    for div in soup.find_all('div', class_=lambda x: x and 'position' in x.lower()):
        f.write(div.get_text().strip() + '\n')
    for div in soup.find_all('div', class_=lambda x: x and 'bread' in x.lower()):
        f.write(div.get_text().strip() + '\n')
    for span in soup.find_all('span', class_=lambda x: x and 'position' in x.lower()):
        f.write(span.get_text().strip() + '\n')
    
    # 所有链接文本
    f.write('\n=== 所有a标签文本 ===\n')
    for a in soup.find_all('a'):
        txt = a.get_text().strip()
        if txt and len(txt) < 50:
            f.write(txt + '\n')
    
    # 正文区域
    f.write('\n=== 正文区域 ===\n')
    for div in soup.find_all('div', class_=lambda x: x and ('content' in x.lower() or 'article' in x.lower() or 'text' in x.lower() or 'main' in x.lower())):
        f.write(f'class={div.get("class")}: {div.get_text().strip()[:500]}\n\n')
    
    # 所有p标签
    f.write('\n=== 所有p标签 ===\n')
    for p in soup.find_all('p'):
        txt = p.get_text().strip()[:200]
        if txt:
            f.write(txt + '\n')

print('done')