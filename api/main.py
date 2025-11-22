"""
Web API
提供监控面板数据接口
"""
from fastapi import FastAPI, Header, HTTPException, Depends, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import Config
from bot import Database, OKXTrader

app = FastAPI(title="AI炒币监控面板")

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
db = Database(Config.DATABASE_PATH)

# 初始化交易器（仅用于查询）
trader = OKXTrader(
    Config.OKX_API_KEY,
    Config.OKX_SECRET_KEY,
    Config.OKX_PASSPHRASE,
    Config.OKX_SIMULATED
)


def verify_panel_token(x_panel_token: str = Header(default=None)):
    """简单的Header Token校验"""
    if Config.PANEL_TOKEN:
        if x_panel_token != Config.PANEL_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized"
            )
    return True


@app.get("/")
async def root():
    """返回监控面板HTML"""
    with open("web/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/api/balance", dependencies=[Depends(verify_panel_token)])
async def get_balance():
    """获取账户余额（包含平均成本价和盈亏）"""
    balance = trader.get_balance()
    if not balance['success']:
        return {"success": False, "error": balance.get('error')}
    
    # 获取当前价格
    price = trader.get_ticker(Config.TRADING_SYMBOL)
    
    total_value = 0
    if price:
        total_value = balance['btc'] * price + balance['usdt']
    
    # 获取平均成本价（从成交记录计算）
    avg_cost_data = trader.get_spot_avg_cost(Config.TRADING_SYMBOL, balance['btc'])
    avg_cost = 0
    unrealized_pnl = 0
    unrealized_pnl_percent = 0
    
    if avg_cost_data['success'] and avg_cost_data.get('avg_price', 0) > 0:
        avg_cost = avg_cost_data['avg_price']
        if price and balance['btc'] > 0:
            unrealized_pnl = (price - avg_cost) * balance['btc']
            unrealized_pnl_percent = ((price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0
    
    return {
        "success": True,
        "usdt": round(balance['usdt'], 2),
        "btc": round(balance['btc'], 8),  # 改为8位小数，BTC标准精度
        "btc_price": round(price, 2) if price else 0,
        "total_value": round(total_value, 2),
        "avg_cost": round(avg_cost, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "unrealized_pnl_percent": round(unrealized_pnl_percent, 2)
    }


@app.get("/api/trades", dependencies=[Depends(verify_panel_token)])
async def get_trades(limit: int = 10):
    """获取最近交易记录"""
    trades = db.get_recent_trades(limit)
    return {"success": True, "trades": trades}


@app.get("/api/statistics", dependencies=[Depends(verify_panel_token)])
async def get_statistics():
    """获取统计数据（包含历史表现）"""
    stats = db.get_statistics()
    performance = db.get_recent_performance(20)  # 最近20笔
    
    # 合并基础统计和历史表现
    stats.update({
        'win_rate': performance.get('win_rate', 0),
        'recent_profit': performance.get('total_profit', 0),
        'best_trade': performance.get('best_trade'),
        'worst_trade': performance.get('worst_trade')
    })
    
    return {"success": True, "statistics": stats}


@app.get("/api/status", dependencies=[Depends(verify_panel_token)])
async def get_status():
    """获取最新状态"""
    status = db.get_latest_status()
    return {"success": True, "status": status}


@app.get("/api/config", dependencies=[Depends(verify_panel_token)])
async def get_config():
    """获取配置信息"""
    return {
        "success": True,
        "config": {
            "symbol": Config.TRADING_SYMBOL,
            "max_trading_amount": Config.MAX_TRADING_AMOUNT,
            "max_position_percent": Config.MAX_POSITION_PERCENT,
            "max_stop_loss": Config.MAX_STOP_LOSS_PERCENT,
            "min_take_profit": Config.MIN_TAKE_PROFIT_PERCENT,
            "check_mode": "K线对齐（15m K线结束前2分钟）",
            "simulated": Config.OKX_SIMULATED
        }
    }


if __name__ == "__main__":
    import uvicorn
    print(f"启动Web服务: http://localhost:{Config.WEB_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=Config.WEB_PORT)
