# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup

url = 'https://jd.gzhu.edu.cn/info/1096/2426.htm'
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
r.encoding = 'utf-8'
soup = BeautifulSoup(r.text, 'lxml')

with open('debug_output.txt', 'w', encoding='utf-8') as f:
    f.write('=== TITLE ===\n')
    if soup.title:
        f.write(soup.title.get_text() + '\n\n')
    else:
        f.write('无title\n\n')
    
    f.write('=== H标签 ===\n')
    for tag in ['h1','h2','h3','h4']:
        for el in soup.find_all(tag):
            txt = el.get_text().strip()[:300]
            if txt:
                f.write(f'{tag}: {txt}\n')
    
    f.write('\n=== 页面顶部800字符 ===\n')
    text = soup.get_text()
    f.write(text[:800])
    
    f.write('\n\n=== 所有class为content/info的div ===\n')
    for cls in ['content', 'info', 'article', 'main']:
        for div in soup.find_all('div', class_=cls):
            f.write(f'div.{cls}: {div.get_text().strip()[:200]}\n')

print('已保存到 debug_output.txt')