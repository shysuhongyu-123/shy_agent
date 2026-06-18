"""
全面测试 recommend_node 的各种情况
"""
import sys
import os
sys.path.insert(0, '.')

# 解决 Windows 编码问题
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.retriever import recommend_teachers, load_teachers
from app.profile_db import load_profile, save_profile, delete_profile

# 先清理测试数据
delete_profile("test_user")

print("=" * 60)
print("测试1: 空画像（用户还没输入任何信息）")
print("=" * 60)
profile = {"interest": {}, "goal": {}, "history": []}
result = recommend_teachers(profile, top_n=30)
print(f"  匹配导师数: {len(result)}")
assert len(result) == 0, "空画像应该匹配到0个导师"
print("  ✅ 通过")

print()
print("=" * 60)
print("测试2: 只有兴趣 - ai: 1.0")
print("=" * 60)
profile = {"interest": {"ai": {"composite_score": 1.0}}, "goal": {}, "history": []}
result = recommend_teachers(profile, top_n=30)
print(f"  匹配导师数: {len(result)}")
assert len(result) > 0, "ai:1.0 应该匹配到导师"
print(f"  前3个导师:")
for t in result[:3]:
    print(f"    {t['name']}: {t['score']}")
print("  ✅ 通过")

print()
print("=" * 60)
print("测试3: 只有兴趣 - robotics: 1.0")
print("=" * 60)
profile = {"interest": {"robotics": {"composite_score": 1.0}}, "goal": {}, "history": []}
result = recommend_teachers(profile, top_n=30)
print(f"  匹配导师数: {len(result)}")
assert len(result) > 0, "robotics:1.0 应该匹配到导师"
print(f"  前3个导师:")
for t in result[:3]:
    print(f"    {t['name']}: {t['score']}")
print("  ✅ 通过")

print()
print("=" * 60)
print("测试4: 兴趣+目标 - ai: 1.0 + master: 1.0")
print("=" * 60)
profile = {
    "interest": {"ai": {"composite_score": 1.0}},
    "goal": {"master": {"composite_score": 1.0}},
    "history": []
}
result = recommend_teachers(profile, top_n=30)
print(f"  匹配导师数: {len(result)}")
assert len(result) > 0, "ai:1.0 + master:1.0 应该匹配到导师"
print(f"  前3个导师:")
for t in result[:3]:
    print(f"    {t['name']}: {t['score']}")
print("  ✅ 通过")

print()
print("=" * 60)
print("测试5: 多个兴趣 - ai: 1.0 + robotics: 1.0")
print("=" * 60)
profile = {
    "interest": {
        "ai": {"composite_score": 1.0},
        "robotics": {"composite_score": 1.0}
    },
    "goal": {},
    "history": []
}
result = recommend_teachers(profile, top_n=30)
print(f"  匹配导师数: {len(result)}")
assert len(result) > 0, "ai+robotics 应该匹配到导师"
print(f"  前3个导师:")
for t in result[:3]:
    print(f"    {t['name']}: {t['score']}")
print("  ✅ 通过")

print()
print("=" * 60)
print("测试6: 换一批 - 确保 offset 循环正确")
print("=" * 60)
profile = {
    "interest": {"ai": {"composite_score": 1.0}},
    "goal": {},
    "history": []
}
all_scored = recommend_teachers(profile, top_n=30)
print(f"  总匹配导师数: {len(all_scored)}")

# 模拟换一批
for batch in range(5):
    offset = batch * 6
    if offset >= len(all_scored):
        offset = 0
    teachers = all_scored[offset:offset + 6]
    if len(teachers) < 6:
        remaining = 6 - len(teachers)
        for t in all_scored[:remaining]:
            if t not in teachers:
                teachers.append(t)
        offset = 0
    print(f"  第{batch+1}批: {len(teachers)}个导师, offset={offset}")
    assert len(teachers) == 6, f"每批应该返回6个导师, 实际{len(teachers)}"
    # 检查是否有重复
    names = [t['name'] for t in teachers]
    assert len(names) == len(set(names)), f"第{batch+1}批有重复导师!"
print("  ✅ 通过")

print()
print("=" * 60)
print("测试7: 低匹配度兴趣 - 确保不报错")
print("=" * 60)
profile = {
    "interest": {"micro_nano": {"composite_score": 0.1}},
    "goal": {},
    "history": []
}
result = recommend_teachers(profile, top_n=30)
print(f"  匹配导师数: {len(result)}")
# 即使匹配不到也不应该报错
print("  ✅ 通过")

print()
print("=" * 60)
print("测试8: 负权重兴趣 - 确保不报错")
print("=" * 60)
profile = {
    "interest": {"ai": {"composite_score": -0.5}},
    "goal": {},
    "history": []
}
result = recommend_teachers(profile, top_n=30)
print(f"  匹配导师数: {len(result)}")
# 负权重应该匹配不到导师
assert len(result) == 0, "负权重应该匹配不到导师"
print("  ✅ 通过")

print()
print("=" * 60)
print("测试9: 数据库读写 - 保存后读取")
print("=" * 60)
test_profile = {
    "interest": {"ai": {"composite_score": 1.0, "score": 1.0, "count": 1, "positive_count": 1, "negative_count": 0, "last_update": "2026-06-18"}},
    "goal": {"master": {"composite_score": 1.0, "score": 1.0, "count": 1, "positive_count": 1, "negative_count": 0, "last_update": "2026-06-18"}},
    "history": []
}
save_profile("test_user", test_profile)
loaded = load_profile("test_user")
print(f"  兴趣: {list(loaded['interest'].keys())}")
print(f"  目标: {list(loaded['goal'].keys())}")
assert "ai" in loaded["interest"], "ai 应该被保存"
assert "master" in loaded["goal"], "master 应该被保存"
print("  ✅ 通过")

# 清理
delete_profile("test_user")

print()
print("=" * 60)
print("所有测试通过! 🎉")
print("=" * 60)