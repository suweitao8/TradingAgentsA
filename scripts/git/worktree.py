#!/usr/bin/env python3
"""
Git Worktree 管理工具

封装 AGENTS.md 中规定的 worktree 隔离开发流程，降低每次手敲命令出错的概率。
提供三个子命令：

  create  创建隔离 worktree（建分支 + 三重验证 + 软链 node_modules）
  finish  执行收尾流程（合并 → 推送 → 删 worktree → prune，9 步连续）
  status  查看所有 worktree 状态（含未提交改动、分支、合并状态）

用法：
  python scripts/git/worktree.py create <task-name> [--base main]
  python scripts/git/worktree.py finish <task-name>
  python scripts/git/worktree.py status

设计依据：AGENTS.md「worktree 管理」章节的全部规则。
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _resolve_main_repo_root() -> Path:
    """获取主仓库根目录（无论脚本在主仓库还是 worktree 内执行）。

    worktree 的 git rev-parse --show-toplevel 返回的是 worktree 自己的路径，
    而 git rev-parse --git-common-dir 返回主仓库的 .git 目录，取其父目录即主仓库根。
    """
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        capture_output=True, text=True, check=True, encoding="utf-8", errors="replace"
    )
    git_dir = Path(result.stdout.strip()).resolve()
    return git_dir.parent


# 主仓库根目录（动态获取，确保 worktree 内执行也能定位到主仓库）
REPO_ROOT = _resolve_main_repo_root()
WORKTREES_DIR = REPO_ROOT / ".worktrees"

# ANSI 颜色（Windows 10+ 终端支持）
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


def run(cmd: list, cwd: Optional[Path] = None, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """运行命令，失败时抛出 SystemExit 并打印红色错误。"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=capture, text=True, check=check, encoding="utf-8", errors="replace"
        )
        return result
    except subprocess.CalledProcessError as e:
        stderr = e.stderr or e.stdout or ""
        print(f"{RED}❌ 命令执行失败: {' '.join(cmd)}{RESET}")
        if stderr.strip():
            print(f"{RED}   {stderr.strip()}{RESET}")
        raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"{GREEN}✅ {msg}{RESET}")


def warn(msg: str) -> None:
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def info(msg: str) -> None:
    print(f"{CYAN}ℹ️  {msg}{RESET}")


def fail(msg: str) -> None:
    """打印错误并退出。"""
    print(f"{RED}❌ {msg}{RESET}")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# create 子命令
# ---------------------------------------------------------------------------

def cmd_create(args: argparse.Namespace) -> None:
    """创建隔离 worktree + 三重验证 + 软链 node_modules。"""
    task = args.task
    base = args.base
    branch = f"feat/{task}"
    wt_path = WORKTREES_DIR / task

    info(f"创建 worktree: {wt_path}（分支 {branch}，基于 {base}）")

    # 0. 前置检查：目标路径不能已存在
    if wt_path.exists():
        fail(f"目标路径已存在: {wt_path}。如需复用请先 finish 旧任务，或手动清理。")

    # 1. 从 main 建隔离 worktree
    run(["git", "worktree", "add", str(wt_path), "-b", branch, base], cwd=REPO_ROOT)
    info(f"git worktree add 完成")

    # 2. 三重验证（AGENTS.md 铁律：add 返回成功 ≠ worktree 已注册）
    verify_worktree_registered(task, wt_path, branch)
    ok(f"三重验证通过：worktree 已正确注册")

    # 3. 软链前端 node_modules（Windows junction）
    frontend_nm = wt_path / "frontend" / "node_modules"
    main_nm = REPO_ROOT / "frontend" / "node_modules"
    if main_nm.exists() and not frontend_nm.exists():
        # Windows 用 mklink /J 创建目录联接（junction）
        frontend_nm.parent.mkdir(parents=True, exist_ok=True)
        # 相对路径：从 wt_path/frontend 指回主仓库 frontend/node_modules
        ret = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(frontend_nm), str(main_nm)],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if ret.returncode == 0:
            ok(f"已软链 frontend/node_modules（junction）")
        else:
            warn(f"软链 node_modules 失败（可忽略，后续手动 yarn install）: {ret.stderr.strip()}")

    # 4. 输出后续指引
    print()
    ok(f"worktree 创建成功")
    info(f"下一步：cd {wt_path}")
    info(f"验证：git -C {wt_path} rev-parse --show-toplevel")


def verify_worktree_registered(task: str, wt_path: Path, expected_branch: str) -> None:
    """三重验证 worktree 已注册（AGENTS.md 强制规则）。任一失败即 fail。"""
    # ① worktree list 能看到
    result = run(["git", "worktree", "list"], cwd=REPO_ROOT)
    if str(wt_path) not in result.stdout and wt_path.as_posix() not in result.stdout:
        fail(f"三重验证①失败：git worktree list 看不到 {wt_path}（add 可能未注册）")

    # ② toplevel 指向 worktree 路径
    result = run(["git", "-C", str(wt_path), "rev-parse", "--show-toplevel"])
    toplevel = result.stdout.strip().replace("/", "\\")
    expected = str(wt_path).replace("/", "\\")
    if toplevel.lower() != expected.lower():
        fail(f"三重验证②失败：toplevel={toplevel}，期望={expected}（shell cwd 可能漂移）")

    # ③ 分支名正确
    result = run(["git", "-C", str(wt_path), "branch", "--show-current"])
    actual_branch = result.stdout.strip()
    if actual_branch != expected_branch:
        fail(f"三重验证③失败：分支={actual_branch}，期望={expected_branch}")


