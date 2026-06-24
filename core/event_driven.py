#!/usr/bin/env python3
"""
事件驱动分析模块
================

核心思想：黄金价格主要由宏观事件驱动，技术面只是辅助
本模块专注于事件分析和基本面判断

功能：
1. 经济日历事件分析（美联储、CPI、非农等）
2. 事件影响评分系统
3. 美联储政策追踪
4. 通胀/就业数据分析
5. 地缘政治风险评估
6. 美元指数关联分析
7. 事件驱动的大趋势判断
"""

import re
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class EventImpact:
    """事件影响评估"""
    event_title: str
    impact_level: str = 'Low'           # High/Medium/Low
    gold_direction: float = 0.0         # 对黄金的影响方向 (-1到+1)
    confidence: float = 0.0             # 置信度
    reasoning: str = ''                 # 判断理由


@dataclass
class EventAnalysisResult:
    """事件分析结果"""
    total_events: int = 0
    high_impact_count: int = 0
    medium_impact_count: int = 0
    low_impact_count: int = 0
    
    fed_events: List[Dict] = field(default_factory=list)     # 美联储相关
    inflation_events: List[Dict] = field(default_factory=list)  # 通胀相关
    employment_events: List[Dict] = field(default_factory=list) # 就业相关
    geopolitical_events: List[Dict] = field(default_factory=list) # 地缘政治
    
    event_score: float = 0.0            # 事件综合评分 (-3到+3)
    trend_judgment: str = 'neutral'      # bullish/bearish/neutral
    reasoning: str = ''                  # 判断理由
    key_events: List[EventImpact] = field(default_factory=list)


