#!/usr/bin/env python3
"""智能图片搜索引擎 - 启动入口"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from api.main import app
    uvicorn.run(app, host="0.0.0.0", port=8000)
