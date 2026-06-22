#!/usr/bin/env python3
"""
黄金交易综合分析 - 集成 newsdata.io 新闻API
"""

import requests
from datetime import datetime


class GoldAnalyzer:
    def __init__(self):
        self.NEWSDATA_API_KEY = "pub_a5a5a4284b084fdf82a37a88766f679f"
        self.MARKETAUX_API_KEY = "7yd3GosRCb0clYEHvLnFC6Owaao9t6fQYKwAfUjf"
        self.real_time_price = None
        self.economic_events = []
        self.news = []
        self.sentiment_score = 0
    
    def fetch_real_time_price(self):
        data = {}
        
        try:
            resp = requests.get("https://api.gold-api.com/price/XAU/USD", timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                data['gold_api'] = {
                    'price': d['price'],
                    'updated_at': d['updatedAt'],
                    'updated_readable': d['updatedAtReadable'],
                    'source': 'gold-api.com'
                }
        except Exception as e:
            print(f"⚠️ gold-api.com错误: {e}")
        
        try:
            resp = requests.get("https://aurumrates.com/api/v1/spot", timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                if d.get('status') == 'ok':
                    gold = d['data']['gold']
                    data['aurumrates'] = {
                        'price': gold['price'],
                        'change_pct': gold['change_pct'],
                        'change_abs': gold['change_abs'],
                        'prev_close': gold['prev_close'],
                        'source': 'aurumrates'
                    }
        except Exception as e:
            print(f"⚠️ aurumrates错误: {e}")
        
        self.real_time_price = data
        return data
    
    def fetch_economic_calendar(self):
        events = []
        try:
            resp = requests.get(
                "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for event in data[:20]:
                        events.append({
                            'title': event.get('title'),
                            'date': event.get('date'),
                            'time': event.get('time'),
                            'impact': event.get('impact'),
                            'forecast': event.get('forecast'),
                            'previous': event.get('previous'),
                            'currency': event.get('country', 'USD')
                        })
        except Exception as e:
            print(f"⚠️ 经济日历错误: {e}")
        
        self.economic_events = events
        return events
    
    def fetch_news(self):
        """使用 newsdata.io 获取黄金相关新闻"""
        news = []
        seen_titles = set()
        
        # newsdata.io 搜索
        try:
            url = "https://newsdata.io/api/1/news"
            params = {
                'apikey': self.NEWSDATA_API_KEY,
                'q': 'gold OR XAU OR precious metal OR gold price',
                'language': 'en',
                'category': 'business',
                'size': 10
            }
            
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                d = resp.json()
                if d.get('status') == 'success':
                    for item in d.get('results', []):
                        title = item.get('title', '')
                        if title in seen_titles:
                            continue
                        
                        seen_titles.add(title)
                        news.append({
                            'title': title,
                            'description': item.get('description', ''),
                            'source': item.get('source_name', 'Unknown'),
                            'published_at': item.get('pubDate', ''),
                            'link': item.get('link', ''),
                            'category': item.get('category', [])
                        })
        except Exception as e:
            print(f"⚠️ newsdata.io错误: {e}")
        
        # 如果newsdata.io返回太少，用MarketAux补充
        if len(news) < 5:
            try:
                url = "https://api.marketaux.com/v1/news/all"
                params = {
                    'api_token': self.MARKETAUX_API_KEY,
                    'keywords': 'gold price',
                    'language': 'en',
                    'limit': 5
                }
                
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    d = resp.json()
                    for item in d.get('data', []):
                        title = item.get('title', '')
                        if title in seen_titles:
                            continue
                        
                        seen_titles.add(title)
                        news.append({
                            'title': title,
                            'description': item.get('description', ''),
                            'source': item.get('source', 'Unknown'),
                            'published_at': item.get('published_at', '')
                        })
            except Exception as e:
                print(f"⚠️ MarketAux错误: {e}")
        
        self.news = news[:8]
        return self.news
    
    def analyze_sentiment(self):
        if not self.news:
            return 0
        
        positive_keywords = ['surge', 'rise', 'gain', 'bullish', 'high', 'rally', 'boost', 'record', 'jump', 'up', 'increase', 'strong', 'positive', 'upbeat', 'optimistic', 'soar', 'climb', 'advance', 'recovery', 'higher', 'strengthen', 'rebound']
        negative_keywords = ['fall', 'drop', 'decline', 'plunge', 'bearish', 'low', 'crash', 'slump', 'tumble', 'down', 'decrease', 'weak', 'negative', 'worried', 'pessimistic', 'plummet', 'slip', 'loss', 'dip', 'lower', 'weaken', 'slide']
        
        scores = []
        for article in self.news:
            text = (article.get('title', '') + ' ' + article.get('description', '')).lower()
            score = 0
            
            for kw in positive_keywords:
                if kw in text:
                    score += 0.15
            for kw in negative_keywords:
                if kw in text:
                    score -= 0.15
            
            scores.append(max(-1, min(1, score)))
        
        avg_score = sum(scores) / len(scores) if scores else 0
        self.sentiment_score = avg_score
        return avg_score
    
    def analyze_events(self):
        high_impact = [e for e in self.economic_events if e.get('impact') == 'High']
        medium_impact = [e for e in self.economic_events if e.get('impact') == 'Medium']
        
        event_score = 0
        
        for event in high_impact:
            title = event.get('title', '').lower()
            if 'fed' in title or 'interest rate' in title:
                event_score += 0.3
            if 'cpi' in title or 'inflation' in title:
                event_score += 0.25
            if 'payroll' in title or 'unemployment' in title:
                event_score += 0.2
        
        return {
            'high_count': len(high_impact),
            'medium_count': len(medium_impact),
            'events': high_impact + medium_impact[:5],
            'score': min(event_score, 1.0)
        }
    
    def analyze_technical(self):
        if not self.real_time_price:
            return None
        
        prices = []
        sources = ['gold_api', 'aurumrates']
        
        for source in sources:
            if source in self.real_time_price:
                prices.append(self.real_time_price[source]['price'])
        
        if not prices:
            return None
        
        avg_price = sum(prices) / len(prices)
        change_pct = 0
        
        if 'aurumrates' in self.real_time_price:
            change_pct = self.real_time_price['aurumrates']['change_pct']
        
        tech_score = 0
        if change_pct < -1:
            tech_score -= 0.4
        elif change_pct > 1:
            tech_score += 0.4
        
        if change_pct < -0.5:
            tech_score -= 0.2
        elif change_pct > 0.5:
            tech_score += 0.2
        
        return {
            'price': avg_price,
            'change_pct': change_pct,
            'score': tech_score,
            'trend': '下跌' if change_pct < -0.5 else '上涨' if change_pct > 0.5 else '震荡'
        }
    
    def analyze_game_theory(self):
        events = self.analyze_events()
        analysis = {}
        
        if self.sentiment_score > 0.3:
            analysis['herding_risk'] = '高'
            analysis['herding_score'] = -0.3
            analysis['herding_desc'] = '市场情绪过于乐观，可能存在羊群效应'
        elif self.sentiment_score < -0.3:
            analysis['herding_risk'] = '高'
            analysis['herding_score'] = 0.3
            analysis['herding_desc'] = '市场情绪过于悲观，可能存在逆向机会'
        else:
            analysis['herding_risk'] = '低'
            analysis['herding_score'] = 0
            analysis['herding_desc'] = '市场情绪中性，无明显羊群效应'
        
        if events['high_count'] >= 2:
            analysis['volatility_risk'] = '高'
            analysis['volatility_score'] = -0.2
            analysis['volatility_desc'] = '多个高影响事件，波动率可能上升'
        else:
            analysis['volatility_risk'] = '低'
            analysis['volatility_score'] = 0
            analysis['volatility_desc'] = '事件影响有限'
        
        analysis['total_score'] = analysis['herding_score'] + analysis['volatility_score']
        return analysis
    
    def get_comprehensive_score(self):
        event_analysis = self.analyze_events()
        tech_analysis = self.analyze_technical()
        sentiment = self.sentiment_score
        game_analysis = self.analyze_game_theory()
        
        weights = {
            'event': 0.30,
            'sentiment': 0.20,
            'technical': 0.35,
            'game_theory': 0.15
        }
        
        total_score = (
            event_analysis['score'] * weights['event'] +
            sentiment * weights['sentiment'] +
            (tech_analysis['score'] if tech_analysis else 0) * weights['technical'] +
            game_analysis['total_score'] * weights['game_theory']
        )
        
        return total_score


def main():
    print("=" * 70)
    print("📅 黄金综合分析 (集成 newsdata.io)")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 70)
    
    analyzer = GoldAnalyzer()
    
    print("\n【一】实时金价数据")
    print("-" * 70)
    data = analyzer.fetch_real_time_price()
    
    if 'gold_api' in data:
        d = data['gold_api']
        print(f"💰 gold-api.com: ${d['price']:.2f}/oz (更新: {d['updated_readable']})")
    
    if 'aurumrates' in data:
        d = data['aurumrates']
        print(f"💰 aurumrates: ${d['price']:.2f}/oz ({d['change_pct']:+.2f}%)")
    
    print("\n【二】事件分析")
    print("-" * 70)
    analyzer.fetch_economic_calendar()
    events = analyzer.analyze_events()
    
    print(f"\n📅 今日事件: {events['high_count']}个高影响, {events['medium_count']}个中影响")
    print(f"📊 事件评分: {events['score']:.2f}")
    
    print("\n【三】情绪分析")
    print("-" * 70)
    news = analyzer.fetch_news()
    sentiment = analyzer.analyze_sentiment()
    
    print(f"\n📰 新闻数量: {len(news)} 条")
    print(f"📊 情绪综合评分: {sentiment:+.2f}")
    
    if sentiment > 0.2:
        print("   → 市场情绪: 🟢 看多")
    elif sentiment < -0.2:
        print("   → 市场情绪: 🔴 看空")
    else:
        print("   → 市场情绪: ⚡ 中性")
    
    if news:
        print("\n🎯 新闻摘要:")
        for i, article in enumerate(news[:5], 1):
            title = article.get('title', 'N/A')
            source = article.get('source', 'Unknown')
            time = article.get('published_at', '')[:19] if article.get('published_at') else ''
            print(f"\n  {i}. [{source}] {title[:70]}...")
            if time:
                print(f"      发布: {time}")
            if article.get('description'):
                desc = article['description'][:100]
                print(f"      摘要: {desc}...")
    
    print("\n【四】技术分析")
    print("-" * 70)
    tech = analyzer.analyze_technical()
    
    if tech:
        print(f"\n💰 当前价格: ${tech['price']:.2f}/oz")
        print(f"📈 当日涨跌: {tech['change_pct']:+.2f}%")
        print(f"🎯 趋势: {tech['trend']}")
    
    print("\n【五】博弈分析")
    print("-" * 70)
    game = analyzer.analyze_game_theory()
    print(f"\n🐑 羊群效应风险: {game['herding_risk']}")
    print(f"   分析: {game['herding_desc']}")
    print(f"\n📊 波动率风险: {game['volatility_risk']}")
    print(f"   分析: {game['volatility_desc']}")
    
    print("\n【六】综合建议")
    print("-" * 70)
    total_score = analyzer.get_comprehensive_score()
    
    print(f"\n🎯 综合评分: {total_score:+.2f}")
    
    if total_score > 0.3:
        recommendation = "🟢 买入/做多"
        confidence = "高"
    elif total_score < -0.3:
        recommendation = "🔴 卖出/做空"
        confidence = "高"
    elif total_score > 0:
        recommendation = "🟡 谨慎看多"
        confidence = "中等"
    elif total_score < 0:
        recommendation = "🟡 谨慎看空"
        confidence = "中等"
    else:
        recommendation = "⚡ 观望/轻仓"
        confidence = "低"
    
    print(f"\n📋 交易建议: {recommendation}")
    print(f"💯 置信度: {confidence}")
    
    print("\n" + "=" * 70)
    print("✅ 分析完成")
    print("=" * 70)


if __name__ == "__main__":
    main()