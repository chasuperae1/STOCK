import requests
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class NewsAPIClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
    
    def get_gold_news(self, days: int = 1) -> List[Dict]:
        if not self.api_key:
            return self._get_mock_news()
        
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        try:
            response = requests.get(
                f"{self.base_url}/everything",
                params={
                    "q": "gold OR gold price OR XAU",
                    "from": from_date,
                    "sortBy": "publishedAt",
                    "apiKey": self.api_key,
                    "language": "en"
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("articles", [])
        except Exception as e:
            print(f"Error fetching news: {e}")
            return self._get_mock_news()
    
    def _get_mock_news(self) -> List[Dict]:
        return [
            {
                "title": "Federal Reserve announces interest rate decision, gold prices surge",
                "description": "Gold prices rose 1.5% following the Fed's decision to maintain interest rates.",
                "publishedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": {"name": "Financial News"}
            },
            {
                "title": "Geopolitical tensions boost safe-haven demand for gold",
                "description": "Uncertainty in the Middle East drives investors towards gold.",
                "publishedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": {"name": "Market Watch"}
            },
            {
                "title": "Central bank gold purchases reach record levels",
                "description": "Global central banks continue to accumulate gold reserves.",
                "publishedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": {"name": "Bloomberg"}
            }
        ]


class SentimentAnalyzer:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.hf_api_url = "https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english"
    
    def analyze_sentiment(self, text: str) -> float:
        if not self.api_key:
            return self._analyze_mock_sentiment(text)
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            response = requests.post(
                self.hf_api_url,
                headers=headers,
                json={"inputs": text}
            )
            response.raise_for_status()
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0:
                label = result[0][0]["label"]
                score = result[0][0]["score"]
                return score if label == "POSITIVE" else -score
            return 0.0
        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return self._analyze_mock_sentiment(text)
    
    def _analyze_mock_sentiment(self, text: str) -> float:
        positive_keywords = ["surge", "boost", "rise", "increase", "record", "strong", "bullish", "up"]
        negative_keywords = ["drop", "fall", "decline", "plunge", "bearish", "down", "weak"]
        
        score = 0.0
        text_lower = text.lower()
        
        for keyword in positive_keywords:
            if keyword in text_lower:
                score += 0.2
        
        for keyword in negative_keywords:
            if keyword in text_lower:
                score -= 0.2
        
        return max(-1.0, min(1.0, score))


class EconomicCalendar:
    def __init__(self):
        self.events = []
    
    def get_todays_events(self) -> List[Dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        return self._get_mock_events(today)
    
    def _get_mock_events(self, date: str) -> List[Dict]:
        return [
            {
                "title": "US Non-Farm Payrolls",
                "time": "08:30 ET",
                "impact": "high",
                "actual": None,
                "forecast": "200K",
                "previous": "180K"
            },
            {
                "title": "Fed Interest Rate Decision",
                "time": "14:00 ET",
                "impact": "high",
                "actual": None,
                "forecast": "5.25%",
                "previous": "5.25%"
            },
            {
                "title": "CPI Inflation Data",
                "time": "08:30 ET",
                "impact": "medium",
                "actual": None,
                "forecast": "3.2%",
                "previous": "3.4%"
            }
        ]


class GoldPriceAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
    
    def get_current_price(self) -> float:
        try:
            import yfinance as yf
            gold = yf.Ticker("GC=F")
            data = gold.history(period="1d")
            if not data.empty:
                return data["Close"].iloc[-1]
        except:
            pass
        return self._get_mock_price()
    
    def _get_mock_price(self) -> float:
        import random
        return 2020.0 + random.uniform(-20, 20)


class EventAnalyzer:
    def __init__(self, news_api_key: str = None, sentiment_api_key: str = None):
        self.news_client = NewsAPIClient(news_api_key)
        self.sentiment_analyzer = SentimentAnalyzer(sentiment_api_key)
        self.economic_calendar = EconomicCalendar()
        self.gold_price = GoldPriceAPI()
    
    def analyze_todays_events(self) -> Dict[str, Any]:
        news = self.news_client.get_gold_news(days=1)
        events = self.economic_calendar.get_todays_events()
        current_price = self.gold_price.get_current_price()
        
        sentiment_scores = []
        for article in news:
            text = article.get("title", "") + " " + article.get("description", "")
            score = self.sentiment_analyzer.analyze_sentiment(text)
            sentiment_scores.append(score)
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        
        high_impact_events = [e for e in events if e["impact"] == "high"]
        medium_impact_events = [e for e in events if e["impact"] == "medium"]
        
        return {
            "current_price": current_price,
            "news_count": len(news),
            "avg_sentiment": avg_sentiment,
            "high_impact_events": high_impact_events,
            "medium_impact_events": medium_impact_events,
            "news_details": news,
            "sentiment_scores": sentiment_scores
        }