import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class GoldData:
    SYMBOLS = {
        "gold": "GC=F",
        "gold_etf": "GLD",
        "silver": "SI=F",
        "dollar": "^DXY",
        "vix": "^VIX",
        "spy": "SPY"
    }

    def __init__(self):
        self._data_cache: Dict[str, pd.DataFrame] = {}

    def fetch_gold_data(
        self,
        symbol: str = "gold",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        yf_symbol = self.SYMBOLS.get(symbol, symbol)
        
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        cache_key = f"{symbol}_{start_date}_{end_date}_{interval}"
        if cache_key in self._data_cache:
            return self._data_cache[cache_key]

        try:
            data = yf.download(yf_symbol, start=start_date, end=end_date, interval=interval)
            data = data[["Open", "High", "Low", "Close", "Volume"]]
            data.columns = ["open", "high", "low", "close", "volume"]
            data.index.name = "datetime"
            
            self._data_cache[cache_key] = data
            return data
        except Exception as e:
            raise RuntimeError(f"Failed to fetch gold data: {e}")

    def get_multiple_data(self, symbols: list, **kwargs) -> Dict[str, pd.DataFrame]:
        result = {}
        for symbol in symbols:
            result[symbol] = self.fetch_gold_data(symbol, **kwargs)
        return result

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        
        data['ma20'] = data['close'].rolling(20).mean()
        data['ma60'] = data['close'].rolling(60).mean()
        data['ma200'] = data['close'].rolling(200).mean()
        
        data['rsi'] = self._calculate_rsi(data['close'])
        data['atr'] = self._calculate_atr(data)
        
        data['bb_upper'], data['bb_middle'], data['bb_lower'] = self._calculate_bollinger(data['close'])
        
        data['macd'], data['signal'], data['hist'] = self._calculate_macd(data['close'])
        
        return data.dropna()

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = data['high'] - data['low']
        high_close = (data['high'] - data['close'].shift()).abs()
        low_close = (data['low'] - data['close'].shift()).abs()
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr

    def _calculate_bollinger(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> tuple:
        middle = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    def _calculate_macd(self, prices: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> tuple:
        ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
        ema_slow = prices.ewm(span=slow_period, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist