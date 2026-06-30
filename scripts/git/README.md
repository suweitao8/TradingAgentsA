# Git Tools

## 目录说明

Git工具和工作流脚本

## 脚本列表

- `worktree.py` - **Worktree 隔离开发流程工具**（封装 AGENTS.md 的 worktree 管理）
- `branch_manager.py` - 分支管理
- `check_branch_overlap.py` - 分支重叠检查
- `upstream_git_workflow.sh` - 上游 Git 工作流
- `setup_fork_environment.sh` - 设置 Fork 环境

## worktree.py 使用方法

封装了 AGENTS.md 规定的 worktree 隔离开发流程，避免手敲命令出错。

```bash
# 创建隔离 worktree（建分支 + 三重验证 + 软链 node_modules）
python scripts/git/worktree.py create <task-name>

# 执行收尾流程（合并 → 推送 → 删 worktree → prune，9 步连续）
python scripts/git/worktree.py finish <task-name>

# 查看所有 worktree 状态
python scripts/git/worktree.py status

# finish 支持本地测试模式（不推送远程）
python scripts/git/worktree.py finish <task-name> --no-push
```

脚本内置 AGENTS.md 的全部检查：创建时三重验证（worktree list + toplevel + branch）、收尾时 status 干净确认 + merge/push 成功确认 + 残留检查。

## 注意事项

- 确保在项目根目录下运行脚本
- 检查脚本的依赖要求
- 某些脚本可能需要特殊权限
