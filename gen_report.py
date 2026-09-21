# -*- coding: utf-8 -*-
import json, sys, pickle
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

stats = pickle.load(open(r'D:\AI用户反馈分析工作流\data\_report_stats.pkl','rb'))
total = stats['total']
avg = stats['avg_score']
sent = stats['sent']
emotion = stats['emotion']
topics = stats['topics']
topic_sent = stats['topic_sent']
topic_comments = stats['topic_comments']

pos_pct = sent.get('正面',0)/total*100
neg_pct = sent.get('负面',0)/total*100
neu_pct = sent.get('中性',0)/total*100

# 主题卡片 - 确保每个主题的代表性评论不重复
topic_cards = ''
used_comments = set()
for topic, count in topics[:6]:
    ts = topic_sent.get(topic, {})
    pos = ts.get('正面', 0)
    neu = ts.get('中性', 0)
    neg = ts.get('负面', 0)
    tot = pos+neu+neg
    neg_rate = neg/tot*100 if tot else 0
    # 优先选负面带痛点的，且不重复
    rep = None
    for c in topic_comments.get(topic, []):
        key = c['评论'][:50]
        if c['情感']=='负面' and c['痛点']!='无' and key not in used_comments:
            rep = c; used_comments.add(key); break
    if not rep:
        for c in topic_comments.get(topic, []):
            key = c['评论'][:50]
            if key not in used_comments:
                rep = c; used_comments.add(key); break
    rep_html = ''
    if rep:
        txt = rep['评论']
        rep_html = '<details><summary>点击展开完整评论</summary>' + \
            '<div class="comment-text"><p><strong>' + rep['情感'] + '</strong> · ' + rep['总结'] + '</p>' + \
            '<p style="color:#666;margin-top:8px">' + txt + '</p></div></details>'
    topic_cards += '<div class="topic-card"><h3>' + topic + ' <span style="font-size:13px;color:#999">(' + str(count) + '条提及)</span></h3>' + \
        '<div class="topic-stats"><span class="badge pos">正面 ' + str(pos) + '</span>' + \
        '<span class="badge neu">中性 ' + str(neu) + '</span>' + \
        '<span class="badge neg">负面 ' + str(neg) + ' (' + str(int(neg_rate)) + '%)</span></div>' + rep_html + '</div>'

# 痛点关键词
pain_keywords = ['剧情无法跳过','抽卡歪','原石少','福利少','圣遗物','卡顿','闪退','发热','剧情长','长草期','数值膨胀','老角色']
pain_counts = {kw:0 for kw in pain_keywords}
for topic in ['抽卡保底','剧情角色','优化性能','福利运营']:
    for item in topic_comments.get(topic,[]):
        p = item.get('痛点','')
        for kw in pain_keywords:
            if kw in p: pain_counts[kw] += 1
top_pains_sorted = sorted(pain_counts.items(), key=lambda x:-x[1])[:5]
pains_html = ''
for i,(kw,c) in enumerate(top_pains_sorted,1):
    if c > 0:
        pains_html += '<div class="pain-item"><strong>P' + str(i) + '</strong> · ' + kw + ' <span style="color:#999">(' + str(c) + '次)</span></div>\n'

sent_pos = sent.get('正面',0)
sent_neu = sent.get('中性',0)
sent_neg = sent.get('负面',0)
emo_keys = list(emotion.keys())
emo_vals = list(emotion.values())
topic_names = [t for t,_ in topics[:8]][::-1]
topic_vals = [c for _,c in topics[:8]][::-1]

