# -*- coding: utf-8 -*-
"""
原神玩家评论 AI 分析引擎
功能：读取清洗后的数据 → 主题聚类 + 情感分析 + 痛点统计 → 输出分析结果JSON
"""
import json
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "data" / "reviews_clean.csv"
OUTPUT_JSON = BASE_DIR / "data" / "analysis_result.json"

# ===================== 主题词库 =====================
TOPICS = {
    "抽卡与保底": ["抽卡", "保底", "歪", "常驻", "限定", "十连", "氪", "充钱", "概率", "金", "水位", "小保底", "大保底", "五星", "四星"],
    "剧情与角色": ["剧情", "主线", "传说", "任务", "过场", "演出", "角色", "人设", "性格", "塑造", "人物", "故事"],
    "福利与运营": ["福利", "送", "月卡", "签到", "奖励", "原石", "活动", "运营", "策划", "版本", "更新", "补偿"],
    "战斗与深渊": ["深渊", "螺旋", "战斗", "手感", "机制", "配队", "强度", "联机", "boss", "怪物", "技能"],
    "画面与音乐": ["画面", "画质", "音乐", "BGM", "美术", "建模", "立绘", "特效", "画风", "场景", "风景"],
    "优化与性能": ["卡顿", "闪退", "发热", "掉帧", "优化", "bug", "BUG", "卡", "加载", "内存", "耗电"],
    "探索与开放世界": ["探索", "跑图", "地图", "大世界", "宝箱", "解谜", "收集", "传送", "跑", "自由度"],
    "新手与回坑": ["新手", "开荒", "回坑", "退坑", "入坑", "肝", "长草", "无聊", "日常", "毕业"],
}

POSITIVE_WORDS = ["好玩", "喜欢", "不错", "优秀", "精彩", "感动", "热爱", "棒", "好", "赞", "惊喜", "良心", "丰富", "沉浸", "自由", "精致"]
NEGATIVE_WORDS = ["无聊", "恶心", "肝", "坑", "骗", "逼氪", "恶心", "差", "烂", "失望", "难受", "折磨", "恶心人", "离谱", "不行", "坑钱", "退钱"]

def clean_text(text):
    """清理正文：去掉用户名前缀和'玩过'标签"""
    if pd.isna(text):
        return ""
    text = str(text)
    # 去掉开头的"用户名 玩过"
    text = re.sub(r'^[\s\S]{1,20}?\s+(玩过|想玩|在玩)\s*', '', text)
    # 去掉回复区（"用户名 :"之后的内容）
    text = re.sub(r'[^\s，。！？,.!?：:]{1,15}\s*[:：][\s\S]*$', '', text)
    # 去掉时间/设备
    text = re.sub(r'\d+\s*(小时|天|分钟)前[\s\S]*$', '', text)
    text = re.sub(r'来自\s+[\s\S]*$', '', text)
    return text.strip()

def classify_topic(text):
    """给评论文本打主题标签（一条评论可能属于多个主题）"""
    topics = []
    for topic, keywords in TOPICS.items():
        for kw in keywords:
            if kw in text:
                topics.append(topic)
                break
    return topics if topics else ["其他"]

def classify_sentiment(text, rating):
    """情感分析：结合评分和关键词"""
    score = 0
    if rating:
        try:
            r = float(rating)
            if r >= 4:
                score += 2
            elif r <= 2:
                score -= 2
        except:
            pass
    for w in POSITIVE_WORDS:
        if w in text:
            score += 1
            break
    for w in NEGATIVE_WORDS:
        if w in text:
            score -= 1
            break
    if score >= 2:
        return "正面"
    elif score <= -1:
        return "负面"
    return "中性"

