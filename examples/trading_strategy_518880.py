#!/usr/bin/env python3
"""
黄金交易策略研究 - 以518880（华安黄金ETF）为标准
结合实时数据、事件分析和技术指标给出交易建议
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import math


class GoldTradingStrategy:
    def __init__(self, target_price=518.88):
        self.target_price = target_price  # 518.880元/份
        self.current_data = {}
        self.historical_data = []
        self.strategies = {}
    
    def fetch_realtime_data(self):
        """获取实时行情数据"""
        print("\n📥 获取518880华安黄金ETF实时数据...")
        
        try:
            resp = requests.get(
                "https://push2.eastmoney.com/api/qt/stock/get",
                params={
                    'secid': '1.518880',
                    'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                    'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f107,f169,f170,f171'
                },
                timeout=10
            )
            if resp.status_code == 200:
                d = resp.json()
                if d.get('data'):
                    data = d['data']
                    self.current_data = {
                        'name': '华安黄金ETF(518880)',
                        'price': data.get('f43', 0) / 100 if data.get('f43') else 0,
                        'change': data.get('f169', 0) / 100,
                        'change_pct': data.get('f170', 0) / 100,
                        'volume': data.get('f47', 0),
                        'amount': data.get('f48', 0),
                        'high': data.get('f44', 0) / 100 if data.get('f44') else 0,
                        'low': data.get('f45', 0) / 100 if data.get('f45') else 0,
                        'open': data.get('f46', 0) / 100 if data.get('f46') else 0,
                        'prev_close': data.get('f60', 0) / 100 if data.get('f60') else 0,
                    }
                    print(f"✅ 获取成功")
        except Exception as e:
            print(f"⚠️ 东方财富API失败: {e}")
        
        if not self.current_data.get('price'):
            try:
                resp = requests.get(
                    "https://query1.finance.yahoo.com/v8/finance/chart/518880.SS",
                    params={'interval': '1d', 'range': '1d'},
                    headers={'User-Agent': 'Mozilla/5.0'},
                    timeout=10
                )
                if resp.status_code == 200:
                    d = resp.json()
                    result = d.get('chart', {}).get('result', [])
                    if result:
                        meta = result[0].get('meta', {})
                        self.current_data = {
                            'name': '华安黄金ETF(518880)',
                            'price': meta.get('regularMarketPrice', 0),
                            'change': meta.get('regularMarketChange', 0),
                            'change_pct': meta.get('regularMarketChangePercent', 0),
                            'prev_close': meta.get('previousClose', 0),
                            'high': meta.get('regularMarketDayHigh', 0),
                            'low': meta.get('regularMarketDayLow', 0),
                            'open': meta.get('regularMarketOpen', 0)
                        }
                        print(f"✅ Yahoo Finance获取成功")
            except Exception as e:
                print(f"⚠️ Yahoo Finance失败: {e}")
        
        if not self.current_data.get('price'):
            self.current_data = {
                'name': '华安黄金ETF(518880)',
                'price': self.target_price,
                'change': 0,
                'change_pct': 0,
                'prev_close': self.target_price,
                'high': self.target_price * 1.01,
                'low': self.target_price * 0.99,
                'open': self.target_price
            }
            print(f"⚠️ 使用目标价格: {self.target_price}")
        
        return self.current_data
    
    def fetch_historical_data(self, days=60):
        """获取历史数据"""
        print(f"\n📥 获取近{days}天历史数据...")
        
        try:
            resp = requests.get(
                "https://push2his.eastmoney.com/api/qt/stock/kline/get",
                params={
                    'secid': '1.518880',
                    'fields1': 'f1,f2,f3,f4,f5,f6',
                    'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                    'klt': '101',
                    'fqt': '1',
                    'beg': (datetime.now() - timedelta(days=days)).strftime('%Y%m%d'),
                    'end': datetime.now().strftime('%Y%m%d')
                },
                timeout=15
            )
            if resp.status_code == 200:
                d = resp.json()
                klines = d.get('data', {}).get('klines', [])
                
                if klines:
                    self.historical_data = []
                    for kline in klines:
                        parts = kline.split(',')
                        self.historical_data.append({
                            'date': parts[0],
                            'open': float(parts[1]),
                            'close': float(parts[2]),
                            'high': float(parts[3]),
                            'low': float(parts[4]),
                            'volume': float(parts[5])
                        })
                    print(f"✅ 获取 {len(self.historical_data)} 条历史K线")
        except Exception as e:
            print(f"⚠️ 历史数据获取失败: {e}")
        
        if not self.historical_data:
            self._generate_simulated_history(60)
        
        return self.historical_data
    
    def _generate_simulated_history(self, days):
        """生成模拟历史数据（基于当前价格模拟真实波动）"""
        data = []
        current = self.target_price
        
        for i in range(days, 0, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            change = np.random.normal(0, 0.02)
            current = current * (1 + change)
            
            open_price = current * (1 + np.random.uniform(-0.01, 0.01))
            close_price = current
            high = max(open_price, close_price) * (1 + np.random.uniform(0, 0.005))
            low = min(open_price, close_price) * (1 - np.random.uniform(0, 0.005))
            
            data.append({
                'date': date,
                'open': round(open_price, 3),
                'close': round(close_price, 3),
                'high': round(high, 3),
                'low': round(low, 3),
                'volume': np.random.randint(1000000, 5000000)
            })
        
        self.historical_data = data
        print(f"⚠️ 使用模拟历史数据: {len(data)} 条")
    
    def calculate_indicators(self):
        """计算技术指标"""
        if not self.historical_data:
            return {}
        
        df = pd.DataFrame(self.historical_data)
        df = df.sort_values('date')
        
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['histogram'] = df['macd'] - df['signal']
        
        df['upper_band'] = df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std()
        df['lower_band'] = df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std()
        
        df['trend'] = np.where(df['ma5'] > df['ma10'], '上涨', '下跌')
        df.loc[df['ma5'] == df['ma10'], 'trend'] = '震荡'
        
        self.indicators = df.iloc[-1].to_dict()
        return self.indicators
    
    def analyze_event_impact(self):
        """分析事件影响"""
        events = []
        try:
            resp = requests.get(
                "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for event in data[:10]:
                        title = event.get('title', '').lower()
                        impact = event.get('impact', '')
                        
                        if 'cpi' in title or 'inflation' in title:
                            events.append({
                                'type': '通胀',
                                'title': event.get('title'),
                                'impact': impact,
                                'gold_effect': '负相关' if impact == 'High' else '不确定'
                            })
                        elif 'fed' in title or 'interest rate' in title:
                            events.append({
                                'type': '利率',
                                'title': event.get('title'),
                                'impact': impact,
                                'gold_effect': '负相关' if impact == 'High' else '不确定'
                            })
        except:
            pass
        
        return events
    
    def generate_trading_signals(self):
        """生成交易信号"""
        if not self.current_data or not self.historical_data:
            return None
        
        signals = []
        current_price = self.current_data.get('price', self.target_price)
        indicators = self.calculate_indicators()
        
        if not indicators:
            return None
        
        signal_score = 0
        signal_reason = []
        
        ma5 = indicators.get('ma5', current_price)
        ma10 = indicators.get('ma10', current_price)
        ma20 = indicators.get('ma20', current_price)
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', 0)
        signal_line = indicators.get('signal', 0)
        histogram = indicators.get('histogram', 0)
        upper_band = indicators.get('upper_band', current_price * 1.05)
        lower_band = indicators.get('lower_band', current_price * 0.95)
        
        if current_price > ma5 and current_price > ma10:
            signal_score += 1
            signal_reason.append('价格位于短期均线上方')
        elif current_price < ma5:
            signal_score -= 1
            signal_reason.append('价格跌破短期均线')
        
        if ma5 > ma10:
            signal_score += 1
            signal_reason.append('短期均线金叉')
        elif ma5 < ma10:
            signal_score -= 1
            signal_reason.append('短期均线死叉')
        
        if rsi < 30:
            signal_score += 1
            signal_reason.append('RSI超卖，可能反弹')
        elif rsi > 70:
            signal_score -= 1
            signal_reason.append('RSI超买，注意回调')
        
        if histogram > 0 and histogram > indicators.get('histogram', 0):
            signal_score += 1
            signal_reason.append('MACD柱状图扩张，看多')
        elif histogram < 0:
            signal_score -= 1
            signal_reason.append('MACD柱状图为负')
        
        if current_price < lower_band:
            signal_score += 1
            signal_reason.append('价格触及布林带下轨，超卖')
        elif current_price > upper_band:
            signal_score -= 1
            signal_reason.append('价格触及布林带上轨，超买')
        
        if signal_score >= 2:
            recommendation = '🟢 买入/加仓'
            confidence = '高'
        elif signal_score <= -2:
            recommendation = '🔴 卖出/减仓'
            confidence = '高'
        elif signal_score > 0:
            recommendation = '🟡 谨慎持有'
            confidence = '中'
        elif signal_score < 0:
            recommendation = '🟡 观望'
            confidence = '中'
        else:
            recommendation = '⚡ 中性'
            confidence = '低'
        
        return {
            'score': signal_score,
            'recommendation': recommendation,
            'confidence': confidence,
            'reasons': signal_reason,
            'key_levels': {
                'resistance': upper_band,
                'support': lower_band,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20
            },
            'indicators': {
                'rsi': rsi,
                'macd': macd,
                'signal': signal_line,
                'histogram': histogram
            }
        }
    
    def run_analysis(self):
        """运行完整分析"""
        print("=" * 80)
        print("📅 518880华安黄金ETF交易策略研究")
        print(f"研究时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        self.fetch_realtime_data()
        self.fetch_historical_data(60)
        
        current = self.current_data
        print(f"\n【一】当前行情")
        print("-" * 80)
        print(f"📊 名称: {current.get('name')}")
        print(f"💰 当前价格: ¥{current.get('price', 0):.3f}")
        print(f"📈 涨跌: {current.get('change', 0):+.3f} ({current.get('change_pct', 0):+.2f}%)")
        print(f"📅 今开: ¥{current.get('open', 0):.3f}")
        print(f"📈 最高: ¥{current.get('high', 0):.3f}")
        print(f"📉 最低: ¥{current.get('low', 0):.3f}")
        print(f"📊 昨收: ¥{current.get('prev_close', 0):.3f}")
        
        print(f"\n【二】技术分析")
        print("-" * 80)
        indicators = self.calculate_indicators()
        if indicators:
            print(f"\n📊 均线系统:")
            print(f"   MA5:  ¥{indicators.get('ma5', 0):.3f}")
            print(f"   MA10: ¥{indicators.get('ma10', 0):.3f}")
            print(f"   MA20: ¥{indicators.get('ma20', 0):.3f}")
            print(f"   MA60: ¥{indicators.get('ma60', 0):.3f}")
            
            print(f"\n📊 MACD指标:")
            print(f"   DIF:  {indicators.get('macd', 0):.4f}")
            print(f"   DEA:  {indicators.get('signal', 0):.4f}")
            print(f"   MACD: {indicators.get('histogram', 0):.4f}")
            
            print(f"\n📊 RSI指标:")
            print(f"   RSI(14): {indicators.get('rsi', 0):.2f}")
            if indicators.get('rsi', 50) < 30:
                print(f"   → 超卖区域，可能存在反弹机会")
            elif indicators.get('rsi', 50) > 70:
                print(f"   → 超买区域，注意回调风险")
            else:
                print(f"   → 正常运行区域")
            
            print(f"\n📊 布林带:")
            print(f"   上轨: ¥{indicators.get('upper_band', 0):.3f}")
            print(f"   中轨: ¥{indicators.get('ma20', 0):.3f}")
            print(f"   下轨: ¥{indicators.get('lower_band', 0):.3f}")
            
            print(f"\n📊 趋势判断: {indicators.get('trend', '震荡')}")
        
        print(f"\n【三】事件影响")
        print("-" * 80)
        events = self.analyze_event_impact()
        if events:
            for event in events[:3]:
                emoji = "🔴" if event['impact'] == 'High' else "🟡"
                print(f"{emoji} [{event['type']}] {event['title']}")
                print(f"   → 对黄金影响: {event['gold_effect']}")
        else:
            print("今日无重大财经事件")
        
        print(f"\n【四】交易信号")
        print("-" * 80)
        signals = self.generate_trading_signals()
        if signals:
            print(f"\n🎯 综合评分: {signals['score']:+.0f}")
            print(f"\n📋 交易建议: {signals['recommendation']}")
            print(f"💯 置信度: {signals['confidence']}")
            
            print(f"\n📊 决策依据:")
            for reason in signals['reasons']:
                print(f"   • {reason}")
            
            levels = signals['key_levels']
            print(f"\n📍 关键价位:")
            print(f"   🟥 阻力位: ¥{levels.get('resistance', 0):.3f}")
            print(f"   🟩 支撑位: ¥{levels.get('support', 0):.3f}")
            
            ind = signals['indicators']
            print(f"\n📊 技术指标状态:")
            print(f"   RSI: {ind['rsi']:.2f}", end="")
            if ind['rsi'] < 30:
                print(" (超卖)")
            elif ind['rsi'] > 70:
                print(" (超买)")
            else:
                print(" (正常)")
        
        print(f"\n【五】综合建议")
        print("-" * 80)
        
        if signals:
            score = signals['score']
            price = current.get('price', self.target_price)
            
            if score >= 2:
                print(f"""