html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>原神TapTap用户评论分析报告</title>
<script src="https://cdn.bootcdn.net/ajax/libs/echarts/5.4.3/echarts.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f7fa;color:#333;line-height:1.6}
.container{max-width:1200px;margin:0 auto;padding:20px}
.header{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:40px;border-radius:12px;margin-bottom:24px}
.header h1{font-size:28px;margin-bottom:8px}
.header p{opacity:.9}
.section{background:white;border-radius:12px;padding:24px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.section h2{font-size:20px;margin-bottom:16px;border-left:4px solid #667eea;padding-left:12px}
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:20px}
.kpi{background:#f8f9ff;border-radius:8px;padding:16px;text-align:center}
.kpi .num{font-size:32px;font-weight:bold;color:#667eea}
.kpi .label{font-size:13px;color:#666;margin-top:4px}
.chart-row{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.chart-box{height:350px}
.topic-card{border:1px solid #eee;border-radius:8px;padding:16px;margin-bottom:12px}
.topic-card h3{font-size:16px;margin-bottom:8px}
.topic-stats{display:flex;gap:12px;margin-bottom:8px;font-size:13px}
.badge{padding:2px 8px;border-radius:4px;font-size:12px}
.badge.pos{background:#e6f7ed;color:#52c41a}
.badge.neu{background:#fff7e6;color:#faad14}
.badge.neg{background:#fff1f0;color:#f5222d}
details{margin:8px 0}
summary{cursor:pointer;color:#667eea;font-size:14px}
.comment-text{background:#fafafa;padding:12px;border-radius:6px;font-size:13px;margin-top:8px}
.action-item{display:flex;gap:12px;padding:12px;border-radius:8px;margin-bottom:8px}
.action-p0{background:#fff1f0;border-left:4px solid #f5222d}
.action-p1{background:#fff7e6;border-left:4px solid #faad14}
.action-p2{background:#e6f7ed;border-left:4px solid #52c41a}
.action-item .level{font-weight:bold;min-width:30px}
.pain-item{padding:8px 12px;background:#fff1f0;border-radius:6px;margin-bottom:6px;font-size:14px}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>原神TapTap用户评论分析报告</h1>
  <p>数据来源：TapTap原神评价页 · 有效评论''' + str(total) + '''条 · 平均评分''' + str(avg) + '''星 · AI智能分析</p>
</div>

<div class="section">
  <h2>分析概览</h2>
  <div class="kpi-row">
    <div class="kpi"><div class="num">''' + str(total) + '''</div><div class="label">有效评论</div></div>
    <div class="kpi"><div class="num">''' + str(avg) + '''</div><div class="label">平均评分</div></div>
    <div class="kpi"><div class="num">''' + str(int(pos_pct)) + '''%</div><div class="label">正面占比</div></div>
    <div class="kpi"><div class="num">''' + str(len(topics)) + '''</div><div class="label">覆盖主题</div></div>
  </div>
</div>

<div class="section">
  <h2>整体口碑分析</h2>
  <div class="chart-row">
    <div id="sentChart" class="chart-box"></div>
    <div id="emotionChart" class="chart-box"></div>
  </div>
</div>

<div class="section">
  <h2>主题深度分析</h2>
  <div id="topicChart" class="chart-box" style="height:400px"></div>
  ''' + topic_cards + '''
</div>

<div class="section">
  <h2>核心痛点TOP5</h2>
  ''' + pains_html + '''
</div>

<div class="section">
  <h2>优先级行动建议</h2>
  <div class="action-item action-p0"><div class="level">P0</div><div><strong>剧情跳过功能</strong><br><span style="color:#666">多条评论反馈剧情过长无法跳过，影响回归玩家体验。建议：优先上线剧情跳过选项。</span></div></div>
  <div class="action-item action-p1"><div class="level">P1</div><div><strong>抽卡体验优化</strong><br><span style="color:#666">歪率高、原石获取少是核心负面来源。建议：增加保底机制透明度，提升零氪玩家原石获取效率。</span></div></div>
  <div class="action-item action-p2"><div class="level">P2</div><div><strong>移动端适配</strong><br><span style="color:#666">低端机卡顿、发热、闪退问题。建议：优化低画质模式，提供更细的画质档位。</span></div></div>
</div>

<div class="section">
  <h2>核心结论</h2>
  <p>本次分析共覆盖<strong>''' + str(total) + '''</strong>条TapTap真实用户评论，平均评分<strong>''' + str(avg) + '''</strong>星。</p>
  <p style="margin-top:8px"><strong>整体口碑：</strong>正面占比''' + str(int(pos_pct)) + '''%，用户对游戏品质、开放世界、剧情角色整体认可。</p>
  <p style="margin-top:8px"><strong>主要痛点：</strong>剧情无法跳过、抽卡体验不佳、移动端优化是三大核心问题。</p>
  <p style="margin-top:8px"><strong>用户画像：</strong>老玩家占比高，对游戏有感情但对运营细节有不满；新手/回归玩家体验友好，但长草期留存是挑战。</p>
</div>

</div>
<script>
echarts.init(document.getElementById('sentChart')).setOption({
  title:{text:'情感分布',left:'center'},
  tooltip:{trigger:'item'},
  series:[{type:'pie',radius:'60%',data:[
    {value:''' + str(sent_pos) + ''',name:'正面',itemStyle:{color:'#52c41a'}},
    {value:''' + str(sent_neu) + ''',name:'中性',itemStyle:{color:'#faad14'}},
    {value:''' + str(sent_neg) + ''',name:'负面',itemStyle:{color:'#f5222d'}}
  ],label:{formatter:'{b}: {c} ({d}%)'}}]
});
echarts.init(document.getElementById('emotionChart')).setOption({
  title:{text:'情绪分布',left:'center'},
  tooltip:{trigger:'axis'},
  xAxis:{type:'category',data:''' + json.dumps(emo_keys, ensure_ascii=False) + '''},
  yAxis:{type:'value'},
  series:[{type:'bar',data:''' + json.dumps(emo_vals) + ''',itemStyle:{color:'#667eea'}}]
});
echarts.init(document.getElementById('topicChart')).setOption({
  title:{text:'主题热度TOP',left:'center'},
  tooltip:{trigger:'axis'},
  xAxis:{type:'value'},
  yAxis:{type:'category',data:''' + json.dumps(topic_names, ensure_ascii=False) + '''},
  series:[{type:'bar',data:''' + json.dumps(topic_vals) + ''',itemStyle:{color:'#764ba2'}}]
});
</script>
</body>
</html>'''

out = r'D:\AI用户反馈分析工作流\data\原神评论分析报告.html'
open(out,'w',encoding='utf-8').write(html)
print('报告已生成:', out)
