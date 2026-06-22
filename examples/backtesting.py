#!/usr/bin/env python3
"""
黄金历史数据回测系统
使用真实历史数据，支持多种策略回测
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import math


class GoldBacktester:
    def __init__(self):
        self.historical_data = None
        self.strategy_results = {}
    
    def fetch_historical_data(self, days=90):
        """从免费API获取黄金历史数据"""
        data = []
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            print(f"📥 获取历史数据: {start_date.date()} 到 {end_date.date()}")
            
            resp = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    'function': 'TIME_SERIES_DAILY',
                    'symbol': 'GC=F',
                    'apikey': 'demo'
                },
                timeout=15
            )
            if resp.status_code == 200:
                d = resp.json()
                time_series = d.get('Time Series (Daily)', {})
                
                if time_series:
                    df = pd.DataFrame.from_dict(time_series, orient='index').reset_index()
                    df.columns = ['Date', 'open', 'high', 'low', 'close', 'volume']
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df.sort_values('Date')
                    df = df[['Date', 'open', 'close']].astype({'open': float, 'close': float})
                    
                    data = df.to_dict('records')
                    print(f"✅ Alpha Vantage 获取 {len(data)} 条真实历史数据")
        
        except Exception as e:
            print(f"⚠️ Alpha Vantage失败: {e}")
        
        if not data:
            try:
                resp = requests.get(
                    "https://api.metals.live/v1/spot/gold/historical",
                    timeout=15
                )
                if resp.status_code == 200:
                    d = resp.json()
                    if isinstance(d, list):
                        df = pd.DataFrame(d)
                        df['Date'] = pd.to_datetime(df['date'])
                        df = df.rename(columns={'price': 'close'})
                        df['open'] = df['close']
                        df = df[['Date', 'open', 'close']]
                        data = df.to_dict('records')
                        print(f"✅ metals.live 获取 {len(data)} 条真实历史数据")
            
            except Exception as e:
                print(f"⚠️ metals.live失败: {e}")
        
        if not data:
            print("⚠️ 使用备用数据源...")
            data = self._generate_simulated_data(days)
        
        self.historical_data = data
        return data
    
    def _generate_simulated_data(self, days):
        """生成模拟历史数据（仅作为最后的fallback）"""
        data = []
        base_price = 4200
        current_price = base_price
        
        for i in range(days, 0, -1):
            date = datetime.now() - timedelta(days=i)
            change = np.random.normal(0, 20)
            current_price = max(3800, min(4600, current_price + change))
            
            data.append({
                'Date': date,
                'open': current_price,
                'close': current_price + np.random.normal(0, 10)
            })
        
        print(f"⚠️ 使用模拟数据: {len(data)} 条")
        return data
    
    def calculate_indicators(self):
        """计算技术指标"""
        if not self.historical_data:
            return
        
        df = pd.DataFrame(self.historical_data)
        df = df.sort_values('Date')
        
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma50'] = df['close'].rolling(50).mean()
        df['price_change'] = df['close'].pct_change() * 100
        
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        df['macd'], df['signal'], df['histogram'] = self._calculate_macd(df['close'])
        
        self.historical_data = df.to_dict('records')
    
    def _calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram
    
    def backtest_strategy(self, strategy_name, params=None):
        """回测指定策略"""
        if not self.historical_data:
            print("❌ 请先获取历史数据")
            return None
        
        self.calculate_indicators()
        df = pd.DataFrame(self.historical_data).dropna()
        
        if strategy_name == 'moving_average_crossover':
            results = self._backtest_ma_crossover(df, params)
        elif strategy_name == 'rsi_strategy':
            results = self._backtest_rsi(df, params)
        elif strategy_name == 'macd_strategy':
            results = self._backtest_macd(df, params)
        elif strategy_name == 'golden_cross':
            results = self._backtest_golden_cross(df, params)
        else:
            print(f"❌ 未知策略: {strategy_name}")
            return None
        
        self.strategy_results[strategy_name] = results
        return results
    
    def _backtest_ma_crossover(self, df, params=None):
        """均线交叉策略回测"""
        short_window = params.get('short_window', 20)
        long_window = params.get('long_window', 50)
        
        df['short_ma'] = df['close'].rolling(short_window).mean()
        df['long_ma'] = df['close'].rolling(long_window).mean()
        
        df['signal'] = 0
        df.loc[df['short_ma'] > df['long_ma'], 'signal'] = 1
        df.loc[df['short_ma'] < df['long_ma'], 'signal'] = -1
        
        df['position'] = df['signal'].shift()
        df['strategy_return'] = df['position'] * df['price_change'] / 100
        
        return self._calculate_metrics(df)
    
    def _backtest_rsi(self, df, params=None):
        """RSI策略回测"""
        oversold = params.get('oversold', 30)
        overbought = params.get('overbought', 70)
        
        df['signal'] = 0
        df.loc[df['rsi'] < oversold, 'signal'] = 1
        df.loc[df['rsi'] > overbought, 'signal'] = -1
        
        df['position'] = df['signal'].shift()
        df['strategy_return'] = df['position'] * df['price_change'] / 100
        
        return self._calculate_metrics(df)
    
    def _backtest_macd(self, df, params=None):
        """MACD策略回测"""
        df['signal'] = 0
        df.loc[(df['macd'] > df['signal']) & (df['macd'].shift() <= df['signal'].shift()), 'signal'] = 1
        df.loc[(df['macd'] < df['signal']) & (df['macd'].shift() >= df['signal'].shift()), 'signal'] = -1
        
        df['position'] = df['signal'].shift()
        df['strategy_return'] = df['position'] * df['price_change'] / 100
        
        return self._calculate_metrics(df)
    
    def _backtest_golden_cross(self, df, params=None):
        """金叉/死叉策略回测"""
        df['signal'] = 0
        df.loc[(df['ma20'] > df['ma50']) & (df['ma20'].shift() <= df['ma50'].shift()), 'signal'] = 1
        df.loc[(df['ma20'] < df['ma50']) & (df['ma20'].shift() >= df['ma50'].shift()), 'signal'] = -1
        
        df['position'] = df['signal'].shift()
        df['strategy_return'] = df['position'] * df['price_change'] / 100
        
        return self._calculate_metrics(df)
    
    def _calculate_metrics(self, df):
        """计算回测指标"""
        total_return = (1 + df['strategy_return']).cumprod().iloc[-1] - 1
        daily_returns = df['strategy_return']
        
        win_trades = len(df[df['strategy_return'] > 0])
        total_trades = len(df[df['position'] != 0])
        win_rate = win_trades / total_trades if total_trades > 0 else 0
        
        volatility = daily_returns.std() * math.sqrt(252)
        sharpe_ratio = (daily_returns.mean() * 252) / volatility if volatility > 0 else 0
        
        cumulative = (1 + daily_returns).cumprod()
        max_drawdown = (cumulative / cumulative.cummax() - 1).min()
        
        return {
            'total_return': total_return,
            'annualized_return': (1 + total_return) ** (252 / len(df)) - 1,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'win_trades': win_trades,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'data_points': len(df)
        }
    
    def compare_strategies(self):
        """比较所有策略"""
        if not self.strategy_results:
            print("❌ 没有回测结果")
            return
        
        results = []
        for name, metrics in self.strategy_results.items():
            results.append({
                '策略': name,
                '总收益': f"{metrics['total_return']*100:.2f}%",
                '年化收益': f"{metrics['annualized_return']*100:.2f}%",
                '胜率': f"{metrics['win_rate']*100:.2f}%",
                '夏普比率': f"{metrics['sharpe_ratio']:.2f}",
                '最大回撤': f"{metrics['max_drawdown']*100:.2f}%",
                '交易次数': metrics['total_trades']
            })
        
        df = pd.DataFrame(results)
        print("\n" + "=" * 80)
        print("📊 策略对比结果")
        print("=" * 80)
        print(df.to_string(index=False))
        
        best_sharpe = max(self.strategy_results.items(), key=lambda x: x[1]['sharpe_ratio'])
        best_return = max(self.strategy_results.items(), key=lambda x: x[1]['total_return'])
        
        print(f"\n🏆 夏普比率最高: {best_sharpe[0]} ({best_sharpe[1]['sharpe_ratio']:.2f})")
        print(f"💰 总收益最高: {best_return[0]} ({best_return[1]['total_return']*100:.2f}%)")


def main():
    print("=" * 80)
    print("📈 黄金历史数据回测系统")
    print("=" * 80)
    
    backtester = GoldBacktester()
    
    print("\n【一】获取历史数据")
    print("-" * 80)
    backtester.fetch_historical_data(days=90)
    
    print("\n【二】回测策略")
    print("-" * 80)
    
    strategies = [
        ('moving_average_crossover', {'short_window': 20, 'long_window': 50}),
        ('rsi_strategy', {'oversold': 30, 'overbought': 70}),
        ('macd_strategy', {}),
        ('golden_cross', {})
    ]
    
    for name, params in strategies:
        print(f"\n🔄 回测 {name}...")
        result = backtester.backtest_strategy(name, params)
        
        if result:
            print(f"   ✅ 完成")
            print(f"   📊 总收益: {result['total_return']*100:.2f}%")
            print(f"   📈 年化收益: {result['annualized_return']*100:.2f}%")
            print(f"   🎯 胜率: {result['win_rate']*100:.2f}%")
            print(f"   📉 最大回撤: {result['max_drawdown']*100:.2f}%")
            print(f"   📈 夏普比率: {result['sharpe_ratio']:.2f}")
    
    print("\n【三】策略对比")
    print("-" * 80)
    backtester.compare_strategies()
    
    print("\n" + "=" * 80)
    print("✅ 回测完成")
    print("=" * 80)
    
    print("\n📋 数据摘要:")
    if backtester.historical_data:
        df = pd.DataFrame(backtester.historical_data)
        print(f"   • 数据条数: {len(df)}")
        print(f"   • 时间范围: {df['Date'].min().date()} 到 {df['Date'].max().date()}")
        print(f"   • 价格范围: ${df['close'].min():.2f} - ${df['close'].max():.2f}")


if __name__ == "__main__":
    main()