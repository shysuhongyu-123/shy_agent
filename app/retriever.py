import json
import os
from typing import List, Dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEACHERS_JSON = os.path.join(BASE_DIR, "gzhu_teachers.json")

# ============================================================
# 关键词映射表（基于广州大学机械与电气工程学院实际研究方向）
# 每个画像标签映射到导师数据中可能出现的中文关键词
# ============================================================
KEYWORD_MAP = {
    # === 机器人 ===
    "robotics": [
        "机器人", "机器人技术", "机器人学", "机器人控制", "机器人装备",
        "仿生机器人", "外骨骼机器人", "协作机器人", "移动机器人", "微型机器人",
        "软体机器人", "微机器人", "磁控微机器人", "模块化机器人", "装车机器人",
        "轮足机器人", "水下机器人", "康复机器人", "工业机器人",
        "机器人机构学", "机器人感知", "机器人规划", "机器人建模",
        "微机器人驱动", "反无人机"
    ],
    # === 机械控制 ===
    "control": [
        "控制", "机械控制", "运动控制", "智能控制", "自动控制", "控制理论",
        "控制优化", "协同控制", "容错控制", "鲁棒控制", "滑模控制",
        "自适应控制", "学习控制", "网络控制", "分布式控制", "模糊控制",
        "非线性控制", "电机控制", "振动控制", "电子控制",
        "智能执行与控制", "汽车运动控制", "自适应鲁棒控制",
        "机电一体化", "机械系统动力学控制"
    ],
    # === 人工智能 ===
    "ai": [
        "人工智能", "机器学习", "深度学习", "强化学习", "神经网络",
        "智能算法", "群智能", "计算智能", "多目标优化", "进化算法",
        "大模型", "物理信息神经网络", "智能计算", "演化博弈",
        "新一代人工智能", "元学习", "智能无人系统"
    ],
    # === 计算机视觉 ===
    "vision": [
        "机器视觉", "计算机视觉", "视觉检测", "图像处理", "图像识别",
        "计算机图像识别", "视觉感知", "数字图像处理", "场景语义理解",
        "图像补全", "去噪", "视觉"
    ],
    # === 嵌入式 ===
    "embedded": [
        "嵌入式", "单片机", "ARM", "STM32", "嵌入式系统",
        "单片机技术", "PLC", "可编程控制器", "FPGA",
        "嵌入式技术", "微机原理"
    ],
    # === 智能制造 ===
    "smart_manufacturing": [
        "智能制造", "数字孪生", "数字化", "智能运维", "高端装备",
        "先进制造", "智能制造系统", "数字化建模", "仿真优化",
        "数字孪生车间", "智能制造综合实训", "机械自动化",
        "先进制造技术", "数控技术", "数控", "CAM", "CAD/CAM",
        "计算机辅助设计", "计算机仿真"
    ],
    # === 故障诊断 ===
    "fault_diagnosis": [
        "故障诊断", "状态监测", "无损检测", "健康管理", "智能运维",
        "设备故障诊断", "机械故障诊断", "结构健康监测", "剩余寿命预测",
        "机械动态建模", "信号处理", "盲信号分离", "超声无损检测",
        "设备状态监测", "故障诊断技术"
    ],
    # === 机械设计 ===
    "mechanical_design": [
        "机械设计", "结构设计", "结构优化", "拓扑优化", "机构学",
        "机械机构", "疲劳分析", "可靠性设计", "优化设计",
        "多尺度结构", "结构拓扑优化", "先进结构", "机械系统",
        "机械设计基础", "机械原理", "机械零件设计",
        "近似模型", "设计优化", "结构设计优化"
    ],
    # === 微纳制造 ===
    "micro_nano": [
        "微纳", "微纳制造", "微纳器件", "微纳机构", "精密制造",
        "微结构", "微流控", "微机电", "MEMS", "精密加工",
        "微结构精密制造", "微纳机电器件", "微流控传感器",
        "功能微结构制造", "纳米功能材料", "微纳粘着"
    ],
    # === 车辆工程 ===
    "vehicle": [
        "汽车", "车辆", "新能源汽车", "电动汽车", "汽车电子",
        "汽车制造", "汽车构造", "汽车电器", "汽车检测",
        "清洁燃料汽车", "混合动力", "动力电池", "发动机",
        "交通电气化", "汽车运动控制", "汽车市场营销"
    ],
    # === 材料工程 ===
    "materials": [
        "材料", "金属材料", "复合材料", "纳米材料", "功能材料",
        "表面工程", "摩擦学", "材料加工", "金属加工",
        "金属增材制造", "激光加工", "激光原位合成",
        "高分子", "橡胶", "磁性材料", "智能材料",
        "金属腐蚀", "金属流变学", "材料成形",
        "工程材料", "机械表面技术", "工程摩擦学"
    ],
    # === 力学 ===
    "mechanics": [
        "力学", "动力学", "运动学", "工程力学", "理论力学",
        "材料力学", "结构力学", "弹性力学", "振动",
        "机械振动", "非线性动力学", "流固耦合",
        "界面摩擦力学", "机械动力学", "高等工程力学"
    ],
    # === 传感检测 ===
    "sensing": [
        "传感器", "检测技术", "测试技术", "传感技术", "智能传感",
        "先进传感", "传感检测", "无损检测技术", "信号处理",
        "生物传感", "柔性传感器", "角位移传感", "测量仪器",
        "虚拟仪器", "LabVIEW", "水质监测"
    ],
    # === 电力电子 ===
    "power_electronics": [
        "电力电子", "电机", "电机控制", "电机驱动", "电力传动",
        "电能变换", "新能源", "电池管理", "电池状态估计",
        "能源管理", "电机本体设计", "电力电子电路",
        "运动控制系统", "高电压", "绝缘技术",
        "电力系统", "继电保护", "配网", "虚拟电厂"
    ],
    # === 智能电网 ===
    "smart_grid": [
        "智能电网", "电网", "电力系统", "能源系统", "综合能源",
        "需求响应", "优化调度", "源网荷储", "电力市场",
        "电力系统调度", "电气工程仿真"
    ],
    # === 物联网 ===
    "iot": [
        "物联网", "IoT", "嵌入式", "无线传感", "信息物理系统",
        "网络安全", "物联网技术", "物联网应用", "低空智联网",
        "水下物联网"
    ],
    # === 增材制造 ===
    "additive_manufacturing": [
        "增材制造", "3D打印", "金属增材制造", "激光增材",
        "增材制造装备", "3D打印技术"
    ],
    # === 流体力学 ===
    "fluid_mechanics": [
        "流体力学", "流体", "流场", "多相流", "CFD",
        "计算流体力学", "液压传动", "流固耦合",
        "高分子流变学", "金属流变学", "颗粒传热"
    ],
    # === 精密驱动 ===
    "precision_drive": [
        "压电", "精密驱动", "压电驱动", "压电作动器",
        "压电雾化", "压电精研", "功率超声", "超声技术",
        "精密装备", "智能精密装备"
    ]
}