# ---------------------------------------------------------------------------
# finish 子命令
# ---------------------------------------------------------------------------

def cmd_finish(args: argparse.Namespace) -> None:
    """执行收尾流程：合并 → 推送 → 删 worktree → prune（9 步连续不可分割）。"""
    task = args.task
    branch = f"feat/{task}"
    wt_path = WORKTREES_DIR / task

    info(f"开始收尾任务: {task}")

    # 前置检查：worktree 必须存在
    if not wt_path.exists():
        fail(f"worktree 不存在: {wt_path}")

    # 步骤1：在 worktree 内确认所有改动已提交
    info("步骤1/9：检查 worktree 内是否有未提交改动")
    result = run(["git", "status", "--porcelain"], cwd=wt_path)
    if result.stdout.strip():
        fail(f"worktree 内有未提交改动，请先提交或 stash：\n{result.stdout.strip()}")

    # 步骤2：切回主工作区
    info("步骤2/9：切回主工作区")
    run(["git", "-C", str(REPO_ROOT), "checkout", "main"], cwd=REPO_ROOT)

    # 步骤3：确认在 main 分支（步骤2已 checkout，这里验证）
    info("步骤3/9：确认在 main 分支")
    result = run(["git", "branch", "--show-current"], cwd=REPO_ROOT)
    if result.stdout.strip() != "main":
        fail(f"步骤3失败：当前分支={result.stdout.strip()}，期望 main")

    # 主工作区若有未提交改动，stash 保护（不影响合并）
    stash_needed = False
    status_result = run(["git", "status", "--porcelain"], cwd=REPO_ROOT)
    if status_result.stdout.strip():
        warn(f"主工作区有未提交改动，自动 stash 保护")
        run(["git", "stash", "push", "-u", "-m", f"auto-stash-before-finish-{task}"], cwd=REPO_ROOT)
        stash_needed = True

    # 步骤4：合并（保留分支历史）
    info(f"步骤4/9：git merge --no-ff {branch}")
    merge_result = run(
        ["git", "merge", "--no-ff", branch, "-m", f"merge: 合并 {task}"],
        cwd=REPO_ROOT
    )
    ok(f"合并成功")

    # 恢复 stash（如果之前 stash 了）
    if stash_needed:
        info("恢复之前 stash 的主工作区改动")
        run(["git", "stash", "pop"], cwd=REPO_ROOT)

    # 步骤5：推送
    if args.no_push:
        warn("步骤5/9：跳过推送（--no-push）→ ⚠️ 未推送到远程，保留 worktree 和分支以便后续推送")
        ok(f"任务 {task} 本地收尾完成（仅合并到本地 main，未推送、未清理）")
        info(f"后续推送：cd {REPO_ROOT} && git push origin main")
        info(f"推送后再清理：python scripts/git/worktree.py finish {task}（不带 --no-push）")
        return  # --no-push 模式只到合并为止，不删 worktree/分支，避免丢代码
    else:
        info("步骤5/9：git push origin main")
        run(["git", "push", "origin", "main"], cwd=REPO_ROOT)
        ok(f"推送成功")

    # 步骤6：删 worktree（删除前安全检查已在步骤1确认 status 干净、步骤4确认 merge、步骤5确认 push）
    # 6.1 额外机械验证①：分支提交已全部在 main 上（防 merge 后某提交被遗漏）
    info("步骤6.1：验证功能分支提交已全部进入 main")
    ahead = run(
        ["git", "rev-list", "--count", f"{branch}..main"],
        cwd=REPO_ROOT, check=False
    )
    # branch..main 为空说明 main 包含 branch 的所有提交（main 领先于 branch，无遗漏）
    # 更准确：检查 main..branch 是否有未合并提交（应为 0）
    behind_check = run(
        ["git", "rev-list", "--count", f"main..{branch}"],
        cwd=REPO_ROOT, check=False
    )
    behind_count = int(behind_check.stdout.strip() or "0")
    if behind_count > 0:
        fail(f"步骤6.1失败：分支 {branch} 仍有 {behind_count} 个提交未进入 main，禁止删除（会丢代码）")

    # 6.2 额外机械验证②：本地 main 与 origin/main 同步（防 push 假成功）
    info("步骤6.2：验证本地 main 与 origin/main 同步")
    run(["git", "fetch", "origin", "main"], cwd=REPO_ROOT, check=False)
    sync_check = run(
        ["git", "rev-list", "--left-right", "--count", "main...origin/main"],
        cwd=REPO_ROOT, check=False
    )
    sync_parts = sync_check.stdout.strip().split()
    local_ahead = int(sync_parts[0]) if len(sync_parts) >= 1 else -1
    local_behind = int(sync_parts[1]) if len(sync_parts) >= 2 else -1
    if local_ahead > 0:
        fail(f"步骤6.2失败：本地 main 领先 origin/main {local_ahead} 个提交（推送未成功？），禁止删除")
    if local_behind > 0:
        warn(f"本地 main 落后 origin/main {local_behind} 个提交（远程有新提交），建议先 pull")

    info(f"步骤6/9：删除 worktree {wt_path.name}")
    # 先删 frontend/node_modules junction（Windows 文件锁会阻止 git worktree remove）
    frontend_nm = wt_path / "frontend" / "node_modules"
    if frontend_nm.exists():
        subprocess.run(["cmd", "/c", "rmdir", str(frontend_nm)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    # 先尝试非 force 删除（git 会对有未提交改动的 worktree 拒绝删除，这是保护）
    remove_result = subprocess.run(
        ["git", "worktree", "remove", str(wt_path)],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if remove_result.returncode != 0:
        # 步骤1已确认干净 + 步骤6.1/6.2 已确认合并推送，此处用 force 升级（仅在此安全前提下允许）
        warn(f"非 force 删除失败（{remove_result.stderr.strip()[:80]}），安全检查已过，升级为 --force")
        remove_result2 = subprocess.run(
            ["git", "worktree", "remove", str(wt_path), "--force"],
            cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if remove_result2.returncode != 0:
            # Windows 上 git worktree remove 对含 junction 的目录常失败，回退到 shutil
            info(f"git worktree remove 受限（{remove_result2.stderr.strip()[:60]}），回退到手动删除")
            try:
                import shutil
                shutil.rmtree(wt_path, ignore_errors=True)
            except Exception:
                pass

    # 步骤7：删功能分支（不用 -D 强制删；-d 会拒绝删未合并分支，删失败必须中断）
    info(f"步骤7/9：删除分支 {branch}（用 -d，git 自动拒绝删未合并分支）")
    del_result = subprocess.run(
        ["git", "branch", "-d", branch], cwd=REPO_ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if del_result.returncode != 0:
        fail(
            f"步骤7失败：git branch -d {branch} 被拒绝（git 判定分支可能未完全合并）：\n"
            f"  {del_result.stderr.strip()}\n"
            f"  若确认已合并，请手动检查 git log 后用 git branch -D 强删；否则会丢代码。"
        )
    ok(f"分支 {branch} 已删除")

    # 步骤8：prune
    info("步骤8/9：git worktree prune")
    run(["git", "worktree", "prune"], cwd=REPO_ROOT)

    # 步骤9：确认无残留
    info("步骤9/9：确认 worktree list 无残留")
    result = run(["git", "worktree", "list"], cwd=REPO_ROOT)
    print(result.stdout.rstrip())
    if str(wt_path) in result.stdout or wt_path.as_posix() in result.stdout:
        fail(f"步骤9失败：worktree list 仍残留 {wt_path}，未完成")

    print()
    ok(f"任务 {task} 收尾完成（合并+推送+清理全部成功）")


# ---------------------------------------------------------------------------
# status 子命令
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> None:
    """查看所有 worktree 状态。"""
    result = run(["git", "worktree", "list"], cwd=REPO_ROOT)
    print(f"{CYAN}=== Worktree 列表 ==={RESET}")
    print(result.stdout.rstrip())
    print()

    # 逐个检查 worktree 是否有未提交改动
    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        wt_path_str = parts[0]
        wt_path = Path(wt_path_str)
        if not wt_path.exists():
            continue
        if wt_path == REPO_ROOT:
            continue  # 跳过主工作区
        status = run(["git", "status", "--porcelain"], cwd=wt_path)
        if status.stdout.strip():
            changed = len(status.stdout.strip().splitlines())
            print(f"  {YELLOW}●{RESET} {wt_path.name}: {changed} 个未提交改动")
        else:
            print(f"  {GREEN}●{RESET} {wt_path.name}: 干净")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Git Worktree 管理工具（封装 AGENTS.md 隔离开发流程）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python scripts/git/worktree.py create add-login
  python scripts/git/worktree.py finish add-login
  python scripts/git/worktree.py status
"""
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="创建隔离 worktree")
    p_create.add_argument("task", help="任务名（用于分支名 feat/<task> 和 worktree 目录名）")
    p_create.add_argument("--base", default="main", help="基准分支（默认 main）")

    p_finish = sub.add_parser("finish", help="执行收尾流程（合并→推送→删worktree→prune）")
    p_finish.add_argument("task", help="任务名")
    p_finish.add_argument("--no-push", action="store_true", help="跳过推送（仅本地测试用）")

    sub.add_parser("status", help="查看所有 worktree 状态")

    args = parser.parse_args()

    # 启用 Windows ANSI 颜色
    if sys.platform == "win32":
        os.system("")

    if args.command == "create":
        cmd_create(args)
    elif args.command == "finish":
        cmd_finish(args)
    elif args.command == "status":
        cmd_status(args)


if __name__ == "__main__":
    main()
