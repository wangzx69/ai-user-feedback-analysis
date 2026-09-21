# -*- coding: utf-8 -*-
"""
一键运行：采集 → 清洗 → 分析 → 报告 → 打开浏览器
用法：python run_all.py
"""
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE.parent / "data"

def run_step(name, script):
    print(f"\n{'='*55}")
    print(f"  ▶ {name}")
    print(f"{'='*55}")
    result = subprocess.run(
        [sys.executable, str(BASE / script)],
        cwd=str(BASE),
    )
    if result.returncode != 0:
        print(f"\n❌ {name} 失败了！")
        return False
    return True

def main():
    print("=" * 55)
    print("  AI用户评论分析 - 一键运行")
    print("  流程：采集 → 清洗 → 分析 → 报告")
    print("=" * 55)

    # Step 1: 采集（需要用户手动按回车）
    print("\n【第1步/4步】采集评论")
    print("  浏览器会打开TapTap页面，处理完弹窗后按回车开始采集")
    if not run_step("采集", "scraper.py"):
        return

    # Step 2: 清洗+分析+报告（全自动）
    print("\n【第2步/4步】数据清洗 + 质量过滤")
    # 这里调用我们之前的clean逻辑
    subprocess.run([sys.executable, str(BASE / "clean_reviews.py")], cwd=str(BASE))

    print("\n【第3步/4步】规则分析 + 生成报告")
    subprocess.run([sys.executable, str(BASE / "analyze_reviews.py")], cwd=str(BASE))

    print("\n【第4步/4步】完成！打开报告")
    report = DATA / "原神评论分析报告.html"
    if report.exists():
        import webbrowser
        webbrowser.open(str(report))
        print(f"  报告已在浏览器打开: {report}")

    print(f"\n{'='*55}")
    print("  ✅ 全部完成！")
    print(f"  数据: {DATA / 'reviews_clean.csv'}")
    print(f"  报告: {report}")
    print(f"{'='*55}")

if __name__ == "__main__":
    main()