def load_teachers() -> List[Dict]:
    try:
        with open(TEACHERS_JSON, "r", encoding="utf-8") as f:
            teachers = json.load(f)
        print(f"导师数量: {len(teachers)}")
        if teachers:
            print(teachers[0])
        return teachers
    except Exception as e:
        print("加载导师数据失败:", e)
        return []


def calculate_teacher_score(teacher: Dict, user_profile: Dict) -> float:
    """
    修复：每个画像标签只计一次分，避免关键词重复加分。
    """
    score = 0
    text = " ".join(teacher.get("research", []) + teacher.get("courses", []))

    # 兴趣权重
    for profile_tag, info in user_profile.get("interest", {}).items():
        weight = info.get("composite_score", 0)
        keywords = KEYWORD_MAP.get(profile_tag, [])
        if any(kw in text for kw in keywords):
            score += weight

    # 目标权重
    for profile_tag, info in user_profile.get("goal", {}).items():
        weight = info.get("composite_score", 0)
        keywords = KEYWORD_MAP.get(profile_tag, [])
        if any(kw in text for kw in keywords):
            score += weight

    return round(score, 2)


def recommend_teachers(user_profile: Dict, top_n: int = 5) -> List[Dict]:
    teachers = load_teachers()
    if not teachers:
        return []

    scored_teachers = []
    for teacher in teachers:
        score = calculate_teacher_score(teacher, user_profile)
        if score > 0:
            teacher["score"] = score
            scored_teachers.append(teacher)

    scored_teachers.sort(key=lambda x: x["score"], reverse=True)
    return scored_teachers[:top_n]


def main():
    # 从 SQLite 数据库读取用户画像（默认 session）
    from app.profile_db import load_profile
    user_profile = load_profile("default")

    recommended = recommend_teachers(user_profile, top_n=5)
    print("\n推荐导师列表:")
    for i, t in enumerate(recommended, 1):
        print(f"{i}. {t['name']} - 匹配度 {t['score']}")
        print(f"   研究方向: {', '.join(t['research'])}")
        print(f"   邮箱: {t['email']}")
        print(f"   课程: {', '.join(t['courses'])}")
        print(f"   主页: {t['homepage']}\n")


if __name__ == "__main__":
    main()