🟢 建议操作: 买入/加仓

理由:
• 技术面多个指标显示看多信号
• {'当前价格处于相对低位' if price < indicators.get('ma20', price) else '价格走势强劲'}
• {'RSI处于超卖区域，存在反弹机会' if indicators.get('rsi', 50) < 30 else ''}

仓位建议:
• 激进型: 30%-40%仓位
• 稳健型: 20%-30%仓位

止损位: ¥{levels.get('support', price * 0.98):.3f} (布林带下轨)
目标位: ¥{levels.get('resistance', price * 1.02):.3f} (布林带上轨)
""")
            elif score <= -2:
                print(f"""
🔴 建议操作: 卖出/减仓

理由:
• 技术面多个指标显示看空信号
• {'当前价格处于相对高位' if price > indicators.get('ma20', price) else '价格走势偏弱'}
• {'RSI处于超买区域，注意回调风险' if indicators.get('rsi', 50) > 70 else ''}

仓位建议:
• 激进型: 清仓或留10%-20%
• 稳健型: 观望为主

止损位: ¥{levels.get('resistance', price * 1.02):.3f}
目标位: ¥{levels.get('support', price * 0.98):.3f}
""")
            else:
                print(f"""
⚡ 建议操作: 观望/轻仓

理由:
• 技术面信号中性
• {'价格处于均线附近，等待方向明确' if abs(price - indicators.get('ma20', price)) < price * 0.01 else ''}

仓位建议:
• 激进型: 10%-20%仓位
• 稳健型: 5%-10%仓位

操作建议:
• 等待价格突破关键阻力/支撑后再操作
• 可考虑定投方式分批建仓
""")
        
        print(f"\n【六】风险提示")
        print("-" * 80)
        print("⚠️ 注意事项:")
        print("• 黄金ETF价格与国际金价联动，受美元汇率影响")
        print("• 近期波动较大，建议控制仓位")
        print("• 本分析仅供参考，不构成投资建议")
        print("• 实际交易前请结合个人风险承受能力")
        
        print("\n" + "=" * 80)
        print("✅ 分析完成")
        print("=" * 80)


def main():
    strategy = GoldTradingStrategy(target_price=5.1888)
    strategy.run_analysis()


if __name__ == "__main__":
    main()