class EventDrivenAnalyzer:
    """
    事件驱动分析器
    
    基于宏观经济事件判断黄金大趋势
    """
    
    def __init__(self):
        # 事件关键词库及对黄金的影响方向
        self.event_keywords = {
            # 美联储政策
            'fed rate decision': {'direction': +0.8, 'type': 'fed', 'weight': 0.35},
            'fomc': {'direction': +0.6, 'type': 'fed', 'weight': 0.3},
            'federal reserve': {'direction': +0.4, 'type': 'fed', 'weight': 0.25},
            'interest rate decision': {'direction': +0.7, 'type': 'fed', 'weight': 0.3},
            'rate decision': {'direction': +0.6, 'type': 'fed', 'weight': 0.25},
            'rate cut': {'direction': +0.9, 'type': 'fed', 'weight': 0.35},
            'rate hike': {'direction': -0.9, 'type': 'fed', 'weight': 0.35},
            'powell': {'direction': +0.3, 'type': 'fed', 'weight': 0.15},
            'fed chair': {'direction': +0.2, 'type': 'fed', 'weight': 0.1},
            
            # 通胀数据
            'cpi': {'direction': +0.7, 'type': 'inflation', 'weight': 0.3},
            'consumer price index': {'direction': +0.7, 'type': 'inflation', 'weight': 0.3},
            'core cpi': {'direction': +0.65, 'type': 'inflation', 'weight': 0.25},
            'pce': {'direction': +0.6, 'type': 'inflation', 'weight': 0.25},
            'inflation': {'direction': +0.7, 'type': 'inflation', 'weight': 0.25},
            'ppi': {'direction': +0.4, 'type': 'inflation', 'weight': 0.15},
            'producer price index': {'direction': +0.4, 'type': 'inflation', 'weight': 0.15},
            
            # 就业数据
            'nonfarm': {'direction': -0.5, 'type': 'employment', 'weight': 0.25},
            'non-farm': {'direction': -0.5, 'type': 'employment', 'weight': 0.25},
            'employment change': {'direction': -0.4, 'type': 'employment', 'weight': 0.2},
            'unemployment rate': {'direction': +0.4, 'type': 'employment', 'weight': 0.2},
            'jobless claims': {'direction': +0.3, 'type': 'employment', 'weight': 0.15},
            'nfp': {'direction': -0.5, 'type': 'employment', 'weight': 0.25},
            
            # 经济增长
            'gdp': {'direction': -0.3, 'type': 'growth', 'weight': 0.15},
            'retail sales': {'direction': -0.25, 'type': 'growth', 'weight': 0.1},
            
            # 地缘政治（需要结合新闻判断）
            'geopolitical': {'direction': +0.6, 'type': 'geo', 'weight': 0.25},
            'war': {'direction': +0.8, 'type': 'geo', 'weight': 0.3},
            'conflict': {'direction': +0.6, 'type': 'geo', 'weight': 0.2},
            'sanction': {'direction': +0.5, 'type': 'geo', 'weight': 0.2},
            'election': {'direction': +0.3, 'type': 'geo', 'weight': 0.15},
            'tariff': {'direction': +0.4, 'type': 'geo', 'weight': 0.2},
        }
        
        # 高影响事件列表（用于快速筛选）
        self.high_impact_keywords = [
            'cpi', 'pce', 'nonfarm', 'nfp', 'fomc', 'rate decision',
            'gdp', 'fed', 'interest rate', 'rate cut', 'rate hike',
            'employment', 'unemployment'
        ]
    
    def analyze_economic_calendar(
        self,
        events: List[Dict],
        look_ahead_days: int = 3
    ) -> EventAnalysisResult:
        """
        分析经济日历事件
        
        参数：
            events: 事件列表（来自Forex Factory等）
            look_ahead_days: 向前看多少天的事件
        
        返回：
            EventAnalysisResult
        """
        result = EventAnalysisResult()
        
        if not events:
            result.reasoning = '无事件数据'
            return result
        
        # 过滤未来几天的事件
        today = datetime.now().date()
        upcoming_events = []
        
        for event in events:
            try:
                event_date_str = event.get('date', '')
                if isinstance(event_date_str, str):
                    # 尝试解析日期
                    for fmt in ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d', '%Y-%m-%d %H:%M']:
                        try:
                            event_date = datetime.strptime(event_date_str[:10], '%Y-%m-%d').date()
                            break
                        except:
                            continue
                    else:
                        continue
                else:
                    continue
                
                days_diff = (event_date - today).days
                if -1 <= days_diff <= look_ahead_days:  # 包含昨天到未来N天
                    upcoming_events.append(event)
            except:
                continue
        
        result.total_events = len(upcoming_events)
        
        # 统计影响等级
        for event in upcoming_events:
            impact = event.get('impact', 'Low')
            if impact == 'High':
                result.high_impact_count += 1
            elif impact == 'Medium':
                result.medium_impact_count += 1
            else:
                result.low_impact_count += 1
            
            # 分类事件
            title = event.get('title', '').lower()
            currency = event.get('currency', '')
            
            # 只关注美元相关事件（对黄金影响最大）
            if currency and currency != 'USD':
                continue
            
            event_info = {
                'title': event.get('title'),
                'date': event.get('date'),
                'impact': impact,
                'forecast': event.get('forecast'),
                'previous': event.get('previous'),
            }
            
            if any(k in title for k in ['fed', 'fomc', 'rate decision', 'interest rate', 'powell']):
                result.fed_events.append(event_info)
            elif any(k in title for k in ['cpi', 'pce', 'inflation', 'ppi']):
                result.inflation_events.append(event_info)
            elif any(k in title for k in ['nonfarm', 'nfp', 'employment', 'unemployment', 'jobless']):
                result.employment_events.append(event_info)
        
        # 计算事件评分
        result.event_score = self._calculate_event_score(upcoming_events)
        
        # 判断趋势
        if result.event_score > 0.5:
            result.trend_judgment = 'bullish'
        elif result.event_score < -0.5:
            result.trend_judgment = 'bearish'
        else:
            result.trend_judgment = 'neutral'
        
        # 生成关键事件分析
        result.key_events = self._generate_key_events(upcoming_events)
        
        # 生成理由
        result.reasoning = self._generate_reasoning(result)
        
        return result
    
    def _calculate_event_score(self, events: List[Dict]) -> float:
        """计算事件综合评分"""
        if not events:
            return 0.0
        
        total_score = 0.0
        total_weight = 0.0
        
        for event in events:
            title = event.get('title', '').lower()
            impact = event.get('impact', 'Low')
            currency = event.get('currency', '')
            
            # 非美元事件权重减半
            currency_weight = 1.0 if currency == 'USD' else 0.3
            
            # 影响等级权重
            impact_weight = {
                'High': 1.0,
                'Medium': 0.5,
                'Low': 0.2
            }.get(impact, 0.2)
            
            # 匹配关键词
            matched_direction = 0.0
            max_weight = 0.0
            
            for keyword, info in self.event_keywords.items():
                if keyword in title:
                    if info['weight'] > max_weight:
                        max_weight = info['weight']
                        matched_direction = info['direction'] * info['weight']
            
            if max_weight > 0:
                score = matched_direction * impact_weight * currency_weight
                total_score += score
                total_weight += max_weight * impact_weight * currency_weight
        
        if total_weight > 0:
            return total_score / total_weight * 3  # 归一化到-3到+3
        return 0.0
    
    def _generate_key_events(self, events: List[Dict]) -> List[EventImpact]:
        """生成关键事件分析列表"""
        key_events = []
        
        # 只关注美元的高/中影响事件
        us_events = [e for e in events if e.get('currency') == 'USD']
        important = [e for e in us_events if e.get('impact') in ['High', 'Medium']]
        
        for event in important[:10]:
            title = event.get('title', '')
            title_lower = title.lower()
            
            # 找最匹配的关键词
            best_direction = 0.0
            best_reason = ''
            
            for keyword, info in self.event_keywords.items():
                if keyword in title_lower:
                    direction = info['direction']
                    if abs(direction) > abs(best_direction):
                        best_direction = direction
                        if direction > 0:
                            best_reason = f'{keyword}通常利多黄金'
                        else:
                            best_reason = f'{keyword}通常利空黄金'
            
            # 考虑预期和前值的对比
            forecast = event.get('forecast', '')
            previous = event.get('previous', '')
            
            if forecast and previous:
                try:
                    f_val = float(str(forecast).replace('%', '').strip())
                    p_val = float(str(previous).replace('%', '').strip())
                    if f_val > p_val:
                        # 预期比前值高
                        if best_direction > 0:
                            best_reason += f'，预期{forecast}高于前值{previous}，利好程度↑'
                        else:
                            best_reason += f'，预期{forecast}高于前值{previous}，利空程度↑'
                    elif f_val < p_val:
                        if best_direction > 0:
                            best_reason += f'，预期{forecast}低于前值{previous}，利好程度↓'
                        else:
                            best_reason += f'，预期{forecast}低于前值{previous}，利空程度↓'
                except:
                    pass
            
            key_events.append(EventImpact(
                event_title=title,
                impact_level=event.get('impact', 'Low'),
                gold_direction=best_direction,
                confidence=0.7 if event.get('impact') == 'High' else 0.5,
                reasoning=best_reason or '一般事件'
            ))
        
        return key_events
    
    def _generate_reasoning(self, result: EventAnalysisResult) -> str:
        """生成分析理由"""
        reasons = []
        
        if result.fed_events:
            titles = [e['title'] for e in result.fed_events[:3]]
            reasons.append(f"美联储相关事件: {', '.join(titles)}")
        
        if result.inflation_events:
            titles = [e['title'] for e in result.inflation_events[:3]]
            reasons.append(f"通胀数据发布: {', '.join(titles)}")
        
        if result.employment_events:
            titles = [e['title'] for e in result.employment_events[:3]]
            reasons.append(f"就业数据发布: {', '.join(titles)}")
        
        if result.high_impact_count > 0:
            reasons.append(f"共{result.high_impact_count}个高影响事件")
        
        if result.trend_judgment == 'bullish':
            reasons.append(f"整体偏利多黄金（评分{result.event_score:+.2f}）")
        elif result.trend_judgment == 'bearish':
            reasons.append(f"整体偏利空黄金（评分{result.event_score:+.2f}）")
        else:
            reasons.append(f"整体中性（评分{result.event_score:+.2f}）")
        
        return '; '.join(reasons)
    
    def analyze_fed_policy(self, news_list: List[Dict]) -> Dict:
        """
        从新闻中分析美联储政策倾向
        
        返回：
            {
                'policy_direction': 'hawkish'/'dovish'/'neutral',
                'rate_cut_probability': float,
                'rate_hike_probability': float,
                'key_news': List[str]
            }
        """
        hawkish_words = ['hike', 'hawkish', 'tighten', 'higher rate', 'raise rate', 'restrictive', 'inflation high']
        dovish_words = ['cut', 'dovish', 'ease', 'lower rate', 'pivot', 'rate cut', 'loosen', 'inflation cool']
        
        hawkish_count = 0
        dovish_count = 0
        total_articles = 0
        key_news = []
        
        for news in news_list:
            title = news.get('title', '') or ''
            desc = news.get('description', '') or ''
            text = (title + ' ' + desc).lower()
            
            if 'fed' not in text and 'powell' not in text and 'fomc' not in text:
                continue
            
            total_articles += 1
            
            h_count = sum(1 for w in hawkish_words if w in text)
            d_count = sum(1 for w in dovish_words if w in text)
            
            hawkish_count += h_count
            dovish_count += d_count
            
            if h_count > 0 or d_count > 0:
                key_news.append(news.get('title', '')[:80])
        
        total = hawkish_count + dovish_count
        if total == 0:
            return {
                'policy_direction': 'neutral',
                'rate_cut_probability': 0.5,
                'rate_hike_probability': 0.5,
                'key_news': key_news[:5],
                'article_count': total_articles
            }
        
        cut_prob = dovish_count / total
        hike_prob = hawkish_count / total
        
        if cut_prob > 0.6:
            direction = 'dovish'
        elif hike_prob > 0.6:
            direction = 'hawkish'
        else:
            direction = 'neutral'
        
        return {
            'policy_direction': direction,
            'rate_cut_probability': cut_prob,
            'rate_hike_probability': hike_prob,
            'key_news': key_news[:5],
            'article_count': total_articles
        }
    
    def analyze_geopolitical_risk(self, news_list: List[Dict]) -> Dict:
        """
        从新闻中分析地缘政治风险
        
        黄金是避险资产，地缘风险升高通常利多黄金
        """
        risk_keywords = {
            'war': 1.0,
            'conflict': 0.7,
            'military': 0.6,
            'attack': 0.6,
            'sanction': 0.5,
            'tariff': 0.4,
            'tension': 0.5,
            'crisis': 0.6,
            'election': 0.3,
            'uncertainty': 0.4,
            'fear': 0.4,
            'safe haven': 0.5,
            'risk off': 0.5,
        }
        
        risk_score = 0.0
        total_risk_words = 0
        relevant_news = []
        
        for news in news_list:
            title = news.get('title', '') or ''
            desc = news.get('description', '') or ''
            text = (title + ' ' + desc).lower()
            
            article_risk = 0.0
            for keyword, weight in risk_keywords.items():
                count = text.count(keyword)
                if count > 0:
                    article_risk += count * weight
                    total_risk_words += count
            
            if article_risk > 0:
                risk_score += article_risk
                relevant_news.append({
                    'title': news.get('title', ''),
                    'risk_score': article_risk,
                    'source': news.get('source', '')
                })
        
        # 归一化到0-1
        normalized_score = min(risk_score / 10.0, 1.0)
        
        if normalized_score > 0.6:
            risk_level = 'high'
        elif normalized_score > 0.3:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_score': normalized_score,
            'risk_level': risk_level,
            'relevant_news_count': len(relevant_news),
            'top_risk_news': sorted(relevant_news, key=lambda x: x['risk_score'], reverse=True)[:5],
            'gold_impact': normalized_score * 1.5 - 0.5,  # -0.5 到 +1.0
        }
    
    def get_event_driven_trend(
        self,
        calendar_events: List[Dict],
        news_list: List[Dict]
    ) -> Dict:
        """
        综合事件驱动分析，给出大趋势判断
        
        这是核心函数，整合所有分析
        """
        # 1. 经济日历分析
        calendar_result = self.analyze_economic_calendar(calendar_events)
        
        # 2. 美联储政策分析
        fed_result = self.analyze_fed_policy(news_list)
        
        # 3. 地缘政治风险
        geo_result = self.analyze_geopolitical_risk(news_list)
        
        # 综合评分（权重分配）
        # 经济日历: 35%
        # 美联储政策: 35%
        # 地缘政治: 30%
        
        calendar_score = calendar_result.event_score / 3.0  # 归一化到-1到+1
        
        # 美联储政策分数：鸽派利多，鹰派利空
        fed_score = (fed_result['rate_cut_probability'] - fed_result['rate_hike_probability'])
        
        # 地缘政治分数
        geo_score = geo_result['gold_impact']
        
        # 加权综合
        final_score = (
            calendar_score * 0.35 +
            fed_score * 0.35 +
            geo_score * 0.30
        )
        
        # 置信度
        confidence = 0.0
        if calendar_result.total_events > 0:
            confidence += 0.3
        if fed_result['article_count'] > 2:
            confidence += 0.35
        if geo_result['relevant_news_count'] > 2:
            confidence += 0.35
        
        # 趋势判断
        if final_score > 0.3:
            trend = 'bullish'
        elif final_score < -0.3:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        return {
            'final_score': final_score,           # -1到+1
            'trend': trend,                       # bullish/bearish/neutral
            'confidence': confidence,             # 0到1
            'components': {
                'calendar_score': calendar_score,
                'fed_score': fed_score,
                'geo_score': geo_score,
            },
            'calendar_analysis': calendar_result,
            'fed_analysis': fed_result,
            'geo_analysis': geo_result,
            'analysis_time': datetime.now().isoformat(),
        }


