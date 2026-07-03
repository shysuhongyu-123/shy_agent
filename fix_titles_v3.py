# -*- coding: utf-8 -*-
"""
最终版title修复 v3
基于实际页面结构分析：
1. 面包屑导航中有分类（如"教授（正高）"）
2. 正文第一行有"博士、教授、博士生导师"
3. 第一个p标签有"博士、教授、博士生导师"
"""
import json
import os
import re
import sys
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEACHERS_JSON = os.path.join(BASE_DIR, "app", "gzhu_teachers.json")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# 所有职称关键词
ALL_TITLES = [
    '教授', '副教授', '讲师', '助教',
    '博士生导师', '博士导师',
    '硕士生导师', '硕士导师',
    '研究员', '副研究员', '助理研究员',
    '高级工程师', '工程师', '助理工程师',
    '高级实验师', '实验师', '助理实验师',
    '教授级高级工程师',
    '院长', '副院长',
    '主任', '副主任',
    '书记', '副书记',
    '处长', '副处长',
    '校长', '副校长',
]

# 需要排除的冗余关键词
EXCLUDE_KEYWORDS = ['博导', '硕导']


def fetch_teacher_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            r.encoding = 'utf-8'
            return r.text
    except Exception as e:
        print(f"  请求失败: {e}")
    return None


def extract_titles(html):
    """
    从页面中提取职称，基于实际页面结构
    """
    soup = BeautifulSoup(html, 'lxml')
    found_titles = []
    
    # 策略1: 从面包屑导航提取（如"教授（正高）"）
    # 面包屑通常在页面顶部，包含"首页 > 师资队伍 > ... > 教授（正高）"
    breadcrumb_text = ''
    for div in soup.find_all('div', class_=lambda x: x and ('position' in ' '.join(x) if x else False)):
        breadcrumb_text = div.get_text()
    # 也检查所有a标签中的分类信息
    all_links = [a.get_text().strip() for a in soup.find_all('a')]
    for link in all_links:
        for t in ALL_TITLES:
            if t in link and t not in found_titles:
                found_titles.append(t)
    
    # 策略2: 从正文区域第一行提取
    content_div = soup.find('div', class_='v_news_content')
    if content_div:
        content_text = content_div.get_text().strip()
        # 第一行通常是 "张春良博士、教授、博士生导师"
        first_line = content_text.split('\n')[0] if '\n' in content_text else content_text[:200]
        for t in ALL_TITLES:
            if t in first_line and t not in found_titles:
                found_titles.append(t)
    
    # 策略3: 从第一个p标签提取
    first_p = soup.find('p')
    if first_p:
        p_text = first_p.get_text().strip()
        for t in ALL_TITLES:
            if t in p_text and t not in found_titles:
                found_titles.append(t)
    
    # 策略4: 从页面标题提取
    if soup.title:
        title_text = soup.title.get_text()
        for t in ALL_TITLES:
            if t in title_text and t not in found_titles:
                found_titles.append(t)
    
    # 排除冗余关键词
    for kw in EXCLUDE_KEYWORDS:
        while kw in found_titles:
            found_titles.remove(kw)
    
    # 排序
    sorted_titles = sorted(found_titles, key=lambda x: ALL_TITLES.index(x) if x in ALL_TITLES else 999)
    
    return sorted_titles


def extract_supervisor_type(titles):
    if '博士生导师' in titles or '博士导师' in titles:
        return '博士生导师'
    elif '硕士生导师' in titles or '硕士导师' in titles:
        return '硕士生导师'
    else:
        return '本科生导师'


def main():
    with open(TEACHERS_JSON, 'r', encoding='utf-8') as f:
        teachers = json.load(f)
    
    print(f"导师总数: {len(teachers)}")
    
    fixed_count = 0
    error_count = 0
    
    for i, teacher in enumerate(teachers):
        name = teacher['name']
        url = teacher.get('homepage', '')
        old_titles = teacher.get('title', [])
        
        print(f"\n[{i+1}/{len(teachers)}] {name}")
        print(f"  旧title: {old_titles}")
        
        if not url:
            print("  无主页URL，跳过")
            continue
        
        html = fetch_teacher_page(url)
        if not html:
            print("  爬取失败，跳过")
            error_count += 1
            continue
        
        new_titles = extract_titles(html)
        print(f"  新title: {new_titles}")
        
        if new_titles:
            teacher['title'] = new_titles
            teacher['supervisor_type'] = extract_supervisor_type(new_titles)
            if old_titles != new_titles:
                fixed_count += 1
                print(f"  [已更新]")
        else:
            print(f"  [未找到，保留原值]")
    
    print(f"\n\n===== 统计 =====")
    print(f"更新数量: {fixed_count}")
    print(f"失败数量: {error_count}")
    
    with open(TEACHERS_JSON, 'w', encoding='utf-8') as f:
        json.dump(teachers, f, ensure_ascii=False, indent=4)
    print(f"已保存到 {TEACHERS_JSON}")


if __name__ == '__main__':
    main()