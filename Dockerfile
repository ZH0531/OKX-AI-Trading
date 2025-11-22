FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --index-url https://pypi.tuna.tsinghua.edu.cn/simple --timeout 300 -r requirements.txt

# 复制项目文件
COPY . .

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 暴露端口（如果有Web面板）
EXPOSE 8000

# 默认运行交易机器人
CMD ["python", "run.py"]
