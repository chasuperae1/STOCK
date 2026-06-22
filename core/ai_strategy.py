import pandas as pd
import numpy as np
from typing import Dict, Any
from .strategy import BaseStrategy, Signal
from .ai_api import EventAnalyzer


class AIEventDrivenStrategy(BaseStrategy):
    def __init__(self, event_engine, news_api_key=None, sentiment_api_key=None):
        super().__init__(event_engine)
        self.event_analyzer = EventAnalyzer(news_api_key, sentiment_api_key)
        self.set_params(
            sentiment_threshold=0.3,
            technical_weight=0.3,
            sentiment_weight=0.5,
            event_weight=0.2,
            min_confidence=0.6
        )
        self.last_analysis = None
    
    def calculate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < 60:
            return Signal(Signal.HOLD)
        
        event_analysis = self.event_analyzer.analyze_todays_events()
        self.last_analysis = event_analysis
        
        technical_score = self._calculate_technical_score(data)
        sentiment_score = event_analysis['avg_sentiment']
        event_score = self._calculate_event_score(event_analysis)
        
        combined_score = (
            technical_score * self.get_param('technical_weight') +
            sentiment_score * self.get_param('sentiment_weight') +
            event_score * self.get_param('event_weight')
        )
        
        confidence = min(abs(combined_score), 1.0)
        
        if combined_score > self.get_param('sentiment_threshold'):
            return Signal(Signal.LONG, price=data['close'].iloc[-1], confidence=confidence)
        elif combined_score < -self.get_param('sentiment_threshold'):
            return Signal(Signal.SHORT, price=data['close'].iloc[-1], confidence=confidence)
        
        return Signal(Signal.HOLD)
    
    def _calculate_technical_score(self, data: pd.DataFrame) -> float:
        data = data.copy()
        data['ma20'] = data['close'].rolling(20).mean()
        data['ma60'] = data['close'].rolling(60).mean()
        data['rsi'] = self._calculate_rsi(data['close'])
        
        latest = data.iloc[-1]
        
        score = 0.0
        
        if latest['close'] > latest['ma20']:
            score += 0.3
        if latest['ma20'] > latest['ma60']:
            score += 0.3
        
        if latest['rsi'] < 30:
            score += 0.4
        elif latest['rsi'] > 70:
            score -= 0.4
        
        return max(-1.0, min(1.0, score))
    
    def _calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_event_score(self, analysis: Dict[str, Any]) -> float:
        score = 0.0
        
        high_impact_count = len(analysis['high_impact_events'])
        medium_impact_count = len(analysis['medium_impact_events'])
        
        score += high_impact_count * 0.3
        score += medium_impact_count * 0.15
        
        for event in analysis['high_impact_events']:
            event_title = event['title'].lower()
            if 'fed' in event_title or 'interest rate' in event_title:
                score += 0.2
            if 'cpi' in event_title or 'inflation' in event_title:
                score += 0.15
            if 'payroll' in event_title:
                score += 0.1
        
        return max(-1.0, min(1.0, score))
    
    def get_analysis_report(self) -> Dict[str, Any]:
        if self.last_analysis is None:
            return {"error": "No analysis performed yet"}
        
        return {
            "current_price": self.last_analysis['current_price'],
            "sentiment_summary": self._get_sentiment_summary(),
            "event_summary": self._get_event_summary(),
            "news_summary": self._get_news_summary()
        }
    
    def _get_sentiment_summary(self) -> Dict[str, Any]:
        if self.last_analysis is None:
            return {}
        
        sentiment = self.last_analysis['avg_sentiment']
        if sentiment > 0.2:
            return {"status": "bullish", "score": sentiment, "description": "Positive news sentiment favors buying"}
        elif sentiment < -0.2:
            return {"status": "bearish", "score": sentiment, "description": "Negative news sentiment favors selling"}
        else:
            return {"status": "neutral", "score": sentiment, "description": "Neutral news sentiment"}
    
    def _get_event_summary(self) -> Dict[str, Any]:
        if self.last_analysis is None:
            return {}
        
        high_events = self.last_analysis['high_impact_events']
        medium_events = self.last_analysis['medium_impact_events']
        
        return {
            "high_impact_count": len(high_events),
            "medium_impact_count": len(medium_events),
            "events": [event['title'] for event in high_events + medium_events]
        }
    
    def _get_news_summary(self) -> Dict[str, Any]:
        if self.last_analysis is None:
            return {}
        
        news = self.last_analysis['news_details']
        return {
            "count": len(news),
            "headlines": [article['title'] for article in news[:5]]
        }


class GameTheoryStrategy(BaseStrategy):
    def __init__(self, event_engine):
        super().__init__(event_engine)
        self.set_params(
            herding_threshold=0.7,
            contrarian_threshold=-0.5,
            volume_spike_multiplier=2.0
        )
        self.price_history = []
        self.volume_history = []
    
    def calculate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < 20:
            return Signal(Signal.HOLD)
        
        self.price_history.append(data['close'].iloc[-1])
        self.volume_history.append(data['volume'].iloc[-1])
        
        if len(self.price_history) > 20:
            self.price_history.pop(0)
            self.volume_history.pop(0)
        
        herding_score = self._detect_herding_behavior(data)
        contrarian_score = self._detect_contrarian_opportunity(data)
        volume_signal = self._analyze_volume_spike(data)
        
        combined_score = herding_score + contrarian_score + volume_signal
        confidence = min(abs(combined_score), 1.0)
        
        if combined_score > 0.3:
            return Signal(Signal.LONG, price=data['close'].iloc[-1], confidence=confidence)
        elif combined_score < -0.3:
            return Signal(Signal.SHORT, price=data['close'].iloc[-1], confidence=confidence)
        
        return Signal(Signal.HOLD)
    
    def _detect_herding_behavior(self, data: pd.DataFrame) -> float:
        recent_returns = data['close'].pct_change().tail(5)
        avg_return = recent_returns.mean()
        std_return = recent_returns.std()
        
        if std_return == 0:
            return 0.0
        
        z_score = abs(avg_return / std_return)
        
        if z_score > 2 and avg_return > 0:
            return -0.5
        elif z_score > 2 and avg_return < 0:
            return 0.5
        
        return 0.0
    
    def _detect_contrarian_opportunity(self, data: pd.DataFrame) -> float:
        rsi = self._calculate_rsi(data['close'])
        latest_rsi = rsi.iloc[-1]
        
        if latest_rsi < 25:
            return 0.6
        elif latest_rsi > 75:
            return -0.6
        
        return 0.0
    
    def _calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _analyze_volume_spike(self, data: pd.DataFrame) -> float:
        avg_volume = data['volume'].rolling(20).mean().iloc[-1]
        current_volume = data['volume'].iloc[-1]
        
        if current_volume > avg_volume * self.get_param('volume_spike_multiplier'):
            recent_trend = data['close'].pct_change().tail(3).mean()
            if recent_trend > 0:
                return 0.3
            else:
                return -0.3
        
        return 0.0