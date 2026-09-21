# -*- coding: utf-8 -*-
"""生成HTML可视化报告"""
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent.parent
INPUT_JSON = BASE_DIR / "data" / "analysis_result.json"
OUTPUT_HTML = BASE_DIR / "data" / "原神评论分析报告.html"

def main():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    overview = data["overview"]
    topics = data["topics"]
    pain_points = data["pain_points"]
    pos_points = data["pos_points"]
    keyword_freq = data["keyword_freq"]
    samples = data.get("sample_reviews", {})

    # 准备图表数据
    rating_labels = [f"{k}星" for k in overview["rating_dist"].keys()]
    rating_values = list(overview["rating_dist"].values())

    topic_names = list(topics.keys())
    topic_counts = [topics[t]["count"] for t in topic_names]
    topic_pos = [topics[t]["sentiment"].get("正面", 0) for t in topic_names]
    topic_neu = [topics[t]["sentiment"].get("中性", 0) for t in topic_names]
    topic_neg = [topics[t]["sentiment"].get("负面", 0) for t in topic_names]

    pain_names = [p["topic"] for p in pain_points]
    pain_ratios = [p["negative_ratio"] for p in pain_points]

    sentiment_data = [{"name": k, "value": v} for k, v in overview["sentiment_dist"].items()]

    kw_items = list(keyword_freq.items())[:15]
    kw_names = [k for k, v in kw_items]
    kw_values = [v for k, v in kw_items]

    # 精选评论
    sample_html = ""
    for topic, sample in list(samples.items())[:5]:
        sample_html += f"""
        <div class="sample-card">
            <div class="sample-topic">{topic}</div>
            <div class="sample-text">{sample['text']}...</div>
            <div class="sample-meta">— {sample['username']}（{sample['rating']}星）</div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>原神玩家评论分析报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif; background: #0f1923; color: #e0e0e0; padding: 20px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
.header {{ text-align: center; padding: 30px 0; }}
.header h1 {{ font-size: 28px; color: #fff; margin-bottom: 8px; }}
.header p {{ color: #8899aa; font-size: 14px; }}
.cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0; }}
.card {{ background: #1a2736; border-radius: 12px; padding: 20px; text-align: center; }}
.card .num {{ font-size: 32px; font-weight: bold; color: #4fc3f7; }}
.card .label {{ font-size: 13px; color: #8899aa; margin-top: 4px; }}
.charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0; }}
.chart-box {{ background: #1a2736; border-radius: 12px; padding: 20px; }}
.chart-box h3 {{ font-size: 15px; color: #ccc; margin-bottom: 12px; }}
.chart {{ width: 100%; height: 320px; }}
.full {{ grid-column: 1 / -1; }}
.samples {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0; }}
.sample-card {{ background: #1a2736; border-radius: 12px; padding: 16px; }}
.sample-topic {{ display: inline-block; background: #2d4a5e; color: #4fc3f7; padding: 2px 10px; border-radius: 10px; font-size: 12px; margin-bottom: 8px; }}
.sample-text {{ font-size: 13px; line-height: 1.6; color: #bbb; }}
.sample-meta {{ font-size: 12px; color: #667; margin-top: 8px; text-align: right; }}
.insight {{ background: #1a2736; border-radius: 12px; padding: 20px; margin: 16px 0; }}
.insight h3 {{ color: #4fc3f7; margin-bottom: 12px; }}
.insight ul {{ list-style: none; padding: 0; }}
.insight li {{ padding: 8px 0; border-bottom: 1px solid #22303f; font-size: 14px; line-height: 1.6; }}
.insight li:last-child {{ border: none; }}
.insight strong {{ color: #ffb74d; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>原神玩家评论分析报告</h1>
        <p>数据来源：TapTap | 样本：{overview['total']}位不同用户 | 平均评分：{overview['avg_rating']}</p>
    </div>

    <div class="cards">
        <div class="card"><div class="num">{overview['total']}</div><div class="label">有效评论用户</div></div>
        <div class="card"><div class="num">{overview['avg_rating']}</div><div class="label">平均评分</div></div>
        <div class="card"><div class="num">{overview['sentiment_dist'].get('正面',0)}</div><div class="label">正面评价</div></div>
        <div class="card"><div class="num">{overview['sentiment_dist'].get('负面',0)}</div><div class="label">负面评价</div></div>
    </div>

    <div class="charts">
        <div class="chart-box">
            <h3>评分分布</h3>
            <div id="ratingChart" class="chart"></div>
        </div>
        <div class="chart-box">
            <h3>情感倾向</h3>
            <div id="sentimentChart" class="chart"></div>
        </div>
    </div>

    <div class="charts">
        <div class="chart-box full">
            <h3>主题分布（按情感堆叠）</h3>
            <div id="topicChart" class="chart" style="height:380px"></div>
        </div>
    </div>

    <div class="charts">
        <div class="chart-box">
            <h3>痛点TOP5（负面率最高）</h3>
            <div id="painChart" class="chart"></div>
        </div>
        <div class="chart-box">
            <h3>高频关键词</h3>
            <div id="kwChart" class="chart"></div>
        </div>
    </div>

    <div class="insight">
        <h3>关键洞察</h3>
        <ul>
            <li><strong>抽卡与保底</strong>是最大痛点（负面率{pain_points[0]['negative_ratio']}%）——玩家对抽卡概率和保底机制抱怨最多，尤其是"歪"和常驻池污染。</li>
            <li><strong>剧情与角色</strong>是讨论最集中的话题（{topics.get('剧情与角色',{}).get('pct',0)}%）——玩家既肯定角色塑造，也抱怨任务安排太紧张、传说任务塞进活动。</li>
            <li><strong>新手与回坑</strong>话题占比{topics.get('新手与回坑',{}).get('pct',0)}%——新玩家反馈剧情不能跳过、跑图单一；回坑玩家关注福利变化和角色强度膨胀。</li>
            <li><strong>战斗与深渊</strong>负面率{pain_points[2]['negative_ratio'] if len(pain_points)>2 else 0}%——7.0版本新机制怪被认为是"逼氪"，老角色没有出场机会。</li>
            <li><strong>正面评价</strong>集中在画面音乐、开放世界探索自由度和版本福利提升。</li>
        </ul>
    </div>

    <div class="chart-box" style="margin:16px 0">
        <h3>代表性评论</h3>
        <div class="samples">
            {sample_html}
        </div>
    </div>
</div>

<script>
// 评分分布
echarts.init(document.getElementById('ratingChart')).setOption({{
    tooltip: {{ trigger: 'item' }},
    series: [{{ type: 'pie', radius: ['40%','70%'], data: {json.dumps([{{"name": l, "value": v}} for l,v in zip(rating_labels, rating_values)]), ensure_ascii=False},
        label: {{ color: '#ccc' }} }}]
}});

// 情感分布
echarts.init(document.getElementById('sentimentChart')).setOption({{
    tooltip: {{ trigger: 'item' }},
    series: [{{ type: 'pie', radius: ['40%','70%'], data: {json.dumps(sentiment_data, ensure_ascii=False)},
        color: ['#66bb6a','#ffa726','#ef5350'], label: {{ color: '#ccc' }} }}]
}});

// 主题堆叠柱状图
echarts.init(document.getElementById('topicChart')).setOption({{
    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
    legend: {{ data: ['正面','中性','负面'], textStyle: {{ color: '#aaa' }} }},
    grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
    xAxis: {{ type: 'category', data: {json.dumps(topic_names, ensure_ascii=False)}, axisLabel: {{ color: '#aaa', rotate: 30 }} }},
    yAxis: {{ type: 'value', axisLabel: {{ color: '#aaa' }} }},
    series: [
        {{ name: '正面', type: 'bar', stack: 'total', data: {json.dumps(topic_pos)}, color: '#66bb6a' }},
        {{ name: '中性', type: 'bar', stack: 'total', data: {json.dumps(topic_neu)}, color: '#ffa726' }},
        {{ name: '负面', type: 'bar', stack: 'total', data: {json.dumps(topic_neg)}, color: '#ef5350' }},
    ]
}});

// 痛点TOP5
echarts.init(document.getElementById('painChart')).setOption({{
    tooltip: {{ trigger: 'axis' }},
    grid: {{ left: '3%', right: '8%', containLabel: true }},
    xAxis: {{ type: 'value', axisLabel: {{ color: '#aaa', formatter: '{{value}}%' }} }},
    yAxis: {{ type: 'category', data: {json.dumps(list(reversed(pain_names)), ensure_ascii=False)}, axisLabel: {{ color: '#aaa' }} }},
    series: [{{ type: 'bar', data: {json.dumps(list(reversed(pain_ratios)))}, itemStyle: {{ color: '#ef5350' }}, label: {{ show: true, position: 'right', formatter: '{{c}}%', color: '#ccc' }} }}]
}});

// 高频词
echarts.init(document.getElementById('kwChart')).setOption({{
    tooltip: {{}},
    grid: {{ left: '3%', right: '8%', containLabel: true }},
    xAxis: {{ type: 'value', axisLabel: {{ color: '#aaa' }} }},
    yAxis: {{ type: 'category', data: {json.dumps(list(reversed(kw_names)), ensure_ascii=False)}, axisLabel: {{ color: '#aaa' }} }},
    series: [{{ type: 'bar', data: {json.dumps(list(reversed(kw_values)))}, itemStyle: {{ color: '#4fc3f7' }} }}]
}});
</script>
</body>
</html>"""

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"✅ 报告已生成: {OUTPUT_HTML.resolve()}")

if __name__ == "__main__":
    main()
