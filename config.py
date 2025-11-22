"""配置管理"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """系统配置"""
    
    # OKX配置
    OKX_API_KEY = os.getenv('OKX_API_KEY', '')
    OKX_SECRET_KEY = os.getenv('OKX_SECRET_KEY', '')
    OKX_PASSPHRASE = os.getenv('OKX_PASSPHRASE', '')
    OKX_SIMULATED = os.getenv('OKX_SIMULATED', 'true').lower() == 'true'
    
    # DeepSeek配置
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    
    # 交易配置
    TRADING_SYMBOL = os.getenv('TRADING_SYMBOL', 'BTC-USDT')
    # 以下改为最大限制值，实际值由AI决定
    MAX_TRADING_AMOUNT = float(os.getenv('MAX_TRADING_AMOUNT', '0.01'))  # 最大交易BTC数量
    MAX_POSITION_PERCENT = float(os.getenv('MAX_POSITION_PERCENT', '30'))  # 最大仓位百分比
    MAX_STOP_LOSS_PERCENT = float(os.getenv('MAX_STOP_LOSS_PERCENT', '5.0'))  # 最大止损百分比
    MIN_TAKE_PROFIT_PERCENT = float(os.getenv('MIN_TAKE_PROFIT_PERCENT', '1.0'))  # 最小止盈百分比
    
    # 运行配置
    # CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # 已废弃：现使用K线对齐检查
    WEB_PORT = int(os.getenv('WEB_PORT', '8000'))
    
    # 监控配置
    ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
    METRICS_PORT = int(os.getenv('METRICS_PORT', '9090'))
    
    # 日志配置
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'  # 打印AI完整提示词到控制台
    LOG_AI_DECISIONS = os.getenv('LOG_AI_DECISIONS', 'true').lower() == 'true'  # 记录所有AI决策到日志
    
    # AI配置
    AI_MIN_CONFIDENCE = int(os.getenv('AI_MIN_CONFIDENCE', '60'))  # AI最低信心阈值
    
    # 代理配置
    USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'
    HTTP_PROXY = os.getenv('HTTP_PROXY', 'http://127.0.0.1:7890')
    HTTPS_PROXY = os.getenv('HTTPS_PROXY', 'http://127.0.0.1:7890')
    
    # 数据库配置（模拟盘和实盘使用不同数据库）
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _db_name = 'trading_simulated.db' if OKX_SIMULATED else 'trading_live.db'
    DATABASE_PATH = os.path.join(BASE_DIR, 'data', _db_name)

    # 面板访问保护
    PANEL_TOKEN = os.getenv('PANEL_TOKEN', '')
    
    @classmethod
    def validate_config(cls):
        """验证配置是否完整"""
        errors = []
        
        if not cls.OKX_API_KEY:
            errors.append('OKX_API_KEY未配置')
        if not cls.OKX_SECRET_KEY:
            errors.append('OKX_SECRET_KEY未配置')
        if not cls.OKX_PASSPHRASE:
            errors.append('OKX_PASSPHRASE未配置')
        if not cls.DEEPSEEK_API_KEY:
            errors.append('DEEPSEEK_API_KEY未配置')
            
        return errors
    
    @classmethod
    def print_config(cls):
        """打印配置信息"""
        print("=" * 50)
        print("系统配置:")
        print(f"  交易对: {cls.TRADING_SYMBOL}")
        print(f"  最大交易量: {cls.MAX_TRADING_AMOUNT} BTC")
        print(f"  最大仓位: {cls.MAX_POSITION_PERCENT}%")
        print(f"  AI信心阈值: {cls.AI_MIN_CONFIDENCE}%")
        print(f"  检查方式: 每15分钟K线结束后2分钟内")
        print(f"  模拟盘: {'是' if cls.OKX_SIMULATED else '否'}")
        print(f"  调试模式: {'是' if cls.DEBUG_MODE else '否'}")
        print("=" * 50)
