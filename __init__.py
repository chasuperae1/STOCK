from .core.event import Event, EventEngine, EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_POSITION, EVENT_ACCOUNT, EVENT_LOG, EVENT_STRATEGY_SIGNAL
from .core.data import GoldData
from .core.strategy import Signal, BaseStrategy, TrendFollowingStrategy, MeanReversionStrategy, GridTradingStrategy, MultiFactorStrategy
from .core.ai_strategy import AIEventDrivenStrategy, GameTheoryStrategy
from .core.ai_api import NewsAPIClient, SentimentAnalyzer, EconomicCalendar, GoldPriceAPI, EventAnalyzer
from .core.backtest import BackTester, BackTestResult
from .core.portfolio import Portfolio, Position, RiskManager
from .config.default_config import Config, DEFAULT_CONFIG

__all__ = [
    'Event',
    'EventEngine',
    'EVENT_TICK',
    'EVENT_ORDER',
    'EVENT_TRADE',
    'EVENT_POSITION',
    'EVENT_ACCOUNT',
    'EVENT_LOG',
    'EVENT_STRATEGY_SIGNAL',
    'GoldData',
    'Signal',
    'BaseStrategy',
    'TrendFollowingStrategy',
    'MeanReversionStrategy',
    'GridTradingStrategy',
    'MultiFactorStrategy',
    'AIEventDrivenStrategy',
    'GameTheoryStrategy',
    'NewsAPIClient',
    'SentimentAnalyzer',
    'EconomicCalendar',
    'GoldPriceAPI',
    'EventAnalyzer',
    'BackTester',
    'BackTestResult',
    'Portfolio',
    'Position',
    'RiskManager',
    'Config',
    'DEFAULT_CONFIG'
]

__version__ = '1.0.0'