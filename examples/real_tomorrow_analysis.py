#!/usr/bin/env python3
"""
真实的黄金交易研究分析
使用免费API获取真实数据
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_real_gold_price():
    """从多个免费API获取真实金价"""
    print("🔄 正在从多个免费API获取真实金价...")
    
    results = {}
    
    # 1. xaus.com - 无需API Key
    try:
        resp = requests.get("https://xaus.com/api/v1/spot", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results['xaus'] = {
                'price': data.get('spot_usd_oz'),
                'per_gram': data.get('per_gram_usd'),
                'updated': data.get('updated_at'),
                'source': data.get('price_source', 'xaus.com')
            }
    except Exception as e:
        print(f"  ⚠️ xaus.com: {e}")
    
    # 2. aurumrates.com - 无需API Key, 50次/天
    try:
        resp = requests.get("https://aurumrates.com/api/v1/spot", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'ok':
                gold = data['data']['gold']
                results['aurumrates'] = {
                    'price': gold.get('price'),
                    'change_pct': gold.get('change_pct'),
                    'change_abs': gold.get('change_abs'),
                    'prev_close': gold.get('prev_close'),
                    'source': gold.get('source')
                }
    except Exception as e:
        print(f"  ⚠️ aurumrates.com: {e}")
    
    # 3. freegoldapi.com - CSV历史数据
    try:
        resp = requests.get("https://freegoldapi.com/data/latest.csv", timeout=15)
        if resp.status_code == 200:
            lines = resp.text.strip().split('\n')
            historical = []
            for line in lines[-100:]:  # 最近100条
                parts = line.split(',')
                if len(parts) >= 2 and parts[0].startswith('20'):
                    try:
                        date = parts[0]
                        price = float(parts[1])
                        historical.append({'date': date, 'price': price})
                    except:
                        pass
            results['freegoldapi'] = {
                'historical_count': len(historical),
                'latest': historical[-1] if historical else None,
                'history': historical
            }
    except Exception as e:
        print(f"  ⚠️ freegoldapi.com: {e}")
    
    return results


def get_real_news_gdelt():
    """从GDELT获取真实的黄金相关新闻"""
    print("\n🔄 正在从GDELT项目获取真实黄金新闻...")
    
    try:
        # GDELT 2.0 DOC API - 完全免费,无需Key
        # 查询最近15分钟关于gold的新闻
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            'query': '(gold OR "gold price" OR XAU) AND sourcelang:eng',
            'mode': 'ArtList',
            'maxrecords': 10,
            'format': 'json',
            'sort': 'datedesc'
        }
        
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            articles = data.get('articles', [])
            print(f"  ✅ 获取到 {len(articles)} 条真实新闻")
            return articles
    except Exception as e:
        print(f"  ⚠️ GDELT: {e}")
    return []


def calculate_technical_indicators_from_history(history):
    """从真实历史数据计算技术指标"""
    if not history or len(history) < 20:
        return None
    
    df = pd.DataFrame(history)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['close'] = df['price']
    
    # 计算技术指标
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma50'] = df['close'].rolling(50).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 波动率
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(20).std() * np.sqrt(252)
    
    # 价格变化
    latest = df.iloc[-1]
    changes = {}
    for days in [1, 5, 10, 20, 50]:
        if len(df) > days:
            change = (df['close'].iloc[-1] / df['close'].iloc[-days-1] - 1) * 100
            changes[f'{days}d'] = change
    
    return {
        'latest_price': latest['close'],
        'ma20': latest['ma20'],
        'ma50': latest['ma50'],
        'rsi': latest['rsi'],
        'volatility': latest['volatility'],
        'changes': changes,
        'data': df
    }


def get_real_economic_calendar():
    """从免费API获取真实经济日历"""
    print("\n🔄 正在获取真实经济日历...")
    
    events = []
    
    # Trading Economics - 有免费层 (但需要Key)
    # 这里使用其他来源
    try:
        # ForexFactory RSS
        resp = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                for event in data[:20]:
                    if 'gold' in event.get('title', '').lower() or \
                       event.get('impact') in ['High', 'Medium']:
                        events.append({
                            'title': event.get('title'),
                            'date': event.get('date'),
                            'time': event.get('time'),
                            'impact': event.get('impact'),
                            'forecast': event.get('forecast'),
                            'previous': event.get('previous'),
                            'currency': event.get('country', 'USD')
                        })
                print(f"  ✅ 获取到 {len(events)} 条真实经济事件")
    except Exception as e:
        print(f"  ⚠️ ForexFactory: {e}")
    
    return events


def main():
    print("=" * 70)
    print("📅 真实数据 - 明日黄金交易研究分析")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
    print("=" * 70)
    
    # 1. 获取真实金价
    print("\n" + "=" * 70)
    print("【第一步】真实金价数据 (来自多个免费API)")
    print("=" * 70)
    
    gold_data = get_real_gold_price()
    
    print("\n📊 黄金价格 (USD/oz):")
    prices = []
    for source, data in gold_data.items():
        if 'price' in data and data['price']:
            print(f"  • {source}: ${data['price']:.2f}/oz")
            prices.append(data['price'])
            if 'updated' in data:
                print(f"    更新时间: {data['updated']}")
            if 'change_pct' in data:
                print(f"    涨跌: {data['change_pct']:+.2f}% (${data['change_abs']:+.2f})")
            if 'prev_close' in data:
                print(f"    前收: ${data['prev_close']:.2f}")
    
    if prices:
        avg_price = sum(prices) / len(prices)
        print(f"\n  💰 平均价格: ${avg_price:.2f}/oz")
        print(f"  💰 每克: ${avg_price/31.1035:.2f}/g")
    else:
        print("  ❌ 无法获取金价")
        return
    
    # 2. 真实技术分析
    print("\n" + "=" * 70)
    print("【第二步】真实历史数据技术分析")
    print("=" * 70)
    
    if 'freegoldapi' in gold_data and gold_data['freegoldapi'].get('history'):
        history = gold_data['freegoldapi']['history']
        print(f"\n  数据源: freegoldapi.com (基于Yahoo Finance)")
        print(f"  历史数据: {len(history)} 条")
        
        tech = calculate_technical_indicators_from_history(history)
        if tech:
            print(f"\n  📈 技术指标 (基于真实历史):")
            print(f"    最新价: ${tech['latest_price']:.2f}")
            print(f"    MA20:   ${tech['ma20']:.2f}")
            print(f"    MA50:   ${tech['ma50']:.2f}")
            print(f"    RSI(14): {tech['rsi']:.2f}")
            print(f"    波动率:  {tech['volatility']*100:.2f}% (年化)")
            
            print(f"\n  📊 价格变化:")
            for period, change in tech['changes'].items():
                emoji = "📈" if change > 0 else "📉"
                print(f"    {emoji} {period}: {change:+.2f}%")
            
            # 判断趋势
            trend_signal = ""
            if tech['latest_price'] > tech['ma20'] > tech['ma50']:
                trend_signal = "强势上升趋势"
            elif tech['latest_price'] < tech['ma20'] < tech['ma50']:
                trend_signal = "强势下降趋势"
            elif tech['rsi'] > 70:
                trend_signal = "超买区域"
            elif tech['rsi'] < 30:
                trend_signal = "超卖区域"
            else:
                trend_signal = "震荡整理"
            print(f"\n  🎯 趋势判断: {trend_signal}")
    
    # 3. 真实新闻
    print("\n" + "=" * 70)
    print("【第三步】真实新闻分析 (来自GDELT)")
    print("=" * 70)
    
    news = get_real_news_gdelt()
    if news:
        print(f"\n  📰 最新 {len(news)} 条真实黄金相关新闻:")
        positive_keywords = ['surge', 'rise', 'gain', 'bullish', 'high', 'rally', 'boost', 'record', 'jump']
        negative_keywords = ['fall', 'drop', 'decline', 'plunge', 'bearish', 'low', 'crash', 'slump', 'tumble']
        
        sentiment_scores = []
        for i, article in enumerate(news[:10], 1):
            title = article.get('title', 'N/A')
            print(f"  {i}. {title[:120]}")
            
            # 简单情感分析
            title_lower = title.lower()
            score = 0
            for kw in positive_keywords:
                if kw in title_lower:
                    score += 0.2
            for kw in negative_keywords:
                if kw in title_lower:
                    score -= 0.2
            sentiment_scores.append(max(-1, min(1, score)))
        
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            print(f"\n  📊 新闻情绪综合: {avg_sentiment:+.2f}")
            if avg_sentiment > 0.2:
                print("     → 市场情绪: 看多")
            elif avg_sentiment < -0.2:
                print("     → 市场情绪: 看空")
            else:
                print("     → 市场情绪: 中性")
    
    # 4. 真实经济日历
    print("\n" + "=" * 70)
    print("【第四步】真实经济日历")
    print("=" * 70)
    
    events = get_real_economic_calendar()
    if events:
        print(f"\n  📅 即将到来的经济事件 ({len(events)} 条):")
        for event in events[:10]:
            impact_emoji = "🔴" if event.get('impact') == 'High' else "🟡" if event.get('impact') == 'Medium' else "🟢"
            print(f"    {impact_emoji} [{event.get('impact')}] {event.get('title')}")
            print(f"        日期: {event.get('date')} {event.get('time', '')}")
            if event.get('forecast'):
                print(f"        预期: {event['forecast']} | 前值: {event.get('previous', 'N/A')}")
    
    # 5. 综合分析
    print("\n" + "=" * 70)
    print("【第五步】综合交易建议")
    print("=" * 70)
    
    current_price = sum(prices) / len(prices) if prices else 0
    
    # 计算综合评分
    score = 0
    
    # 技术面
    if tech:
        if tech['rsi'] < 30:
            score += 0.5  # 超卖
        elif tech['rsi'] > 70:
            score -= 0.5  # 超买
        
        if tech['latest_price'] > tech['ma20']:
            score += 0.3
        else:
            score -= 0.3
    
    # 情绪面
    if 'avg_sentiment' in dir() and avg_sentiment:
        score += avg_sentiment * 0.5
    
    print(f"\n  🎯 综合评分: {score:+.2f}")
    print(f"  💰 当前价格: ${current_price:.2f}/oz")
    
    if score > 0.3:
        recommendation = "🟢 买入/做多"
        color = "GREEN"
    elif score < -0.3:
        recommendation = "🔴 卖出/做空"
        color = "RED"
    else:
        recommendation = "⚡ 观望/轻仓"
        color = "NEUTRAL"
    
    print(f"\n  ┌─────────────────────────────────────┐")
    print(f"  │ 建议: {recommendation}")
    print(f"  │ 评分: {score:+.2f}")
    print(f"  │ 价格: ${current_price:.2f}/oz")
    print(f"  └─────────────────────────────────────┘")
    
    if tech:
        # 关键价位
        atr = tech['latest_price'] * tech['volatility'] / np.sqrt(252)
        support = tech['ma20'] - atr
        resistance = tech['ma20'] + atr
        
        print(f"\n  📍 关键价位 (基于ATR):")
        print(f"     阻力: ${resistance:.2f}")
        print(f"     当前: ${current_price:.2f}")
        print(f"     支撑: ${support:.2f}")
        print(f"     ATR:  ${atr:.2f}")
    
    print("\n" + "=" * 70)
    print("✅ 报告完成 - 所有数据来自真实免费API")
    print("数据源: xaus.com, aurumrates.com, freegoldapi.com, GDELT")
    print("=" * 70)
    
    print(f"\n⚠️  风险提示:")
    print(f"  • 黄金市场波动大，请严格控制仓位")
    print(f"  • 建议止损不超过总资金的2%")
    print(f"  • 本分析仅供参考，不构成投资建议")
    print(f"  • 实际交易前请咨询专业投资顾问")


if __name__ == "__main__":
    main()