# OKX BTC 自动交易系统

## 快速开始

### 1. 配置环境
复制 `.env.example` 为 `.env`，填入API密钥：
```bash
OKX_API_KEY=你的OKX_API密钥
OKX_SECRET_KEY=你的OKX密钥
OKX_PASSPHRASE=你的OKX密码短语
DEEPSEEK_API_KEY=你的DeepSeek密钥
```

### 2. 运行
```bash
python run.py
```

## 核心特性

- **AI决策**: DeepSeek Reasoner分析K线数据
- **原始数据**: 直接发送OHLCV数据，让AI自主分析
- **自动交易**: 每15分钟自动检查并执行
- **风险控制**: AI信心度阈值过滤

## 系统架构

```
K线数据 → AI分析 → 交易决策 → 执行交易
  ↑                              ↓
  └──────── 15分钟循环 ←──────────┘
```

## 关键配置

- `AI_MIN_CONFIDENCE=60` - 只有信心≥60%才交易
- `OKX_SIMULATED=true` - 使用模拟盘（建议先测试）

## 文件结构

```
bot/
  ai_analyzer.py    # AI分析器（精简版）
  trader.py         # 交易执行
  database.py       # 数据存储
run.py             # 主程序
config.py          # 配置管理
```

## 注意事项

1. 先在模拟盘测试24小时
2. 查看 `logs/` 目录了解决策过程
3. 最小交易量：0.00001 BTC

---

版本: 3.0 (精简版)
