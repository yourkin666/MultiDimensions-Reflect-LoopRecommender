#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多维度反思循环推荐系统 - 主入口
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from sanic import Sanic
from sanic_ext import Extend

from src.api.recommendation_api import setup_routes
from src.utils.logger_config import setup_logger

# 加载环境变量
load_dotenv()

# 设置日志
log_file = os.getenv("LOG_FILE", f"logs/app_{datetime.now().strftime('%Y%m%d')}.log")
setup_logger(log_level=os.getenv("LOG_LEVEL", "INFO"), log_file=log_file)

# 创建Sanic应用
app = Sanic("MultiDimensionReflectRecommender")
Extend(app)

# 设置路由
setup_routes(app)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        debug=bool(os.getenv("DEBUG", False)),
        auto_reload=bool(os.getenv("AUTO_RELOAD", False))
    ) 