# -*- coding: utf-8 -*-
"""
评论数据清洗脚本 - 修复版
使用方法：在 Anaconda Prompt 中运行 python clean_reviews.py
"""

import sys
import re
import pandas as pd
from pathlib import Path

# 修复 Windows 控制台中文乱码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 输入输出路径
BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "data" / "reviews_raw.csv"
OUTPUT_FILE = BASE_DIR / "data" / "reviews_for_coze.xlsx"

MIN_TEXT_LENGTH = 10
MAX_TEXT_LENGTH = 5000
MAX_ROWS = 100


def clean_review_text(text):
    if pd.isna(text):
        return ""
    text = str(text)
    # 移除 URL
    text = re.sub(r"https?://\S+", "", text)
    # 移除零宽字符等不可见字符
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]", "", text)
    # 移除 Markdown 图片和链接
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[.*?\]\(.*?\)", "", text)
    # 合并空白
    text = re.sub(r"\s+", " ", text)
    # 移除常见噪声词（出现在末尾时）
    for noise in ["展开全文", "收起全文", "查看更多", "回复", "举报", "分享", "展开", "收起"]:
        if text.endswith(noise):
            text = text[: -len(noise)]
    # 移除开头的"玩过"等标签
    text = re.sub(r"^\s*(玩过|想玩|在玩)\s+", "", text)
    return text.strip()


def extract_rating(rating_raw):
    if pd.isna(rating_raw) or str(rating_raw).strip() == "":
        return ""
    rating_str = str(rating_raw).strip()
    # 已经是数字
    try:
        val = float(rating_str)
        if 0 <= val <= 5:
            return val
        if 5 < val <= 10:
            return round(val / 2, 1)
    except ValueError:
        pass
    # 从文本中提取数字
    match = re.search(r"(\d+\.?\d*)\s*[星分]?", rating_str)
    if match:
        val = float(match.group(1))
        if 0 <= val <= 5:
            return val
        if 5 < val <= 10:
            return round(val / 2, 1)
    # 星星字符
    star_count = len(re.findall(r"[★⭐]", rating_str))
    if star_count > 0:
        return star_count
    return ""


def detect_language(text):
    if not text:
        return "unknown"
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    total = len(text.strip())
    if total == 0:
        return "unknown"
    ratio = chinese_chars / total
    if ratio > 0.5:
        return "zh"
    elif ratio < 0.1:
        return "en"
    return "mixed"


def estimate_quality(text):
    if not text:
        return "low"
    length = len(text.strip())
    if length > 100:
        return "high"
    elif length >= 20:
        return "medium"
    return "low"


def main():
    print("=" * 55)
    print("  评论数据清洗工具 - 修复版")
    print("=" * 55)

    if not INPUT_FILE.exists():
        print(f"\n❌ 找不到输入文件: {INPUT_FILE}")
        print("请先运行 scraper.py 采集评论数据。")
        return

    print(f"\n读取: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, dtype=str)
    df = df.fillna("")
    print(f"  原始数据: {len(df)} 条")

    print("\n[1/5] 清洗评论文本...")
    df["review_text"] = df["review_text"].map(clean_review_text)

    print("[2/5] 过滤无效数据...")
    before = len(df)
    df = df[df["review_text"].str.len() >= MIN_TEXT_LENGTH]
    print(f"  移除短评论: {before - len(df)} 条")

    print("[3/5] 去除重复评论...")
    before = len(df)
    df = df.drop_duplicates(subset=["review_text"])
    print(f"  去除重复: {before - len(df)} 条")

    print("[4/5] 添加结构化字段...")
    df.insert(0, "feedback_id", range(1, len(df) + 1))
    if "rating" in df.columns:
        df["rating"] = df["rating"].map(extract_rating)
    else:
        df["rating"] = ""
    df["language"] = df["review_text"].map(detect_language)
    df["quality"] = df["review_text"].map(estimate_quality)
    df["text_length"] = df["review_text"].str.len()

    print("[5/5] 添加人工复核字段...")
    df["review_text"] = df["review_text"].apply(
        lambda x: x[:MAX_TEXT_LENGTH] + "..." if len(x) > MAX_TEXT_LENGTH else x
    )
    df["manual_sentiment"] = ""
    df["manual_topic"] = ""
    df["manual_priority"] = ""
    df["manual_notes"] = ""

    df = df.head(MAX_ROWS)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")

    print(f"\n✅ 清洗完成！有效评论: {len(df)} 条")
    print(f"  保存: {OUTPUT_FILE.resolve()}")
    print(f"\n数据概览:")
    print(f"  语言分布: {df['language'].value_counts().to_dict()}")
    print(f"  质量分布: {df['quality'].value_counts().to_dict()}")
    if "rating" in df.columns:
        rated = df[df["rating"] != ""]
        if len(rated) > 0:
            print(f"  评分分布: {rated['rating'].value_counts().sort_index().to_dict()}")
    print(f"  平均长度: {df['text_length'].mean():.0f} 字")


if __name__ == "__main__":
    main()
