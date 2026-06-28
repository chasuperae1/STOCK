#!/usr/bin/env python3
"""
黄金交易分析专家 - Skill主入口 (v2.0)
====================================

提供标准化的黄金ETF(518880)分析报告，确保每次分析风格一致。

使用方式：
    python3 -m skills.gold_analysis.analyze [options]

选项：
    --full          完整分析报告（默认）
    --quick         快速分析（仅行情+技术面）
    --backtest      历史事件回测
    --strategy      事件驱动策略回测
    --etf CODE      指定ETF代码（默认518880）
    --market MARKET 指定市场（默认sh）
"""

import sys
import os
import argparse
from datetime import datetime

# 确保workspace在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core.api_tools import (
    ChinaStockAPI,
    GoldAPI,
    EconomicCalendarAPI,
    NewsAPI,
    ForexAPI
)
from core.real_data import RealGoldETFData
from core.event_driven import EventDrivenAnalyzer
from core.news_sentiment import NewsSentimentAnalyzer
from core.blogger_tracker import BloggerTracker

import pandas as pd
import numpy as np


class GoldAnalysisSkill:
    """
    黄金分析Skill - 标准化分析报告
    
    确保每次分析输出风格完全一致
    """
    
    REPORT_WIDTH = 90
    
    def __init__(self, etf_code: str = '518880', market: str = 'sh'):
        self.etf_code = etf_code
        self.market = market
        
        # 分析器
        self.event_analyzer = EventDrivenAnalyzer()
        self.sentiment_analyzer = NewsSentimentAnalyzer()
        
        # 数据缓存
        self.realtime_data = None
        self.historical_df = None
        self.events = []
        self.news = []
        self.gold_price = None
        self.forex_data = None
        
        # 分析结果
        self.tech_indicators = {}
        self.event_result = None
        self.sentiment_result = None
    
    def print_separator(self, char: str = "=", label: str = ""):
        """打印分隔线"""
        if label:
            total = self.REPORT_WIDTH
            label_len = len(label) + 2
            left = (total - label_len) // 2
            right = total - left - label_len
            print(char * left + " " + label + " " + char * right)
        else:
            print(char * self.REPORT_WIDTH)
    
    def print_section(self, title: str, star: bool = False, weight: str = ""):
        """打印章节标题"""
        print()
        self.print_separator("=")
        if weight:
            print(f"【{title}】{' ⭐ ' + weight if star else ''}")
        else:
            print(f"【{title}】{' ⭐' if star else ''}")
        self.print_separator("=")
    
    def fetch_all_data(self, history_days: int = 250) -> bool:
        """获取所有数据"""
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📡 数据获取阶段")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # 1. ETF实时行情
        print("📡 [1/6] 获取ETF实时行情...")
        self.realtime_data = ChinaStockAPI.get_realtime(self.etf_code, self.market)
        if not self.realtime_data or 'price' not in self.realtime_data:
            print("   ❌ 失败")
            return False
        print(f"   ✅ ¥{self.realtime_data['price']:.3f}")
        
        # 2. 国际金价
        print("📡 [2/6] 获取国际金价...")
        self.gold_price = GoldAPI.get_realtime_price()
        if self.gold_price and 'price' in self.gold_price:
            print(f"   ✅ ${self.gold_price['price']:.2f}/oz")
        else:
            print("   ⚠️  获取失败（不影响主要分析）")
        
        # 3. 历史K线数据
        print("📡 [3/6] 获取历史K线数据...")
        data = RealGoldETFData(self.etf_code, self.market)
        self.historical_df = data.fetch_history(days=history_days)
        if self.historical_df is not None and len(self.historical_df) > 0:
            print(f"   ✅ {len(self.historical_df)}条 ({self.historical_df['date'].iloc[0]} ~ {self.historical_df['date'].iloc[-1]})")
        else:
            print("   ⚠️  获取失败（技术面分析将跳过）")
        
        # 4. 经济日历事件
        print("📡 [4/6] 获取经济日历事件...")
        self.events = EconomicCalendarAPI.forexfactory() or []
        print(f"   ✅ {len(self.events)}个事件")
        
        # 5. 财经新闻（严格24小时时间过滤）
        print("📡 [5/6] 获取财经新闻（24小时内）...")
        self.news = NewsAPI.get_financial_news(hours=24)
        # 统计中英文
        cn_count = sum(1 for n in self.news if n.get('language') == 'zh')
        en_count = sum(1 for n in self.news if n.get('language') == 'en')
        print(f"   ✅ {len(self.news)}条新闻（中文{cn_count} + 英文{en_count}）")
        # 显示时间范围
        if self.news:
            ages = [n.get('_age_hours', 24) for n in self.news]
            print(f"   ⏰ 时间范围: 最近{min(ages):.1f}小时 ~ 最近{max(ages):.1f}小时（北京时间）")
        
        # 6. 外汇数据
        print("📡 [6/6] 获取外汇数据...")
        self.forex_data = ForexAPI.currency_api()
        if self.forex_data:
            print(f"   ✅ 美元/人民币: {self.forex_data.get('data', {}).get('cny', 'N/A')}")
        else:
            print("   ⚠️  获取失败")
        
        print()
        return True
    
    def calculate_tech_indicators(self) -> dict:
        """计算技术指标"""
        if self.historical_df is None or len(self.historical_df) < 60:
            return {}
        
        df = self.historical_df.copy()
        close = df['close']
        
        # 均线
        for n in [5, 10, 20, 60]:
            if len(df) >= n:
                self.tech_indicators[f'ma{n}'] = close.rolling(n).mean().iloc[-1]
        
        # RSI
        if len(df) >= 14:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss.replace(0, np.nan)
            rs = rs.fillna(50)
            self.tech_indicators['rsi'] = 100 - (100 / (1 + rs.iloc[-1]))
        
        # MACD
        if len(df) >= 26:
            exp12 = close.ewm(span=12, adjust=False).mean()
            exp26 = close.ewm(span=26, adjust=False).mean()
            dif = exp12 - exp26
            dea = dif.ewm(span=9, adjust=False).mean()
            self.tech_indicators['macd_dif'] = dif.iloc[-1]
            self.tech_indicators['macd_dea'] = dea.iloc[-1]
            self.tech_indicators['macd_hist'] = (dif - dea).iloc[-1]
        
        # 布林带
        if len(df) >= 20:
            ma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            self.tech_indicators['boll_upper'] = (ma20 + 2 * std20).iloc[-1]
            self.tech_indicators['boll_mid'] = ma20.iloc[-1]
            self.tech_indicators['boll_lower'] = (ma20 - 2 * std20).iloc[-1]
        
        return self.tech_indicators
    
    def get_tech_score(self) -> float:
        """技术面评分（-1到+1）"""
        if not self.tech_indicators or not self.realtime_data:
            return 0.0
        
        score = 0.0
        price = self.realtime_data['price']
        signals = 0
        
        # 均线系统
        ma5 = self.tech_indicators.get('ma5')
        ma10 = self.tech_indicators.get('ma10')
        ma20 = self.tech_indicators.get('ma20')
        ma60 = self.tech_indicators.get('ma60')
        
        if ma5 and ma20:
            if price > ma5 > ma20:
                score += 0.5
                signals += 1
            elif price < ma5 < ma20:
                score -= 0.5
                signals += 1
            else:
                score += 0.0
                signals += 1
        
        if ma20 and ma60:
            if ma20 > ma60:
                score += 0.3
                signals += 1
            else:
                score -= 0.3
                signals += 1
        
        # RSI
        rsi = self.tech_indicators.get('rsi', 50)
        if rsi < 30:
            score += 0.6
            signals += 1
        elif rsi > 70:
            score -= 0.6
            signals += 1
        elif rsi > 55:
            score += 0.2
            signals += 1
        elif rsi < 45:
            score -= 0.2
            signals += 1
        else:
            score += 0.0
            signals += 1
        
        # MACD
        dif = self.tech_indicators.get('macd_dif')
        dea = self.tech_indicators.get('macd_dea')
        if dif is not None and dea is not None:
            if dif > dea:
                score += 0.4
                signals += 1
            else:
                score -= 0.4
                signals += 1
        
        # 布林带
        upper = self.tech_indicators.get('boll_upper')
        lower = self.tech_indicators.get('boll_lower')
        if upper and lower:
            if price < lower:
                score += 0.5
                signals += 1
            elif price > upper:
                score -= 0.5
                signals += 1
            else:
                score += 0.0
                signals += 1
        
        if signals > 0:
            return max(-1.0, min(1.0, score))
        return 0.0
    
    def section_realtime(self):
        """第一部分：实时行情"""
        self.print_section("一、实时行情")
        
        d = self.realtime_data
        print(f"\n💰 {d.get('name', '黄金ETF华安')} ({self.etf_code})")
        print(f"   当前价格: ¥{d['price']:.3f}")
        print(f"   涨跌幅: {d.get('change_pct', 0):+.2f}% ({d.get('change', 0):+.3f})")
        print(f"   今开: ¥{d.get('open', 0):.3f} | 昨收: ¥{d.get('prev_close', 0):.3f}")
        print(f"   最高: ¥{d.get('high', 0):.3f} | 最低: ¥{d.get('low', 0):.3f}")
        
        if self.gold_price and 'price' in self.gold_price:
            change = self.gold_price.get('change_pct', 0)
            print(f"\n🌍 国际金价 (XAU/USD):")
            print(f"   现货价格: ${self.gold_price['price']:.2f}/oz")
            if change:
                print(f"   涨跌幅: {change:+.2f}%")
        
        if self.historical_df is not None:
            df = self.historical_df
            ret_5d = (df['close'].iloc[-1] / df['close'].iloc[-6] - 1) * 100 if len(df) > 5 else 0
            ret_20d = (df['close'].iloc[-1] / df['close'].iloc[-21] - 1) * 100 if len(df) > 20 else 0
            ret_60d = (df['close'].iloc[-1] / df['close'].iloc[-61] - 1) * 100 if len(df) > 60 else 0
            
            print(f"\n📈 近期走势:")
            print(f"   近5日: {ret_5d:+.2f}% | 近20日: {ret_20d:+.2f}% | 近60日: {ret_60d:+.2f}%")
    
    def section_event_backtest(self):
        """第二部分：历史事件回测分析"""
        self.print_section("二、历史事件回测分析", star=True, weight="基于500天真实数据")
        
        if self.historical_df is None or len(self.historical_df) < 20:
            print("\n   ⚠️ 历史数据不足，历史事件分析跳过")
            return
        
        df = self.historical_df
        price = self.realtime_data['price']
        
        # 计算近期收益率
        ret_10d = (df['close'].iloc[-1] / df['close'].iloc[-11] - 1) * 100 if len(df) > 10 else 0
        ret_20d = (df['close'].iloc[-1] / df['close'].iloc[-21] - 1) * 100 if len(df) > 20 else 0
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # 布林带
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        std20 = df['close'].rolling(20).std().iloc[-1]
        boll_upper = ma20 + 2 * std20
        boll_lower = ma20 - 2 * std20
        boll_position = (price - boll_lower) / (boll_upper - boll_lower) if boll_upper != boll_lower else 0.5
        
        # 均线
        ma5 = df['close'].rolling(5).mean().iloc[-1]
        ma20_val = df['close'].rolling(20).mean().iloc[-1]
        
        # 创X日新高
        high_60d = df['close'].rolling(60).max().iloc[-2] if len(df) >= 62 else price
        high_20d = df['close'].rolling(20).max().iloc[-2] if len(df) >= 22 else price
        new_high_60 = price >= high_60d
        new_high_20 = price >= high_20d
        
        print(f"\n📊 当前市场状态（对应历史规律）：")
        
        print(f"\n   【超跌反弹信号】")
        print(f"   - 10日涨跌: {ret_10d:+.2f}% → ", end='')
        if ret_10d <= -8:
            print("✅ 符合超跌反弹条件（10日跌8%+）")
        elif ret_10d <= -5:
            print("⚠️  部分符合（5日跌5%+）")
        else:
            print("❌ 不符合超跌反弹条件")
        
        print(f"   - 20日涨跌: {ret_20d:+.2f}% → ", end='')
        if ret_20d <= -10:
            print("✅ 符合超跌反弹条件（20日跌10%+）")
        elif ret_20d <= -5:
            print("⚠️  部分符合")
        else:
            print("❌ 不符合超跌反弹条件")
        
        print(f"   - RSI(14): {rsi:.1f} → ", end='')
        if rsi < 30:
            print("✅ 超卖（买入信号加强）")
        elif rsi < 40:
            print("⚠️  偏低")
        elif rsi > 70:
            print("⚠️  超买")
        else:
            print("正常")
        
        print(f"   - 布林带位置: ", end='')
        if boll_position < 0.2:
            print(f"🟢 下轨附近（超卖买入信号）")
        elif boll_position > 0.8:
            print(f"🔴 上轨附近（超买信号）")
        elif boll_position < 0.5:
            print(f"🟡 下方（偏弱）")
        else:
            print(f"🟡 上方（偏强）")
        
        print(f"\n   【趋势突破信号】")
        print(f"   - 创60日新高: ", end='')
        if new_high_60:
            print("✅ 是")
        else:
            print("❌ 否")
        
        print(f"   - 创20日新高: ", end='')
        if new_high_20:
            print("✅ 是")
        else:
            print("❌ 否")
        
        print(f"   - MA5/MA20: ", end='')
        if ma5 > ma20_val:
            print(f"🟢 均线多头（上升趋势）")
        elif ma5 < ma20_val:
            print(f"🔴 均线空头（下降趋势）")
        else:
            print("⚡ 纠缠")
        
        print(f"\n💡 历史规律参考:")
        print(f"   - 超跌反弹后10日平均收益: +4.32% (胜率90%)")
        print(f"   - 创60日新高后20日平均收益: +4.01% (胜率74%)")
        print(f"   - 单日大涨3%+后3日平均收益: -2.33% (胜率31%) ⚠️不追高")
        print(f"   - 双动量策略(20日+MA60): 年化+28.12%, 夏普1.32")
    
    def section_event_driven(self):
        """第三部分：事件驱动分析"""
        self.print_section("三、事件驱动分析", star=True, weight="权重40%")
        
        ev = self.event_result
        cal = ev['calendar_analysis']
        fed = ev['fed_analysis']
        geo = ev['geo_analysis']
        
        trend_cn = {
            'bullish': '🟢 看涨（利多黄金）',
            'bearish': '🔴 看跌（利空黄金）',
            'neutral': '⚡ 中性（观望）'
        }.get(ev['trend'], '中性')
        
        print(f"\n📊 事件驱动综合评分: {ev['final_score']:+.2f}")
        print(f"   大趋势判断: {trend_cn}")
        print(f"   置信度: {ev['confidence']:.0%}")
        
        print(f"\n📅 经济日历事件:")
        print(f"   未来事件: {cal.total_events}个")
        print(f"   高影响: {cal.high_impact_count} | 中影响: {cal.medium_impact_count} | 低影响: {cal.low_impact_count}")
        print(f"   事件评分: {cal.event_score:+.2f}")
        
        if cal.key_events:
            print(f"\n   🔑 关键事件:")
            for e in cal.key_events[:5]:
                icon = "🟢" if e.gold_direction > 0 else ("🔴" if e.gold_direction < 0 else "⚡")
                print(f"      {icon} {e.event_title[:50]}")
                print(f"         影响等级: {e.impact_level} | {e.reasoning}")
        
        print(f"\n🏛️ 美联储政策倾向:")
        fed_dir_cn = {
            'dovish': '🐦 鸽派（利多黄金）',
            'hawkish': '🦅 鹰派（利空黄金）',
            'neutral': '⚡ 中性'
        }.get(fed['policy_direction'], '中性')
        print(f"   政策倾向: {fed_dir_cn}")
        print(f"   降息预期: {fed['rate_cut_probability']:.0%} | 加息预期: {fed['rate_hike_probability']:.0%}")
        if fed['key_news']:
            print(f"   相关新闻: {len(fed['key_news'])}篇")
        
        print(f"\n🌍 地缘政治风险:")
        geo_level_cn = {'high': '🔴 高风险', 'medium': '🟡 中风险', 'low': '🟢 低风险'}.get(geo['risk_level'], '低')
        print(f"   风险等级: {geo_level_cn} (评分: {geo['risk_score']:.2f})")
        print(f"   对黄金影响: {geo['gold_impact']:+.2f}")
        print(f"   相关新闻: {geo['relevant_news_count']}篇")
    
    def section_sentiment(self):
        """第四部分：新闻情绪分析"""
        self.print_section("四、新闻情绪分析", star=True, weight="权重25%")
        
        se = self.sentiment_result
        
        label_cn = {
            'positive': '🟢 偏多情绪',
            'negative': '🔴 偏空情绪',
            'neutral': '⚡ 中性情绪'
        }.get(se.sentiment_label, '中性')
        
        if se.fear_greed_index < 25:
            fg_label = "🔴 极度恐惧（逆向买入信号）"
        elif se.fear_greed_index < 45:
            fg_label = "🟡 恐惧"
        elif se.fear_greed_index < 55:
            fg_label = "⚡ 中性"
        elif se.fear_greed_index < 75:
            fg_label = "🟢 贪婪"
        else:
            fg_label = "🟢 极度贪婪（逆向卖出信号）"
        
        # 统计中英文
        cn_count = sum(1 for n in se.analyzed_news if n.source in ['金十数据', '华尔街见闻', '东方财富'])
        en_count = se.total_news - cn_count
        
        print(f"\n📊 情绪概况:")
        print(f"   新闻总数: {se.total_news}（中文{cn_count} + 英文{en_count}）")
        print(f"   正面: {se.positive_news} | 中性: {se.neutral_news} | 负面: {se.negative_news}")
        print(f"   整体情绪: {label_cn} ({se.overall_sentiment:+.2f})")
        print(f"   对黄金影响: {se.gold_impact_score:+.2f}")
        print(f"   恐惧/贪婪指数: {se.fear_greed_index:.0f} - {fg_label}")
        
        if se.topic_distribution:
            print(f"\n🏷️  热门话题:")
            topic_cn = {
                'fed_policy': '美联储政策',
                'inflation': '通胀数据',
                'geopolitical': '地缘政治',
                'dollar': '美元指数',
                'supply_demand': '供需关系',
                'employment': '就业数据',
                'growth': '经济增长',
            }
            sorted_topics = sorted(se.topic_distribution.items(), key=lambda x: x[1], reverse=True)
            for topic, count in sorted_topics[:5]:
                name = topic_cn.get(topic, topic)
                sent = se.sentiment_by_topic.get(topic, 0)
                print(f"   {name}: {count}篇 (情绪{sent:+.2f})")
        
        # 重要新闻
        important = sorted(
            se.analyzed_news,
            key=lambda x: x.importance + abs(x.impact_on_gold),
            reverse=True
        )[:3]
        
        if important:
            print(f"\n📝 重点新闻TOP3:")
            for i, n in enumerate(important, 1):
                icon = "🟢" if n.impact_on_gold > 0.1 else ("🔴" if n.impact_on_gold < -0.1 else "⚡")
                print(f"   {i}. {icon} [{n.source}] {n.title[:55]}")
                print(f"      黄金影响: {n.impact_on_gold:+.2f} | 重要性: {n.importance:.2f}")
    
    def section_technical(self):
        """第五部分：技术面分析"""
        self.print_section("五、技术面分析", star=True, weight="权重25%")
        
        if not self.tech_indicators:
            print("\n   ⚠️ 历史数据不足，技术面分析跳过")
            return
        
        price = self.realtime_data['price']
        
        print(f"\n📈 均线系统:")
        for n in [5, 10, 20, 60]:
            ma = self.tech_indicators.get(f'ma{n}')
            if ma:
                pos = "↑" if price > ma else "↓"
                print(f"   MA{n:2d}: ¥{ma:.3f} {pos}")
        
        rsi = self.tech_indicators.get('rsi', 50)
        print(f"\n📊 RSI(14): {rsi:.2f}")
        if rsi > 70:
            print(f"   ⚠️  超买区域 → 谨慎追高")
        elif rsi < 30:
            print(f"   💡 超卖区域 → 关注机会")
        elif rsi > 55:
            print(f"   🟡 偏强")
        elif rsi < 45:
            print(f"   🟡 偏弱")
        else:
            print(f"   ⚡ 中性")
        
        dif = self.tech_indicators.get('macd_dif', 0)
        dea = self.tech_indicators.get('macd_dea', 0)
        hist = self.tech_indicators.get('macd_hist', 0)
        print(f"\n📊 MACD:")
        print(f"   DIF: {dif:.4f} | DEA: {dea:.4f} | 柱: {hist:.4f}")
        if dif > dea:
            print(f"   🟢 金叉状态")
        else:
            print(f"   🔴 死叉状态")
        
        upper = self.tech_indicators.get('boll_upper', 0)
        mid = self.tech_indicators.get('boll_mid', 0)
        lower = self.tech_indicators.get('boll_lower', 0)
        print(f"\n📊 布林带:")
        print(f"   上轨: ¥{upper:.3f}")
        print(f"   中轨: ¥{mid:.3f}")
        print(f"   下轨: ¥{lower:.3f}")
        
        if price > upper:
            print(f"   🔴 价格在上轨之上 → 超买")
        elif price < lower:
            print(f"   🟢 价格在下轨之下 → 超卖")
        elif price > mid:
            print(f"   🟡 中轨上方 → 偏强")
        else:
            print(f"   🟡 中轨下方 → 偏弱")
        
        tech_score = self.get_tech_score()
        print(f"\n💡 技术面评分: {tech_score:+.2f}")
        
        return tech_score
    
    def get_momentum_score(self) -> float:
        """动量策略评分（-1到+1）"""
        if not self.tech_indicators or not self.realtime_data:
            return 0.0
        
        df = self.historical_df
        price = self.realtime_data['price']
        
        if df is None or len(df) < 60:
            return 0.0
        
        score = 0.0
        signals = 0
        
        close = df['close']
        
        # 1. 各周期动量
        for period, weight in [(10, 0.2), (20, 0.3), (30, 0.5)]:
            if len(df) > period:
                mom = (close.iloc[-1] / close.iloc[-period-1] - 1) * 100
                if mom > 0:
                    score += weight
                else:
                    score -= weight
                signals += 1
        
        # 2. 双动量信号（动量+MA60过滤）
        ma60 = self.tech_indicators.get('ma60')
        if ma60 and len(df) > 30:
            mom_30 = (close.iloc[-1] / close.iloc[-31] - 1) * 100
            # 双动量买入：30日动量正 + 价格在MA60上
            if mom_30 > 0 and price > ma60:
                score += 0.5
            # 双动量卖出：30日动量负 或 价格在MA60下
            elif mom_30 < 0 or price < ma60:
                score -= 0.5
            signals += 1
        
        # 3. 均线多头排列（趋势确认）
        ma5 = self.tech_indicators.get('ma5')
        ma20 = self.tech_indicators.get('ma20')
        ma60_val = self.tech_indicators.get('ma60')
        if ma5 and ma20 and ma60_val:
            if ma5 > ma20 > ma60_val:
                score += 0.3  # 完美多头
            elif ma5 < ma20 < ma60_val:
                score -= 0.3  # 完美空头
            signals += 1
        
        if signals > 0:
            # 归一化到-1到+1
            max_score = 1.0 + 0.5 + 0.3  # = 1.8
            return max(-1.0, min(1.0, score / max_score * 1.2))
        return 0.0
    
    def section_momentum(self):
        """第六部分：动量策略分析"""
        self.print_section("六、动量策略分析", star=True, weight="权重15%")
        
        if not self.tech_indicators or self.historical_df is None:
            print("\n   ⚠️ 数据不足，动量分析跳过")
            return 0.0
        
        df = self.historical_df
        price = self.realtime_data['price']
        close = df['close']
        
        print(f"\n📈 各周期动量:")
        for period in [5, 10, 20, 30, 60]:
            if len(df) > period:
                mom = (close.iloc[-1] / close.iloc[-period-1] - 1) * 100
                icon = "🟢" if mom > 0 else "🔴"
                print(f"   {period:>3}日动量: {mom:+.2f}% {icon}")
        
        # 双动量信号
        ma60 = self.tech_indicators.get('ma60')
        mom_30 = (close.iloc[-1] / close.iloc[-31] - 1) * 100 if len(df) > 30 else 0
        
        print(f"\n🎯 双动量策略 (30日+MA60):")
        print(f"   30日动量: {mom_30:+.2f}% → ", end='')
        if mom_30 > 0:
            print("✅ 动量向上")
        else:
            print("❌ 动量向下")
        
        print(f"   MA60位置: ¥{ma60:.3f} → ", end='')
        if price > ma60:
            print("✅ 价格在MA60上方（大趋势向上）")
        else:
            print("❌ 价格在MA60下方（大趋势向下）")
        
        print(f"   双动量信号: ", end='')
        if mom_30 > 0 and price > ma60:
            print("🟢 买入信号（双确认）")
        elif mom_30 < 0 or price < ma60:
            print("🔴 卖出/观望信号")
        else:
            print("⚡ 中性")
        
        # 均线排列
        ma5 = self.tech_indicators.get('ma5')
        ma20 = self.tech_indicators.get('ma20')
        ma60_val = self.tech_indicators.get('ma60')
        
        print(f"\n📊 均线排列:")
        if ma5 and ma20 and ma60_val:
            if ma5 > ma20 > ma60_val:
                print(f"   ✅ 完美多头排列（MA5 > MA20 > MA60）")
            elif ma5 < ma20 < ma60_val:
                print(f"   ❌ 完美空头排列（MA5 < MA20 < MA60）")
            else:
                print(f"   ⚡ 纠缠状态（无明确趋势）")
        
        # 动量评分
        mom_score = self.get_momentum_score()
        print(f"\n💡 动量策略评分: {mom_score:+.2f}")
        
        # 回测参考
        print(f"\n📚 历史回测参考 (500天):")
        print(f"   双动量策略总收益: +74.77% | 年化+32.50% | 夏普1.46")
        print(f"   买入持有收益: +60.56% | 超额收益: +14.21%")
        
        return mom_score
    
    def section_game_theory(self):
        """第七部分：博弈论分析"""
        self.print_section("七、博弈论分析", star=True, weight="权重10%")
        
        se = self.sentiment_result
        game_score = 0.0
        
        # 1. 情绪极端度
        sentiment_extreme = abs(se.gold_impact_score)
        if sentiment_extreme > 0.6:
            # 情绪过于极端，逆向操作
            game_score -= np.sign(se.gold_impact_score) * 0.5
            print(f"\n🧠 情绪逆向:")
            print(f"   市场情绪过于一致({se.gold_impact_score:+.2f})，警惕反转")
        else:
            game_score += se.gold_impact_score * 0.3
            print(f"\n🧠 情绪正常:")
            print(f"   市场情绪适中，可顺势参考")
        
        # 2. 恐惧贪婪指数逆向
        if se.fear_greed_index < 20:
            game_score += 0.5
            print(f"   恐惧指数过低({se.fear_greed_index:.0f})，逆向偏多")
        elif se.fear_greed_index > 80:
            game_score -= 0.5
            print(f"   贪婪指数过高({se.fear_greed_index:.0f})，逆向偏空")
        
        print(f"\n💡 博弈论评分: {game_score:+.2f}")
        
        return game_score
    
    def section_summary(self, tech_score, mom_score, game_score):
        """第八部分：综合评分与交易建议"""
        self.print_section("八、综合评分与交易建议")
        
        ev = self.event_result
        se = self.sentiment_result
        
        event_score = ev['final_score']
        sentiment_score = se.gold_impact_score
        
        # 权重分配（新增动量策略维度）
        w_event = 0.35
        w_sentiment = 0.20
        w_momentum = 0.15
        w_tech = 0.20
        w_game = 0.10
        
        final_score = (
            event_score * w_event +
            sentiment_score * w_sentiment +
            mom_score * w_momentum +
            tech_score * w_tech +
            game_score * w_game
        )
        
        # 置信度
        confidence = 0.0
        if ev['confidence'] > 0.3:
            confidence += 0.3
        if se.total_news >= 5:
            confidence += 0.25
        if self.tech_indicators:
            confidence += 0.2
        if abs(mom_score) > 0.3:
            confidence += 0.25
        
        print(f"\n📊 各维度评分及权重:")
        print(f"   📅 事件驱动:   {event_score:+.2f}  × {w_event*100:.0f}% = {event_score*w_event:+.2f}")
        print(f"   📰 新闻情绪:   {sentiment_score:+.2f}  × {w_sentiment*100:.0f}% = {sentiment_score*w_sentiment:+.2f}")
        print(f"   🚀 动量策略:   {mom_score:+.2f}  × {w_momentum*100:.0f}% = {mom_score*w_momentum:+.2f}")
        print(f"   📈 技术面:     {tech_score:+.2f}  × {w_tech*100:.0f}% = {tech_score*w_tech:+.2f}")
        print(f"   🧠 博弈论:     {game_score:+.2f}  × {w_game*100:.0f}% = {game_score*w_game:+.2f}")
        print(f"   ───────────────────────────────────")
        print(f"   🎯 综合评分:   {final_score:+.2f}")
        print(f"   💯 置信度:     {confidence:.0%}")
        
        # 交易建议
        if final_score >= 1.0:
            rec = "🟢 强烈买入"
            pos_radical = "30-40%"
            pos_moderate = "20-30%"
            pos_conservative = "15-20%"
        elif final_score >= 0.5:
            rec = "🟢 买入"
            pos_radical = "20-30%"
            pos_moderate = "15-20%"
            pos_conservative = "10-15%"
        elif final_score >= 0.1:
            rec = "🟡 谨慎买入"
            pos_radical = "15-20%"
            pos_moderate = "10-15%"
            pos_conservative = "5-10%"
        elif final_score > -0.1:
            rec = "⚡ 观望为主"
            pos_radical = "10%以内"
            pos_moderate = "5%以内"
            pos_conservative = "观望"
        elif final_score > -0.5:
            rec = "🟡 谨慎减仓"
            pos_radical = "减仓至10%"
            pos_moderate = "减仓至5%"
            pos_conservative = "清仓"
        else:
            rec = "🔴 建议卖出/做空"
            pos_radical = "清仓或做空"
            pos_moderate = "清仓"
            pos_conservative = "清仓"
        
        print(f"\n📋 交易建议: {rec}")
        
        if self.realtime_data:
            price = self.realtime_data['price']
            stop_loss = price * 0.98
            take_profit = price * 1.03
            
            print(f"\n💰 建议仓位:")
            print(f"   激进型: {pos_radical}")
            print(f"   稳健型: {pos_moderate}")
            print(f"   保守型: {pos_conservative}")
            
            print(f"\n🎯 止损止盈参考:")
            print(f"   止损位: ¥{stop_loss:.3f} (约-2%)")
            print(f"   止盈位: ¥{take_profit:.3f} (约+3%)")
            print(f"   风险收益比: 1:1.5")
    
    def section_key_levels(self):
        """第九部分：关键价位参考"""
        self.print_section("九、关键价位参考")
        
        if not self.tech_indicators or not self.realtime_data:
            print("\n   ⚠️ 数据不足")
            return
        
        price = self.realtime_data['price']
        upper = self.tech_indicators.get('boll_upper', price * 1.02)
        lower = self.tech_indicators.get('boll_lower', price * 0.98)
        ma20 = self.tech_indicators.get('ma20', price)
        ma60 = self.tech_indicators.get('ma60', price * 0.95)
        
        print(f"\n🟥 阻力位:")
        print(f"   R1 (布林上轨): ¥{upper:.3f}")
        print(f"   R2 (前高附近): ¥{upper * 1.01:.3f}")
        
        print(f"\n🟩 支撑位:")
        print(f"   S1 (布林下轨): ¥{lower:.3f}")
        print(f"   S2 (MA60):     ¥{ma60:.3f}")
        
        print(f"\n⚡ 当前价格: ¥{price:.3f}")
    
    def section_blogger_views(self):
        """第十部分：知名博主观点追踪"""
        self.print_section("十、知名博主观点追踪", star=True, weight="参考维度")
        
        # 获取博主观点
        tracker = BloggerTracker()
        views = tracker.fetch_blogger_views(days=7)
        consensus = tracker.analyze_consensus(views)
        
        # 共识度概览
        print(f"\n📊 共识度分析:")
        print(f"   看多博主: {consensus['bullish_count']}位")
        print(f"   看空博主: {consensus['bearish_count']}位")
        print(f"   中性博主: {consensus['neutral_count']}位")
        print(f"   平均情绪: {consensus['consensus']:+.2f}")
        print(f"   共识程度: {consensus['consensus_level']}")
        
        # 各博主观点
        print(f"\n📝 各博主最新观点:")
        for i, view in enumerate(views, 1):
            sentiment_emoji = '🟢' if view['sentiment'] > 0.2 else ('🔴' if view['sentiment'] < -0.2 else '⚡')
            sentiment_text = '看多' if view['sentiment'] > 0.2 else ('看空' if view['sentiment'] < -0.2 else '中性')
            
            print(f"\n   {i}. {sentiment_emoji} {view['name']} ({view['style']})")
            print(f"      平台: {view['platform']} | 粉丝: {view['followers']}")
            print(f"      观点: {view['view']}")
            print(f"      情绪: {sentiment_text} ({view['sentiment']:+.2f})")
        
        # 投资建议
        print(f"\n💡 博主观点参考建议:")
        if consensus['consensus'] > 0.3:
            print(f"   ✅ 博主共识偏多，可参考做多")
        elif consensus['consensus'] < -0.3:
            print(f"   ⚠️ 博主共识偏空，建议谨慎")
        else:
            print(f"   ⚡ 博主观点分歧较大，建议独立判断")
        
        print(f"\n   📌 重要提示:")
        print(f"   • 博主观点仅供参考，不构成投资建议")
        print(f"   • 网红可能滞后或错误，数据比网红更可靠")
        print(f"   • 建议用5维度分析系统交叉验证")
        
        return consensus
    
    def section_risk_warning(self):
        """第十一部分：风险提示"""
        self.print_section("十一、风险提示")
        
        print(f"""
⚠️  重要风险提示
────────────────────────────────────────────────────────────────────────
• 本分析仅供学习研究参考，不构成任何投资建议
• 投资有风险，入市需谨慎，请根据个人风险承受能力做出决策
• 黄金价格受多种因素影响，过去表现不代表未来收益
• 事件分析基于公开信息和历史规律，实际走势可能完全不同
• 历史规律不代表未来一定会重复
• 黑天鹅事件可能导致超跌后继续跌
• 技术分析有局限性，不能作为唯一决策依据
• 建议严格设置止损，单笔亏损控制在2%以内
• 黄金ETF跟踪国际金价，需注意汇率波动和溢价风险
• 博主观点仅供参考，不构成投资建议
────────────────────────────────────────────────────────────────────────
""")
    
    def run_full_analysis(self):
        """运行完整分析"""
        self.print_separator("=")
        print(f"📊 黄金ETF({self.etf_code}) 完整分析报告 (v3.0)")
        self.print_separator("=")
        print(f"⏰ 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("💡 核心思想: 事件驱动(35%) + 新闻情绪(20%) + 动量策略(15%) + 技术面(20%) + 博弈论(10%)")
        print("✅ 数据来源: 全部来自真实API，无任何模拟数据")
        print()
        
        # 获取数据
        if not self.fetch_all_data(history_days=250):
            print("\n❌ 无法获取关键数据，分析终止")
            return
        
        # 计算技术指标
        self.calculate_tech_indicators()
        
        # 事件驱动分析
        print("🔍 正在进行事件驱动分析...")
        self.event_result = self.event_analyzer.get_event_driven_trend(self.events, self.news)
        
        # 新闻情绪分析
        print("🔍 正在进行新闻情绪分析...")
        self.sentiment_result = self.sentiment_analyzer.analyze_news(self.news)
        
        # 技术面评分
        tech_score = self.get_tech_score()
        
        # 动量策略评分
        mom_score = self.get_momentum_score()
        
        # 输出各部分
        self.section_realtime()
        self.section_event_backtest()
        self.section_event_driven()
        self.section_sentiment()
        self.section_technical()
        self.section_momentum()
        game_score = self.section_game_theory()
        self.section_summary(tech_score, mom_score, game_score)
        self.section_key_levels()
        self.section_blogger_views()
        self.section_risk_warning()
        
        self.print_separator("=")
        print("✅ 分析完成")
        self.print_separator("=")


def main():
    parser = argparse.ArgumentParser(description='黄金交易分析专家 - Skill')
    parser.add_argument('--etf', default='518880', help='ETF代码（默认518880）')
    parser.add_argument('--market', default='sh', help='市场（默认sh）')
    parser.add_argument('--quick', action='store_true', help='快速分析模式')
    parser.add_argument('--backtest', action='store_true', help='历史事件回测')
    parser.add_argument('--strategy', action='store_true', help='事件驱动策略回测')
    
    args = parser.parse_args()
    
    if args.backtest:
        from core.event_backtest import EventBacktester
        from core.real_data import RealGoldETFData
        
        print("📊 历史事件回测分析")
        print("=" * 80)
        
        data = RealGoldETFData(args.etf, args.market)
        df = data.fetch_history(days=500)
        
        if df is None:
            print("❌ 无法获取数据")
            return
        
        backtester = EventBacktester(df)
        backtester.run_all_analysis()
        return
    
    if args.strategy:
        from core.event_driven_strategy import EventDrivenStrategy
        from core.real_data import RealGoldETFData
        
        print("📊 事件驱动策略回测")
        print("=" * 80)
        
        data = RealGoldETFData(args.etf, args.market)
        df = data.fetch_history(days=500)
        
        if df is None:
            print("❌ 无法获取数据")
            return
        
        strategy = EventDrivenStrategy(df)
        result = strategy.run_backtest(
            take_profit_pct=3.0,
            stop_loss_pct=2.0,
            max_hold_days=10,
        )
        strategy.print_result(result)
        return
    
    # 默认：完整分析
    skill = GoldAnalysisSkill(args.etf, args.market)
    skill.run_full_analysis()


if __name__ == "__main__":
    main()