def main():
    print("=" * 55)
    print("  原神玩家评论分析引擎")
    print("=" * 55)

    # 读取数据
    df = pd.read_csv(INPUT_FILE)
    print(f"\n读取: {len(df)} 条")

    # 清洗正文
    df["clean_text"] = df["review_text"].apply(clean_text)

    # 按用户名去重（保留最长的）
    df = df.sort_values("clean_text", key=lambda x: x.str.len(), ascending=False)
    df = df.drop_duplicates(subset=["username"], keep="first")
    df = df[df["clean_text"].str.len() >= 10]
    print(f"去重+过滤后: {len(df)} 个不同用户")

    # 主题分类
    all_topics = []
    for text in df["clean_text"]:
        topics = classify_topic(text)
        all_topics.append(topics)
    df["topics"] = all_topics

    # 情感分析
    df["sentiment"] = [classify_sentiment(t, r) for t, r in zip(df["clean_text"], df.get("rating", []))]

    # ===== 统计 =====
    result = {}

    # 1. 概览
    result["overview"] = {
        "total": len(df),
        "avg_rating": round(df["rating"].dropna().astype(float).mean(), 1) if "rating" in df.columns else 0,
        "rating_dist": {str(k): int(v) for k, v in df["rating"].value_counts().sort_index().items()},
        "sentiment_dist": dict(df["sentiment"].value_counts()),
        "avg_length": int(df["clean_text"].str.len().mean()),
    }

    # 2. 主题分布
    topic_counter = Counter()
    topic_sentiment = defaultdict(lambda: Counter())
    for topics, sentiment in zip(df["topics"], df["sentiment"]):
        for t in topics:
            topic_counter[t] += 1
            topic_sentiment[t][sentiment] += 1

    result["topics"] = {}
    for topic, count in topic_counter.most_common():
        result["topics"][topic] = {
            "count": count,
            "sentiment": dict(topic_sentiment[topic]),
            "pct": round(count / len(df) * 100, 1),
        }

    # 3. 痛点TOP5（负面评论最多的主题）
    pain_points = []
    for topic in topic_counter.keys():
        neg = topic_sentiment[topic].get("负面", 0)
        total = topic_counter[topic]
        if total >= 3:
            pain_points.append({
                "topic": topic,
                "negative_count": neg,
                "total": total,
                "negative_ratio": round(neg / total * 100, 1),
            })
    pain_points.sort(key=lambda x: x["negative_ratio"], reverse=True)
    result["pain_points"] = pain_points[:5]

    # 4. 正面评价TOP5
    pos_points = []
    for topic in topic_counter.keys():
        pos = topic_sentiment[topic].get("正面", 0)
        total = topic_counter[topic]
        if total >= 3:
            pos_points.append({
                "topic": topic,
                "positive_count": pos,
                "total": total,
                "positive_ratio": round(pos / total * 100, 1),
            })
    pos_points.sort(key=lambda x: x["positive_ratio"], reverse=True)
    result["pos_points"] = pos_points[:5]

    # 5. 精选评论（每个主题挑1条最有代表性的长评论）
    result["sample_reviews"] = {}
    for topic in topic_counter.keys():
        topic_df = df[df["topics"].apply(lambda ts: topic in ts)]
        if len(topic_df) > 0:
            longest = topic_df.loc[topic_df["clean_text"].str.len().idxmax()]
            result["sample_reviews"][topic] = {
                "username": longest.get("username", ""),
                "rating": str(longest.get("rating", "")),
                "text": longest["clean_text"][:300],
            }

    # 6. 高频词统计（简单分词：按2-4字滑窗）
    all_text = " ".join(df["clean_text"].tolist())
    # 游戏高频关键词
    keyword_freq = Counter()
    for topic, keywords in TOPICS.items():
        for kw in keywords:
            cnt = all_text.count(kw)
            if cnt > 0:
                keyword_freq[kw] = cnt
    result["keyword_freq"] = dict(keyword_freq.most_common(20))

    # 保存JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        def to_native(obj):
            import numpy as np
            if isinstance(obj, (np.integer,)): return int(obj)
            if isinstance(obj, (np.floating,)): return float(obj)
            if isinstance(obj, np.ndarray): return obj.tolist()
            return str(obj)
        json.dump(result, f, ensure_ascii=False, indent=2, default=to_native)

    # 打印摘要
    print(f"\n✅ 分析完成！")
    print(f"  平均评分: {result['overview']['avg_rating']}")
    print(f"  情感分布: {result['overview']['sentiment_dist']}")
    print(f"  平均长度: {result['overview']['avg_length']} 字")
    print(f"\n=== 主题分布 ===")
    for topic, data in sorted(result["topics"].items(), key=lambda x: -x[1]["count"]):
        print(f"  {topic}: {data['count']}条 ({data['pct']}%)")
    print(f"\n=== 痛点TOP5（负面率最高）===")
    for pp in result["pain_points"]:
        print(f"  {pp['topic']}: 负面率 {pp['negative_ratio']}% ({pp['negative_count']}/{pp['total']})")
    print(f"\n结果已保存: {OUTPUT_JSON.resolve()}")

if __name__ == "__main__":
    main()


