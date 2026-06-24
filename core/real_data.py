#!/usr/bin/env python3
"""
真实历史数据获取模块
===================

**核心原则**：严禁使用模拟数据，必须使用真实API数据

数据源：
    1. 新浪财经K线接口（主）
    2. 腾讯财经K线接口（备）

使用说明：
    from core.real_data import RealGoldETFData
    
    data = RealGoldETFData()
    df = data.fetch_history(days=250)
    
    # 检查是否为真实数据
    if data.is_real_data:
        print("✅ 使用真实数据")
    else:
        print("❌ 无法获取真实数据")
"""

import requests
import pandas as pd
import json
from datetime import datetime
from typing import Optional, Dict, List


class RealGoldETFData:
    """
    518880华安黄金ETF真实历史数据获取
    
    严禁使用模拟数据，必须从真实API获取
    """
    
    def __init__(self, code: str = '518880', market: str = 'sh'):
        """
        初始化
        
        参数:
            code: ETF代码，默认518880
            market: 市场，sh=沪市
        """
        self.code = code
        self.market = market
        self.full_code = f"{market}{code}"
        self.is_real_data = False
        self.data_source = ""
        self.data = None
    
    def _fetch_sina(self, days: int = 250) -> Optional[pd.DataFrame]:
        """
        从新浪财经获取历史K线数据
        
        参数:
            days: 获取天数
        
        返回:
            DataFrame，包含 date, open, high, low, close, volume
        """
        url = "https://quotes.sina.cn/cn/api/jsonp_v2.php/=/CN_MarketDataService.getKLineData"
        params = {
            'symbol': self.full_code,
            'scale': 240,  # 日线
            'ma': 'no',
            'datalen': days
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                return None
            
            text = resp.text
            
            # 解析JSONP
            if '(' not in text or ')' not in text:
                return None
            
            json_str = text[text.index('(')+1:text.rindex(')')]
            data = json.loads(json_str)
            
            if not isinstance(data, list) or len(data) == 0:
                return None
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            df = df.rename(columns={
                'day': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # 确保数值类型
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna()
            df = df.sort_values('date').reset_index(drop=True)
            
            self.is_real_data = True
            self.data_source = "新浪财经"
            
            return df
            
        except Exception as e:
            print(f"❌ 新浪财经获取失败: {e}")
            return None
    
    def _fetch_tencent(self, days: int = 250) -> Optional[pd.DataFrame]:
        """
        从腾讯财经获取历史K线数据
        
        参数:
            days: 获取天数
        
        返回:
            DataFrame
        """
        url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        params = {
            'param': f'{self.full_code},day,,,{days},qfq'
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            
            if data.get('code') != 0:
                return None
            
            stock_data = data.get('data', {}).get(self.full_code, {})
            klines = stock_data.get('qfqday') or stock_data.get('day', [])
            
            if not klines or len(klines) == 0:
                return None
            
            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=['date', 'open', 'close', 'high', 'low', 'volume', 'other'])
            
            # 确保数值类型
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna()
            df = df.sort_values('date').reset_index(drop=True)
            
            self.is_real_data = True
            self.data_source = "腾讯财经"
            
            return df
            
        except Exception as e:
            print(f"❌ 腾讯财经获取失败: {e}")
            return None
    
    def fetch_history(self, days: int = 250, force_real: bool = True) -> Optional[pd.DataFrame]:
        """
        获取真实历史数据
        
        **核心原则**：默认强制使用真实数据，失败则返回None
        
        参数:
            days: 获取天数，默认250天（约1年）
            force_real: 是否强制真实数据，True=失败返回None，False=不允许
        
        返回:
            DataFrame，失败返回None
        
        注意:
            绝不返回模拟数据！如果所有API都失败，直接返回None
        """
        print(f"📊 正在获取 {self.code} 历史K线数据 ({days}天)...")
        
        # 尝试新浪财经
        print("  尝试新浪财经...", end=" ")
        df = self._fetch_sina(days)
        if df is not None:
            print(f"✅ 成功！获取到 {len(df)} 条数据")
            self.data = df
            return df
        print("❌ 失败")
        
        # 尝试腾讯财经
        print("  尝试腾讯财经...", end=" ")
        df = self._fetch_tencent(days)
        if df is not None:
            print(f"✅ 成功！获取到 {len(df)} 条数据")
            self.data = df
            return df
        print("❌ 失败")
        
        # 所有API都失败
        print(f"\n❌ 无法获取真实历史数据")
        print(f"   已尝试: 新浪财经、腾讯财经")
        print(f"   建议:")
        print(f"     1. 检查网络连接")
        print(f"     2. 稍后重试")
        print(f"     3. 手动提供数据文件")
        
        self.is_real_data = False
        return None
    
    def get_data_info(self) -> Dict:
        """
        获取数据信息
        """
        if self.data is None:
            return {'status': 'no_data'}
        
        return {
            'status': 'ok',
            'is_real_data': self.is_real_data,
            'data_source': self.data_source,
            'rows': len(self.data),
            'start_date': self.data['date'].iloc[0],
            'end_date': self.data['date'].iloc[-1],
            'start_price': self.data['close'].iloc[0],
            'end_price': self.data['close'].iloc[-1],
            'total_return': (self.data['close'].iloc[-1] / self.data['close'].iloc[0] - 1) * 100
        }


# =============================================================================
# 快速测试
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("📊 真实历史数据获取测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    data = RealGoldETFData('518880', 'sh')
    df = data.fetch_history(days=120)  # 获取120天数据
    
    if df is not None:
        print(f"\n✅ 数据获取成功！")
        info = data.get_data_info()
        print(f"数据源: {info['data_source']}")
        print(f"数据条数: {info['rows']} 条")
        print(f"起始日期: {info['start_date']}")
        print(f"结束日期: {info['end_date']}")
        print(f"起始价格: ¥{info['start_price']:.3f}")
        print(f"结束价格: ¥{info['end_price']:.3f}")
        print(f"区间涨幅: {info['total_return']:+.2f}%")
        print(f"\n数据样例:")
        print(df.tail(5).to_string(index=False))
    else:
        print("\n❌ 无法获取数据")
    
    print("\n" + "=" * 60)