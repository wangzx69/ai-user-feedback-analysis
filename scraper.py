# -*- coding: utf-8 -*-
"""
TapTap 游戏评论采集脚本 - 精简版
改进：只采集玩家正文，不含回复/设备信息/用户名前缀，按用户名去重，目标200条
使用方法：在 Anaconda Prompt 中运行 python scraper.py
"""

import csv
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

# ===================== 配置区 =====================
TARGET_URL = "https://www.taptap.cn/app/168332/review"
MAX_REVIEWS = 200
OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "reviews_raw.csv"

# 页面内JS：精确提取每条评论的字段，只取玩家正文
EXTRACT_JS = r"""
() => {
    const userMap = new Map();

    function getText(el) {
        if (!el) return '';
        return (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
    }

    // 判断是否为评论容器
    function isReviewCard(el) {
        const text = getText(el);
        if (text.length < 30 || text.length > 5000) return false;
        // 必须有"玩过/想玩/在玩"或时间或设备信息
        const hasPlayed = /(玩过|想玩|在玩)/.test(text);
        const hasTime = /\d+\s*(小时|天|分钟)前/.test(text);
        const hasDevice = text.includes('来自');
        // 排除筛选栏
        const filterHits = ['全部评价','全部平台','带图','长评','游戏时长','好评','中评','差评']
            .filter(kw => text.includes(kw)).length;
        if (filterHits >= 2) return false;
        return (hasPlayed || hasTime || hasDevice) && text.length > 50;
    }

    // 向上找评论卡片容器
    function findCard(startEl, maxDepth) {
        let el = startEl;
        for (let i = 0; i < maxDepth && el && el !== document.body; i++) {
            if (isReviewCard(el)) return el;
            el = el.parentElement;
        }
        return null;
    }

    // 提取评分
    function getRating(card) {
        // 找星级元素
        const all = card.querySelectorAll('*');
        for (const el of all) {
            const t = getText(el);
            if (/^[★☆⭐]+$/.test(t) && t.length <= 5) {
                return (t.match(/[★⭐]/g) || []).length;
            }
        }
        // class含star-X
        for (const el of all) {
            const cls = el.className || '';
            if (typeof cls === 'string') {
                const m = cls.match(/(?:star|rating|score)[-_]?([1-5])\b/);
                if (m) return parseInt(m[1]);
            }
        }
        // style宽度百分比
        for (const el of all) {
            const st = el.getAttribute('style') || '';
            const m = st.match(/width:\s*(\d+)%/);
            if (m) {
                const pct = parseInt(m[1]);
                if (pct >= 20 && pct <= 100 && pct % 20 === 0) return pct / 20;
            }
        }
        return '';
    }

    // 提取用户名
    function getUsername(card) {
        const links = card.querySelectorAll('a');
        for (const a of links) {
            const t = getText(a);
            if (!t || t.length > 20 || t.length < 1) continue;
            if (['展开','收起','回复','举报','分享','更多','详情','攻略'].includes(t)) continue;
            if (t.includes('玩过') || t.includes('来自') || t.includes('http')) continue;
            if (t.includes('小时前') || t.includes('天前')) continue;
            return t;
        }
        // class含user/name
        const els = card.querySelectorAll('[class*="user"],[class*="name"],[class*="author"],[class*="nick"]');
        for (const el of els) {
            const t = getText(el);
            if (t && t.length <= 20 && !t.includes('玩过') && !t.includes('来自') && !t.includes('小时前')) {
                return t;
            }
        }
        return '';
    }

    // 提取评论正文——只取玩家自己写的，不含回复
    function getReviewText(card) {
        // 策略1：找class含content/text/body的元素
        let candidates = [];
        const contentEls = card.querySelectorAll('[class*="content"],[class*="text"],[class*="body"],[class*="detail"],p,span[class]');
        for (const el of contentEls) {
            const t = getText(el);
            if (t.length < 15) continue;
            if (t.includes('玩过') && t.length < 50) continue; // "玩过"标签太短
            if (t.startsWith('来自')) continue;
            if (/^\d+\s*(小时|天|分钟)前/.test(t)) continue;
            candidates.push(t);
        }
        candidates.sort((a, b) => b.length - a.length);

        for (let text of candidates) {
            // 切掉回复区：第一个"短用户名:"之后的全部不要
            // 回复通常格式："用户名 : 回复内容"
            text = text.replace(/([^\s，。！？,.!?：:]{1,12})\s*[:：]\s*[^\n]*$/, '');
            // 切掉时间/设备尾巴
            text = text.replace(/\d+\s*(小时|天|分钟)前[\s\S]*$/, '');
            text = text.replace(/修改于[\s\S]*$/, '');
            text = text.replace(/来自\s+[^\s]*[\s\S]*$/, '');
            // 去掉开头的"玩过/想玩/在玩"标签
            text = text.replace(/^(玩过|想玩|在玩)\s*/, '');
            // 去掉"展开全文/收起"按钮文字
            text = text.replace(/(展开全文|收起全文|展开|收起)$/, '').trim();
            // 去掉末尾纯数字（字数统计）
            text = text.replace(/\s*\d+\s*$/, '').trim();
            if (text.length >= 15) return text;
        }
        return '';
    }

    // 提取时间
    function getDate(card) {
        const t = getText(card);
        const m = t.match(/(\d+\s*(?:小时|天|分钟)前)/);
        return m ? m[1] : '';
    }

    // 提取设备
    function getDevice(card) {
        const t = getText(card);
        const m = t.match(/来自\s+([^\s,，。]+)/);
        return m ? m[1].trim() : '';
    }

    // ===== 定位评论卡片 =====
    const cards = new Set();

    // 策略1: 通过class定位
    try {
        const sel = '[class*="review-item"],[class*="comment-item"],[class*="feed-item"],[class*="post-item"],article[class]';
        for (const el of document.querySelectorAll(sel)) {
            if (isReviewCard(el)) cards.add(el);
        }
    } catch(e) {}

    // 策略2: 通过"来自"（设备信息）向上找卡片
    if (cards.size === 0) {
        try {
            for (const el of document.querySelectorAll('*')) {
                const t = getText(el);
                if (t.includes('来自') && t.length < 150 && el.children.length <= 8) {
                    const c = findCard(el, 15);
                    if (c) cards.add(c);
                }
            }
        } catch(e) {}
    }

    // 策略3: 通过时间向上找
    if (cards.size === 0) {
        try {
            for (const el of document.querySelectorAll('*')) {
                const t = getText(el);
                if (/\d+\s*(小时|天|分钟)前/.test(t) && t.length < 150 && el.children.length <= 8) {
                    const c = findCard(el, 15);
                    if (c) cards.add(c);
                }
            }
        } catch(e) {}
    }

    // 策略4: 通过"玩过"标签向上找
    if (cards.size === 0) {
        try {
            for (const el of document.querySelectorAll('*')) {
                const t = getText(el);
                if ((t === '玩过' || t === '想玩' || t === '在玩') && el.children.length <= 2) {
                    const c = findCard(el, 15);
                    if (c) cards.add(c);
                }
            }
        } catch(e) {}
    }

    // 无效评论过滤：自动丢掉乱码/键盘敲击/纯符号
    function isValidReview(text) {
        if (!text || text.length < 50) return false;
        // 连续重复字符>8个（如uuuuuuu、jjjjjjjjj）
        if (/(.)\1{8,}/.test(text)) return false;
        // 中文字符占比<50%
        const cn = (text.match(/[\u4e00-\u9fff]/g) || []).length;
        if (cn / text.length < 0.3) return false;
        // 词汇多样性太低（unique字/总字数 < 0.25）
        const chars = text.replace(/[^\u4e00-\u9fffa-zA-Z]/g, '');
        if (chars.length > 30) {
            const unique = new Set(chars).size;
            if (unique / chars.length < 0.25) return false;
        }
        return true;
    }

    // 处理每张卡片
    for (const card of cards) {
        const username = getUsername(card);
        const rating = getRating(card);
        const reviewText = getReviewText(card);
        const reviewDate = getDate(card);
        const device = getDevice(card);

        if (!reviewText || reviewText.length < 50) continue;
        // 无效评论过滤（乱码/键盘敲击/太短）
        if (!isValidReview(reviewText)) continue;
        // 正文不能就是用户名
        if (username && reviewText.replace(/\s/g,'') === username.replace(/\s/g,'')) continue;

        // 按用户名去重，保留更长的
        const key = username || reviewText.substring(0, 80);
        const existing = userMap.get(key);
        if (existing) {
            if (reviewText.length > existing.review_text.length) {
                existing.review_text = reviewText;
                if (rating) existing.rating = rating;
                if (reviewDate) existing.review_date = reviewDate;
                if (device) existing.device = device;
            }
        } else {
            userMap.set(key, {
                review_text: reviewText,
                rating: rating,
                username: username,
                review_date: reviewDate,
                device: device,
                source: 'TapTap',
                page_url: window.location.href,
                crawled_at: new Date().toLocaleString('zh-CN'),
            });
        }
    }

    return {
        reviews: Array.from(userMap.values()),
        card_count: cards.size,
    };
}
"""


