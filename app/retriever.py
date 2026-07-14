import json
import os
from typing import List, Dict

from app.logger import logger
from app.cache import cache_teacher_scores, get_cached_teacher_scores

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

# ============================================================
# 课程-目标匹配规则
# 根据导师的课程名称，评估该课程对学生目标的帮助程度
# ============================================================
# 就业导向关键词：课程名称中包含这些词，说明对就业有帮助
EMPLOYMENT_KEYWORDS = [
    "应用", "技术", "工程", "设计", "制造", "实践", "实训",
    "编程", "开发", "系统", "自动化", "检测", "控制",
    "单片机", "PLC", "嵌入式", "CAD", "CAM", "SolidWorks",
    "LabVIEW", "MATLAB", "C语言", "Python", "电路", "电子",
    "驱动", "机器人", "数控", "仿真", "创新", "发明",
    "项目管理", "企业管理", "市场营销", "专业英语"
]

# 考研导向关键词
MASTER_KEYWORDS = [
    "高等", "理论", "原理", "力学", "数学", "矩阵论",
    "现代控制", "信号与系统", "数字信号", "复变函数",
    "计算方法", "运筹", "优化", "机器学习", "深度学习",
    "人工智能", "神经网络", "机器人学", "自动控制原理",
    "现代控制理论", "非线性控制", "智能控制"
]

# 读博/科研导向关键词
PHD_KEYWORDS = [
    "高等", "前沿", "研讨", "论文", "科研", "创新",
    "现代控制理论", "非线性控制", "智能控制", "机器学习",
    "深度学习", "神经网络", "机器人学", "信号处理",
    "数值计算", "计算方法", "矩阵论", "高等工程力学",
    "高等机构学", "故障诊断学", "专家系统", "系统工程",
    "多智能体", "协同控制", "网络安全", "信息物理"
]

# 竞赛导向关键词
COMPETITION_KEYWORDS = [
    "创新", "发明", "设计", "机器人", "单片机", "嵌入式",
    "编程", "C语言", "Python", "智能", "电子", "电路",
    "机械设计", "数控", "3D打印", "SolidWorks", "LabVIEW",
    "MATLAB", "竞赛", "实训", "实践"
]


def load_teachers() -> List[Dict]:
    try:
        with open(TEACHERS_JSON, "r", encoding="utf-8") as f:
            teachers = json.load(f)
        logger.info("导师数量: %d", len(teachers))
        return teachers
    except Exception as e:
        logger.error("加载导师数据失败: %s", str(e))
        return []


def calculate_course_goal_score(courses: List[str], goal_tag: str) -> float:
    """
    根据导师的课程信息，评估该导师的课程对学生特定目标的帮助程度。
    返回 0.0 ~ 1.0 的分数。
    """
    if not courses:
        return 0.0

    # 将所有课程合并为一段文本
    course_text = " ".join(courses)

    # 根据目标选择关键词列表
    if goal_tag == "employment":
        keywords = EMPLOYMENT_KEYWORDS
    elif goal_tag == "master":
        keywords = MASTER_KEYWORDS
    elif goal_tag == "phd":
        keywords = PHD_KEYWORDS
    elif goal_tag == "competition":
        keywords = COMPETITION_KEYWORDS
    elif goal_tag == "research":
        # 科研与读博类似
        keywords = PHD_KEYWORDS
    elif goal_tag == "entrepreneurship":
        # 创业：关注创新、管理、市场类课程
        keywords = ["创新", "发明", "管理", "市场", "创业", "项目", "设计", "产品"]
    else:
        return 0.0

    # 计算匹配的关键词数量
    matched_count = 0
    for kw in keywords:
        if kw in course_text:
            matched_count += 1

    # 归一化：匹配数 / 总关键词数，但上限为 1.0
    # 同时考虑课程数量：课程越多，说明该导师教学覆盖面广
    course_count_bonus = min(len(courses) / 10.0, 0.2)  # 最多加 0.2
    base_score = min(matched_count / max(len(keywords) * 0.3, 1), 1.0)

    return round(min(base_score + course_count_bonus, 1.0), 2)


# 全局 LLM 实例（延迟初始化，避免循环导入）
_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if api_key:
            _llm = ChatOpenAI(
                model="deepseek-chat",
                base_url="https://api.deepseek.com",
                api_key=api_key,
                temperature=0.3,
                max_tokens=512
            )
    return _llm


