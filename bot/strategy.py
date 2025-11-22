"""交易策略"""
from typing import Optional


class TradingStrategy:
    """交易策略（记录持仓信息）"""
    
    def __init__(self):
        """初始化"""
        self.last_buy_price: Optional[float] = None
        self.last_trade_amount: Optional[float] = None
        self.position_opened = False
    
    def set_position(self, price: float, amount: float = None):
        """
        设置持仓信息
        :param price: 买入价格
        :param amount: 交易数量
        """
        self.last_buy_price = price
        self.position_opened = True
        
        if amount is not None:
            self.last_trade_amount = amount
    
    def clear_position(self):
        """清空持仓记录"""
        self.last_buy_price = None
        self.last_trade_amount = None
        self.position_opened = False