def main():
    print("=" * 55)
    print("  TapTap 评论采集工具 - 精简版（200条不同用户）")
    print(f"  目标: {TARGET_URL}")
    print(f"  目标数量: {MAX_REVIEWS} 个不同用户")
    print("=" * 55)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_reviews = []
    seen_users = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--start-maximized",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        page = context.new_page()

        print(f"\n正在打开: {TARGET_URL}")
        page.goto(TARGET_URL, wait_until="load", timeout=60000)
        page.wait_for_timeout(3000)
        print(f"页面已加载: {page.title()}")

        print("\n" + "-" * 55)
        print("如果页面有弹窗或验证，请先手动处理。")
        input("准备好后按回车开始采集...")
        print("-" * 55 + "\n")

        no_change = 0
        last_count = 0
        round_num = 0

        while len(all_reviews) < MAX_REVIEWS and no_change < 15:
            round_num += 1

            # 页面存活检测
            try:
                _ = page.url
            except Exception:
                print(f"[第{round_num}轮] 页面关闭，重新打开...")
                try:
                    page = context.new_page()
                    page.goto(TARGET_URL, wait_until="load", timeout=60000)
                    page.wait_for_timeout(3000)
                except Exception:
                    print("  重新打开失败，保存已有数据退出")
                    break

            # 点击"展开"按钮获取全文
            try:
                for i in range(min(page.locator('text=展开').count(), 20)):
                    try:
                        btn = page.locator('text=展开').nth(i)
                        if btn.is_visible(timeout=300):
                            btn.click()
                            page.wait_for_timeout(200)
                    except Exception:
                        continue
            except Exception:
                pass

            page.wait_for_timeout(1500)

            # JS提取
            try:
                result = page.evaluate(EXTRACT_JS)
                dom_reviews = result.get("reviews", [])
                new_count = 0
                for r in dom_reviews:
                    uname = r.get("username", "").strip()
                    text = r.get("review_text", "").strip()
                    if not text or len(text) < 15:
                        continue
                    if uname:
                        if uname not in seen_users:
                            seen_users.add(uname)
                            all_reviews.append(r)
                            new_count += 1
                        else:
                            # 用更长的替换
                            for i, ex in enumerate(all_reviews):
                                if ex.get("username") == uname:
                                    if len(text) > len(ex.get("review_text", "")):
                                        all_reviews[i] = r
                                    break
                    else:
                        # 无用户名的用正文前80字去重
                        dedup_key = text[:80]
                        if dedup_key not in seen_users:
                            seen_users.add(dedup_key)
                            all_reviews.append(r)
                            new_count += 1

                print(f"[第{round_num}轮] 提取{len(dom_reviews)}条，新增{new_count}，累计{len(all_reviews)}个不同用户")
            except Exception as e:
                print(f"[第{round_num}轮] 提取出错: {type(e).__name__}: {e}")

            # 判断是否卡住
            if len(all_reviews) == last_count:
                no_change += 1
                print(f"  无新增 ({no_change}/15)")
            else:
                no_change = 0
            last_count = len(all_reviews)

            if len(all_reviews) >= MAX_REVIEWS:
                break

            # 滚动加载
            try:
                page.mouse.move(720, 500)
                page.wait_for_timeout(200)
                for _ in range(5):
                    page.mouse.wheel(0, 3000)
                    page.wait_for_timeout(400)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1500)
                # 滚动到最后一条评论
                page.evaluate("""
                    const items = document.querySelectorAll('[class*="review"],[class*="comment"],article');
                    if (items.length > 0) items[items.length-1].scrollIntoView({block:'end'});
                """)
                page.wait_for_timeout(2000)
            except Exception:
                continue

            time.sleep(1)

        browser.close()

    # 最终去重
    final = []
    final_users = set()
    for r in all_reviews:
        u = r.get("username", "").strip()
        t = r.get("review_text", "").strip()
        if not t or len(t) < 15:
            continue
        key = u if u else t[:80]
        if key not in final_users:
            final_users.add(key)
            final.append(r)

    # 取前MAX_REVIEWS条
    final = final[:MAX_REVIEWS]

    if not final:
        print("\n⚠ 未采集到评论！请检查网络或手动处理验证后重试。")
        return

    # 保存CSV
    fieldnames = ["review_text", "rating", "username", "review_date", "device", "source", "page_url", "crawled_at"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final)

    print(f"\n✅ 采集完成！共 {len(final)} 条不同用户的评论")
    print(f"  保存: {OUTPUT_FILE.resolve()}")
    rated = [r for r in final if r.get("rating")]
    has_user = [r for r in final if r.get("username")]
    has_date = [r for r in final if r.get("review_date")]
    print(f"\n数据概览：")
    print(f"  有评分: {len(rated)} 条")
    print(f"  有用户名: {len(has_user)} 条")
    print(f"  有时间: {len(has_date)} 条")
    # 正文质量抽查
    bad = [r for r in final if "玩过" in r.get("review_text", "")[:20]]
    print(f"  正文含'玩过'前缀: {len(bad)} 条（应为0）")


if __name__ == "__main__":
    main()

