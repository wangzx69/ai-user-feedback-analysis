# -*- coding: utf-8 -*-
"""美妆评论分析报告自动生成器"""
import pandas as pd, sys, re, json
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============ 1. 读数据 ============
df = pd.read_csv(r"D:\AI用户反馈分析工作流\data\beauty_reviews_100.csv")
print(f"读取{len(df)}条评论")

# ============ 2. 规则分析（情感/主题/痛点）============

# 情感判断
def get_sentiment(text):
    bad_words = ["黏", "油", "刺痛", "过敏", "泛红", "烂脸", "没效果", "不值", "贵", "踩雷", "闲置", "搓泥", "不吸收", "假", "智商税"]
    good_words = ["好", "满意", "回购", "舒服", "温和", "效果", "绝", "赞", "喜欢", "推荐", "救", "亮", "润", "软", "稳定", "安心"]
    bad_count = sum(1 for w in bad_words if w in text)
    good_count = sum(1 for w in good_words if w in text)
    if bad_count > good_count:
        return "负面"
    elif good_count > bad_count:
        return "正面"
    else:
        return "中性"

# 主题判断（多标签）
def get_topics(text):
    topics = []
    if any(w in text for w in ["保湿", "干", "不紧绷", "脱皮", "水润", "润"]):
        topics.append("保湿效果")
    if any(w in text for w in ["提亮", "暗沉", "蜡黄", "亮", "痘印"]):
        topics.append("提亮效果")
    if any(w in text for w in ["抗老", "皱纹", "紧致", "垮", "细纹"]):
        topics.append("抗老效果")
    if any(w in text for w in ["黏", "油", "厚重", "搓泥", "不吸收", "吸收"]):
        topics.append("肤感质地")
    if any(w in text for w in ["过敏", "刺痛", "泛红", "敏感肌", "温和", "刺激"]):
        topics.append("敏感肌适配")
    if any(w in text for w in ["贵", "性价比", "值", "便宜", "量少"]):
        topics.append("价格性价比")
    if not topics:
        topics.append("其他")
    return topics

# 肤质判断
def get_skin_type(text):
    if any(w in text for w in ["干皮", "大干皮", "沙漠", "混干"]):
        return "干皮/混干"
    elif any(w in text for w in ["油皮", "混油", "油光"]):
        return "油皮/混油"
    elif any(w in text for w in ["敏感肌", "过敏", "泛红"]):
        return "敏感肌"
    else:
        return "未提及"

df['sentiment'] = df['clean_text'].apply(get_sentiment)
df['topics'] = df['clean_text'].apply(get_topics)
df['skin_type'] = df['clean_text'].apply(get_skin_type)

# 统计
total = len(df)
good = len(df[df['sentiment'] == "正面"])
bad = len(df[df['sentiment'] == "负面"])
mid = len(df[df['sentiment'] == "中性"])

print(f"正面: {good}条 ({good/total*100:.0f}%)")
print(f"负面: {bad}条 ({bad/total*100:.0f}%)")
print(f"中性: {mid}条 ({mid/total*100:.0f}%)")

# 主题统计
topic_counts = {}
for topics in df['topics']:
    for t in topics:
        topic_counts[t] = topic_counts.get(t, 0) + 1

# 痛点统计（负面评论里的主题）
bad_df = df[df['sentiment'] == "负面"]
bad_topic_counts = {}
for topics in bad_df['topics']:
    for t in topics:
        bad_topic_counts[t] = bad_topic_counts.get(t, 0) + 1

# 肤质统计
skin_counts = df['skin_type'].value_counts().to_dict()

# ============ 3. 生成HTML报告 ============

# 痛点TOP5
top_pains = sorted(bad_topic_counts.items(), key=lambda x: -x[1])[:5]

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>美妆精华产品消费者评论分析报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif; background: #fdf2f8; color: #333; line-height: 1.6; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
.cover {{ background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%); color: white; padding: 60px 40px; border-radius: 16px; margin-bottom: 30px; }}
.cover h1 {{ font-size: 36px; margin-bottom: 16px; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
.kpi-card {{ background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.kpi-card .label {{ font-size: 13px; color: #999; margin-bottom: 8px; }}
.kpi-card .value {{ font-size: 32px; font-weight: 700; }}
.chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }}
.chart-box {{ background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.chart {{ height: 300px; }}
.table-box {{ background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 30px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #f0f0f0; font-size: 14px; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
.badge-p0 {{ background: #fee2e2; color: #dc2626; }}
.badge-p1 {{ background: #fef3c7; color: #d97706; }}
</style>
</head>
<body>
<div class="container">
<div class="cover">
  <h1>美妆精华产品消费者评论分析报告</h1>
  <p>数据来源：美妆精华类产品评论 · 有效评论{total}条 · 自动生成</p>
</div>

<div class="kpi-grid">
  <div class="kpi-card">
    <div class="label">总评论数</div>
    <div class="value">{total}</div>
  </div>
  <div class="kpi-card" style="color:#10b981">
    <div class="label">好评率</div>
    <div class="value">{good/total*100:.0f}%</div>
  </div>
  <div class="kpi-card" style="color:#ef4444">
    <div class="label">差评率</div>
    <div class="value">{bad/total*100:.0f}%</div>
  </div>
  <div class="kpi-card" style="color:#f59e0b">
    <div class="label">中性评价</div>
    <div class="value">{mid/total*100:.0f}%</div>
  </div>
</div>

<div class="chart-row">
  <div class="chart-box">
    <h3>情感分布</h3>
    <div id="sentimentPie" class="chart"></div>
  </div>
  <div class="chart-box">
    <h3>主题热度</h3>
    <div id="topicBar" class="chart"></div>
  </div>
</div>

<div class="table-box">
  <h3>核心痛点TOP5</h3>
  <table>
    <tr><th>排名</th><th>痛点</th><th>频次</th><th>优先级</th></tr>
    {"".join(f"<tr><td>{i+1}</td><td>{p[0]}</td><td>{p[1]}条</td><td><span class='badge badge-p0'>P0</span></td></tr>" if i<2 else f"<tr><td>{i+1}</td><td>{p[0]}</td><td>{p[1]}条</td><td><span class='badge badge-p1'>P1</span></td></tr>" for i, p in enumerate(top_pains))}
  </table>
</div>

</div>
<script>
const sentimentPie = echarts.init(document.getElementById('sentimentPie'));
sentimentPie.setOption({{
  series: [{{
    type: 'pie',
    radius: ['40%', '70%'],
    data: [
      {{ value: {good}, name: '好评', itemStyle: {{ color: '#10b981' }} }},
      {{ value: {bad}, name: '差评', itemStyle: {{ color: '#ef4444' }} }},
      {{ value: {mid}, name: '中性', itemStyle: {{ color: '#f59e0b' }} }},
    ]
  }}]
}});

const topicBar = echarts.init(document.getElementById('topicBar'));
topicBar.setOption({{
  xAxis: {{ type: 'value' }},
  yAxis: {{ type: 'category', data: {json.dumps(list(topic_counts.keys()))} }},
  series: [{{ type: 'bar', data: {json.dumps(list(topic_counts.values()))} }}]
}});
</script>
</body>
</html>"""

out = Path(r"D:\AI用户反馈分析工作流\data\美妆精华评论分析报告.html")
out.write_text(html, encoding="utf-8")
print(f"\n✅ 报告已生成: {out}")
