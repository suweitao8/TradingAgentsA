#!/usr/bin/env python3
"""
创建GitHub Release的脚本
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('scripts')


def run_command(command, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd,
            capture_output=True, 
            text=True, 
            encoding='utf-8'
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def create_release_notes():
    """创建发布说明"""
    release_notes = """
## 🚀 现代化全栈架构与多智能体分析

TradingAgentsA v1.0.1 带来全新的 FastAPI + Vue3 全栈架构，基于多智能体的 A 股深度分析平台！

### ✨ 主要特性

#### 🏗️ 现代化全栈架构
- ⚡ 后端 FastAPI（高性能异步 RESTful API）
- 🖥️ 前端 Vue 3 + Vite + Element Plus 单页应用
- 🗄️ MongoDB + Redis 双数据库架构
- 🐳 Docker 一键部署，开箱即用

#### 🤖 多智能体股票分析
- 📊 多智能体协作（市场/基本面/新闻/技术分析师 + 风险评估）
- 🇨🇳 中文增强，适配 A 股市场
- 📈 多数据源支持（Tushare / AKShare / BaoStock）
- 💡 支持 OpenAI 兼容协议的多家 LLM Provider

#### 🔧 工程化能力
- 📋 任务队列与 SSE 实时进度推送
- 🗓️ APScheduler 定时数据采集
- 💾 多级缓存（Redis + MongoDB）
- 📚 完整文档体系

### 🚀 快速开始

#### 1. 使用 Docker 一键启动（推荐）
```bash
# 克隆仓库
git clone https://github.com/hsliuping/TradingAgents-CN.git
cd TradingAgentsA

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API 密钥（LLM / 数据源）

# 一键启动全栈
docker-compose up -d
```

#### 2. 本地开发模式
```bash
# 安装后端依赖（pip + pyproject.toml）
pip install -e .

# 安装前端依赖（yarn）
cd frontend && yarn install

# 启动后端 API（端口 8000）
python -m uvicorn app.main:app --reload --port 8000

# 启动前端 dev server（端口 3000）
cd frontend && yarn dev
```

启动后访问前端：http://localhost:3000

### 📚 文档和支持

- 📖 [完整文档](./docs/)
- 🔧 [配置指南](./docs/configuration/)
- 🚀 [部署指南](./docs/deployment/)
- 🧪 [开发指南](./docs/development/)

### 🎯 推荐配置

- **LLM Provider**: 京东云 jdcloud（默认，模型 kimi-k2.5）
- **数据源**: Tushare（主）+ AKShare（兜底）
- **数据库**: MongoDB + Redis（Docker）

### 🙏 致谢

感谢 [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) 原始项目的开发者们，为金融AI领域提供了优秀的开源框架。

### 📄 许可证

核心多智能体框架遵循 Apache 2.0 许可证；FastAPI 后端与 Vue 前端为专有代码。

---

**🚀 立即体验**: `docker-compose up -d`
"""
    return release_notes.strip()

def show_release_info():
    """显示发布信息"""
    logger.info(f"🎉 TradingAgentsA v1.0.1 已成功发布到GitHub！")
    logger.info(f"=")

    logger.info(f"\n📋 发布内容:")
    logger.info(f"  🏗️ FastAPI + Vue3 现代化全栈架构")
    logger.info(f"  🤖 多智能体 A 股分析")
    logger.info(f"  🐳 Docker 一键部署")
    logger.info(f"  🧪 完整的测试体系")
    logger.info(f"  📚 详细的使用文档")

    logger.info(f"\n🔗 GitHub链接:")
    logger.info(f"  📦 Release: https://github.com/hsliuping/TradingAgents-CN/releases/tag/v1.0.1")
    logger.info(f"  📝 代码: https://github.com/hsliuping/TradingAgents-CN")

    logger.info(f"\n🚀 快速开始:")
    logger.info(f"  1. git clone https://github.com/hsliuping/TradingAgents-CN.git")
    logger.info(f"  2. cd TradingAgentsA")
    logger.info(f"  3. cp .env.example .env（编辑填入 API 密钥）")
    logger.info(f"  4. docker-compose up -d")

    logger.info(f"\n💡 主要特性:")
    logger.info(f"  ✅ 多智能体股票分析")
    logger.info(f"  ✅ FastAPI + Vue3 全栈")
    logger.info(f"  ✅ Docker 一键部署")
    logger.info(f"  ✅ 多分析师协作决策")
    logger.info(f"  ✅ 完整的中文支持")

def main():
    """主函数"""
    logger.info(f"🚀 创建GitHub Release")
    logger.info(f"=")
    
    # 检查是否在正确的分支
    success, stdout, stderr = run_command("git branch --show-current")
    if not success or stdout.strip() != "main":
        logger.error(f"❌ 请确保在main分支上，当前分支: {stdout.strip()}")
        return False
    
    # 检查是否有未推送的提交
    success, stdout, stderr = run_command("git status --porcelain")
    if not success:
        logger.error(f"❌ Git状态检查失败: {stderr}")
        return False
    
    if stdout.strip():
        logger.error(f"❌ 发现未提交的更改，请先提交所有更改")
        return False
    
    logger.info(f"✅ Git状态检查通过")
    
    # 检查标签是否存在
    success, stdout, stderr = run_command("git tag -l cn-v0.1.2")
    if not success or "cn-v0.1.2" not in stdout:
        logger.error(f"❌ 标签 cn-v0.1.2 不存在")
        return False
    
    logger.info(f"✅ 版本标签检查通过")
    
    # 生成发布说明
    release_notes = create_release_notes()
    
    # 保存发布说明到文件
    with open("RELEASE_NOTES_v0.1.2.md", "w", encoding="utf-8") as f:
        f.write(release_notes)
    
    logger.info(f"✅ 发布说明已生成")
    
    # 显示GitHub Release创建指南
    logger.info(f"\n📋 GitHub Release创建指南:")
    logger.info(f"=")
    logger.info(f"1. 访问: https://github.com/hsliuping/TradingAgents-CN/releases/new")
    logger.info(f"2. 选择标签: cn-v0.1.2")
    logger.info(f"3. 发布标题: TradingAgentsA v0.1.2 - Web管理界面和Google AI支持")
    logger.info(f"4. 复制 RELEASE_NOTES_v0.1.2.md 的内容到描述框")
    logger.info(f"5. 勾选 'Set as the latest release'")
    logger.info(f"6. 点击 'Publish release'")
    
    # 显示发布信息
    show_release_info()
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        logger.info(f"\n🎉 GitHub Release准备完成！")
        logger.info(f"请按照上述指南在GitHub上创建Release")
    else:
        logger.error(f"\n❌ GitHub Release准备失败")
        sys.exit(1)