def calculate_teacher_score(teacher: Dict, user_profile: Dict) -> dict:
    """
    综合评分 = 研究方向匹配分 × 0.7 + 课程-目标匹配分 × 0.3

    纯算法匹配，不调用 LLM，避免 Render 超时。
    预定义标签用关键词匹配，自由文本标签用文本包含匹配。
    
    返回带匹配原因的 dict：
    {
        "score": float,
        "matched_interests": [{"tag": "机器人", "weight": 0.9, "keywords": ["机器人", "机器人控制"]}],
        "matched_goals": [{"tag": "考研", "weight": 0.8, "keywords": ["自动控制原理"]}],
        "research_match": float,  # 0~1 归一化
        "course_match": float     # 0~1 归一化
    }
    """
    # ========== 第一部分：研究方向匹配 ==========
    research_score = 0
    # 将研究方向、课程、科研成果合并为匹配文本
    text_parts = teacher.get("research", []) + teacher.get("courses", [])
    achievements = teacher.get("achievements", [])
    if achievements:
        text_parts.extend(achievements)
    text = " ".join(text_parts)

    matched_interests = []
    matched_goals = []
    max_possible_score = 0

    # 兴趣匹配
    for profile_tag, info in user_profile.get("interest", {}).items():
        weight = info.get("composite_score", 0)
        if weight <= 0:
            continue
        max_possible_score += weight
        
        tag_name = profile_tag
        # 尝试翻译为中文
        from app.agent.trying import NAME_MAP
        if profile_tag in NAME_MAP:
            tag_name = NAME_MAP[profile_tag]
        
        matched_kws = []
        if profile_tag in KEYWORD_MAP:
            keywords = KEYWORD_MAP.get(profile_tag, [])
            for kw in keywords:
                if kw in text:
                    matched_kws.append(kw)
            if matched_kws:
                research_score += weight
                matched_interests.append({
                    "tag": tag_name,
                    "weight": round(weight, 2),
                    "keywords": matched_kws[:3]  # 最多3个关键词
                })
        else:
            if profile_tag in text:
                research_score += weight
                matched_interests.append({
                    "tag": tag_name,
                    "weight": round(weight, 2),
                    "keywords": [profile_tag]
                })

    # 目标匹配
    for profile_tag, info in user_profile.get("goal", {}).items():
        weight = info.get("composite_score", 0)
        if weight <= 0:
            continue
        max_possible_score += weight
        
        tag_name = profile_tag
        from app.agent.trying import NAME_MAP
        if profile_tag in NAME_MAP:
            tag_name = NAME_MAP[profile_tag]
        
        matched_kws = []
        if profile_tag in KEYWORD_MAP:
            keywords = KEYWORD_MAP.get(profile_tag, [])
            for kw in keywords:
                if kw in text:
                    matched_kws.append(kw)
            if matched_kws:
                research_score += weight
                matched_goals.append({
                    "tag": tag_name,
                    "weight": round(weight, 2),
                    "keywords": matched_kws[:3]
                })
        else:
            if profile_tag in text:
                research_score += weight
                matched_goals.append({
                    "tag": tag_name,
                    "weight": round(weight, 2),
                    "keywords": [profile_tag]
                })

    # 归一化研究方向匹配度
    research_match = round(min(research_score / max(max_possible_score, 1), 1.0), 2)

    # ========== 第二部分：课程-目标匹配 ==========
    courses = teacher.get("courses", [])
    course_goal_score = 0
    goal_count = 0

    for goal_tag, info in user_profile.get("goal", {}).items():
        goal_weight = info.get("composite_score", 0)
        if goal_weight > 0:
            goal_course_score = calculate_course_goal_score(courses, goal_tag)
            course_goal_score += goal_course_score * goal_weight
            goal_count += 1

    if goal_count > 0:
        course_goal_score = course_goal_score / goal_count
    else:
        course_goal_score = 0

    course_match = round(min(course_goal_score, 1.0), 2)

    # ========== 综合 ==========
    final_score = research_score * 0.7 + course_goal_score * 2.0 * 0.3

    return {
        "score": round(final_score, 2),
        "matched_interests": matched_interests,
        "matched_goals": matched_goals,
        "research_match": research_match,
        "course_match": course_match
    }


def recommend_teachers(user_profile: Dict, top_n: int = 5, session_id: str = "default") -> List[Dict]:
    """
    推荐导师，带缓存。
    纯算法匹配，不调用 LLM，毫秒级返回。
    """
    # 尝试从缓存获取
    cached = get_cached_teacher_scores(session_id)
    if cached is not None and len(cached) > 0:
        logger.info("导师评分缓存命中: session=%s, 数量=%d", session_id, len(cached))
        return cached[:top_n]

    teachers = load_teachers()
    if not teachers:
        return []

    scored_teachers = []
    for teacher in teachers:
        result = calculate_teacher_score(teacher, user_profile)
        if result["score"] > 0:
            teacher["score"] = result["score"]
            teacher["match_reason"] = {
                "matched_interests": result["matched_interests"],
                "matched_goals": result["matched_goals"],
                "research_match": result["research_match"],
                "course_match": result["course_match"]
            }
            scored_teachers.append(teacher)

    scored_teachers.sort(key=lambda x: x["score"], reverse=True)

    # 如果画像为空（没有匹配到任何导师），返回所有导师（按默认顺序）
    if not scored_teachers:
        for teacher in teachers:
            teacher["score"] = "暂无画像"
            teacher["match_reason"] = {}
            scored_teachers.append(teacher)

    # 缓存评分结果（前30个）
    cache_teacher_scores(session_id, scored_teachers[:30])

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