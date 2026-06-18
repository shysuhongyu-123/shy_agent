import sys
sys.path.insert(0, '.')
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.retriever import recommend_teachers, load_teachers

# 测试 sensing 标签
profile = {'interest': {'sensing': {'composite_score': 1.0}}, 'goal': {}, 'history': []}
result = recommend_teachers(profile, top_n=30)
print(f'sensing:1.0 匹配导师数: {len(result)}')
for t in result[:5]:
    print(f'  {t["name"]}: {t["score"]}')

# 测试 ai 标签
profile2 = {'interest': {'ai': {'composite_score': 1.0}}, 'goal': {}, 'history': []}
result2 = recommend_teachers(profile2, top_n=30)
print(f'ai:1.0 匹配导师数: {len(result2)}')
for t in result2[:5]:
    print(f'  {t["name"]}: {t["score"]}')

# 测试 control 标签
profile3 = {'interest': {'control': {'composite_score': 1.0}}, 'goal': {}, 'history': []}
result3 = recommend_teachers(profile3, top_n=30)
print(f'control:1.0 匹配导师数: {len(result3)}')
for t in result3[:5]:
    print(f'  {t["name"]}: {t["score"]}')