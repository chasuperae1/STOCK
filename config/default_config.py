DEFAULT_CONFIG = {
    'data': {
        'default_symbol': 'gold',
        'default_start_date': '2020-01-01',
        'default_interval': '1d',
        'cache_enabled': True,
        'cache_expire_hours': 24
    },
    
    'backtest': {
        'initial_capital': 100000.0,
        'transaction_cost': 0.001,
        'slippage': 0.0005
    },
    
    'risk': {
        'max_position_size': 0.1,
        'max_drawdown': 0.2,
        'daily_loss_limit': 0.02
    },
    
    'strategy': {
        'trend_following': {
            'short_window': 20,
            'long_window': 60,
            'confirmation_threshold': 0.01
        },
        'mean_reversion': {
            'window': 20,
            'std_dev': 2.0,
            'revert_threshold': 0.5
        },
        'grid_trading': {
            'grid_count': 10,
            'grid_range': 0.10,
            'position_limit': 10
        },
        'multi_factor': {
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'macd_signal_threshold': 0,
            'ma_trend_weight': 0.3,
            'rsi_weight': 0.3,
            'macd_weight': 0.4
        }
    },
    
    'logging': {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_path': 'gold_quant.log'
    }
}


class Config:
    def __init__(self, config_dict=None):
        if config_dict is None:
            self._config = DEFAULT_CONFIG
        else:
            self._config = config_dict
    
    def get(self, key_path, default=None):
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path, value):
        keys = key_path.split('.')
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
    
    def get_data_config(self):
        return self._config.get('data', {})
    
    def get_backtest_config(self):
        return self._config.get('backtest', {})
    
    def get_risk_config(self):
        return self._config.get('risk', {})
    
    def get_strategy_config(self, strategy_name):
        return self._config.get('strategy', {}).get(strategy_name, {})