# =============================================================================
# 快速测试
# =============================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/workspace')
    from core.api_tools import EconomicCalendarAPI, NewsAPI
    
    print("=" * 80)
    print("🧪 事件驱动分析模块测试")
    print("=" * 80)
    print()
    
    # 获取数据
    print("📅 获取经济日历...")
    events = EconomicCalendarAPI.forexfactory() or []
    print(f"   获取到 {len(events)} 个事件")
    
    print("📰 获取财经新闻...")
    news = NewsAPI.get_financial_news()
    print(f"   获取到 {len(news)} 条新闻")
    print()
    
    # 测试分析器
    analyzer = EventDrivenAnalyzer()
    
    print("=" * 80)
    print("📊 经济日历事件分析")
    print("=" * 80)
    
    cal_result = analyzer.analyze_economic_calendar(events)
    print(f"总事件数: {cal_result.total_events}")
    print(f"高影响: {cal_result.high_impact_count} | 中影响: {cal_result.medium_impact_count} | 低影响: {cal_result.low_impact_count}")
    print(f"美联储事件: {len(cal_result.fed_events)} 个")
    print(f"通胀事件: {len(cal_result.inflation_events)} 个")
    print(f"就业事件: {len(cal_result.employment_events)} 个")
    print(f"事件评分: {cal_result.event_score:+.2f}")
    print(f"趋势判断: {cal_result.trend_judgment}")
    print(f"分析理由: {cal_result.reasoning}")
    
    if cal_result.key_events:
        print(f"\n🔑 关键事件分析:")
        for e in cal_result.key_events[:5]:
            direction_icon = "🟢" if e.gold_direction > 0 else ("🔴" if e.gold_direction < 0 else "⚡")
            print(f"   {direction_icon} {e.event_title[:40]}")
            print(f"      影响: {e.impact_level} | 方向: {e.gold_direction:+.2f} | {e.reasoning}")
    
    print()
    print("=" * 80)
    print("🏛️ 美联储政策分析")
    print("=" * 80)
    
    fed_result = analyzer.analyze_fed_policy(news)
    direction_cn = {
        'dovish': '鸽派（利多黄金）',
        'hawkish': '鹰派（利空黄金）',
        'neutral': '中性'
    }.get(fed_result['policy_direction'], '中性')
    
    print(f"政策倾向: {direction_cn}")
    print(f"降息概率: {fed_result['rate_cut_probability']:.1%}")
    print(f"加息概率: {fed_result['rate_hike_probability']:.1%}")
    print(f"相关新闻: {fed_result['article_count']} 篇")
    
    if fed_result['key_news']:
        print(f"\n相关新闻:")
        for n in fed_result['key_news'][:3]:
            print(f"   - {n}")
    
    print()
    print("=" * 80)
    print("🌍 地缘政治风险分析")
    print("=" * 80)
    
    geo_result = analyzer.analyze_geopolitical_risk(news)
    level_cn = {'high': '高', 'medium': '中', 'low': '低'}.get(geo_result['risk_level'], '低')
    
    print(f"风险评分: {geo_result['risk_score']:.2f}")
    print(f"风险等级: {level_cn}")
    print(f"相关新闻: {geo_result['relevant_news_count']} 篇")
    print(f"对黄金影响: {geo_result['gold_impact']:+.2f}")
    
    if geo_result['top_risk_news']:
        print(f"\n高风险新闻:")
        for n in geo_result['top_risk_news'][:3]:
            print(f"   - [{n['source']}] {n['title'][:50]} (风险分: {n['risk_score']:.2f})")
    
    print()
    print("=" * 80)
    print("🎯 综合事件驱动大趋势判断")
    print("=" * 80)
    
    final = analyzer.get_event_driven_trend(events, news)
    
    trend_cn = {
        'bullish': '🟢 看涨（利多黄金）',
        'bearish': '🔴 看跌（利空黄金）',
        'neutral': '⚡ 中性（观望）'
    }.get(final['trend'], '中性')
    
    print(f"\n最终评分: {final['final_score']:+.2f}")
    print(f"趋势判断: {trend_cn}")
    print(f"置信度: {final['confidence']:.1%}")
    print(f"\n各维度得分:")
    print(f"   经济日历: {final['components']['calendar_score']:+.2f} (权重35%)")
    print(f"   美联储政策: {final['components']['fed_score']:+.2f} (权重35%)")
    print(f"   地缘政治: {final['components']['geo_score']:+.2f} (权重30%)")
    
    print(f"\n💡 分析说明:")
    print("   事件驱动分析基于宏观基本面，判断黄金大趋势")
    print("   建议结合技术面做入场时机选择")
    print()
    print("=" * 80)
