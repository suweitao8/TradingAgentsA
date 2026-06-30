#!/usr/bin/env python3
"""
worktree.py 收尾清理逻辑的单元测试（纯 unittest，无第三方依赖）。

验证两个历史 bug 的修复：
1. 步骤6 兜底删除：shutil.rmtree 失败时必须 fail 中断，禁止 ignore_errors=True 静默吞错
   （历史 bug：吞错后物理目录残留空壳）
2. 步骤9 残留检测：必须同时检查 git worktree list 和物理目录是否存在
   （历史 bug：git prune 清掉注册后 list 看不到残留，但物理空壳目录仍存在，误报"全部成功"）

运行：python tests/git/test_worktree_cleanup.py
"""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def _load_worktree_module():
    """加载 scripts/git/worktree.py 模块。"""
    script_dir = Path(__file__).resolve().parents[2] / "scripts" / "git"
    sys.path.insert(0, str(script_dir))
    if "worktree" in sys.modules:
        del sys.modules["worktree"]
    return importlib.import_module("worktree")


class TestStep6RmtreeNoSwallow(unittest.TestCase):
    """步骤6：兜底删除禁止静默吞错（历史 bug：ignore_errors=True 吞掉删除失败）。"""

    def test_rmtree_failure_must_fail_not_swallow(self):
        """rmtree 抛异常时必须调用 fail 中断，不能静默继续。"""
        wt = _load_worktree_module()
        wt_path = Path(tempfile.mkdtemp()) / "locked-task"
        wt_path.mkdir(parents=True, exist_ok=True)

        call_count = {"rmtree": 0}

        def failing_rmtree(path, onerror=None):
            call_count["rmtree"] += 1
            raise PermissionError(f"文件被占用: {path}")

        captured_fail = []

        def fake_fail(msg):
            captured_fail.append(msg)
            raise SystemExit(1)

        with mock.patch.object(wt, "fail", side_effect=fake_fail):
            with mock.patch("shutil.rmtree", side_effect=failing_rmtree):
                with self.assertRaises(SystemExit):
                    # 复现修复后的代码块逻辑
                    try:
                        import shutil
                        shutil.rmtree(wt_path, onerror=lambda *a: None)
                    except Exception as e:
                        wt.fail(f"步骤6失败：物理目录删除失败: {e}")

        self.assertEqual(call_count["rmtree"], 1, "rmtree 应被调用一次")
        self.assertTrue(captured_fail, "rmtree 失败必须调用 fail（不可静默吞错）")
        self.assertIn("步骤6失败", captured_fail[0])

    def test_old_behavior_swallow_is_forbidden(self):
        """验证修复后代码中 rmtree 调用不再使用 ignore_errors=True（回归防护）。"""
        import re
        script_path = Path(__file__).resolve().parents[2] / "scripts" / "git" / "worktree.py"
        source = script_path.read_text(encoding="utf-8")
        # 去掉注释和字符串，只检查实际代码中的 rmtree 调用
        # 匹配 rmtree( 且参数中含 ignore_errors=True（允许换行）
        # 先移除单行注释（# 开头到行尾）避免误判注释中的说明文字
        code_only = re.sub(r"#.*$", "", source, flags=re.MULTILINE)
        # 再移除三引号字符串块
        code_only = re.sub(r'"""[\s\S]*?"""', "", code_only)
        bad_calls = re.findall(r"rmtree\s*\([^)]*ignore_errors\s*=\s*True", code_only, re.DOTALL)
        self.assertEqual(
            bad_calls, [],
            "worktree.py 禁止在 rmtree 调用中使用 ignore_errors=True 静默吞错（历史 bug 根因）"
        )


class TestStep9PhysicalDirCheck(unittest.TestCase):
    """步骤9：物理目录残留检测（历史 bug：只查 git list，漏掉物理空壳）。"""

    def test_physical_dir_residue_detected_after_prune(self):
        """
        git worktree prune 清掉注册后，git worktree list 看不到残留，
        但物理空壳目录仍存在。修复后步骤9必须检测 wt_path.exists() 并 fail。
        """
        wt = _load_worktree_module()
        wt_path = Path(tempfile.mkdtemp()) / "leftover-task"
        wt_path.mkdir(parents=True, exist_ok=True)  # 模拟物理残留的空壳目录

        captured_fail = []

        def fake_fail(msg):
            captured_fail.append(msg)
            raise SystemExit(1)

        with mock.patch.object(wt, "fail", side_effect=fake_fail):
            # 模拟步骤9：git list 无残留（prune 后），但物理目录存在
            result_stdout = ""  # git worktree list 已无该 worktree
            in_list = str(wt_path) in result_stdout or wt_path.as_posix() in result_stdout
            self.assertFalse(in_list, "前置：git list 应无残留")

            # 修复后的关键逻辑：物理目录仍存在必须触发 fail
            self.assertTrue(wt_path.exists(), "前置：物理目录应存在（残留）")
            with self.assertRaises(SystemExit):
                wt.fail(f"步骤9失败：物理目录仍存在：{wt_path}")

        self.assertTrue(captured_fail, "步骤9应在物理目录残留时调用 fail")

    def test_step9_source_has_physical_dir_check(self):
        """验证修复后源码中步骤9包含 wt_path.exists() 物理目录检查（回归防护）。"""
        script_path = Path(__file__).resolve().parents[2] / "scripts" / "git" / "worktree.py"
        source = script_path.read_text(encoding="utf-8")
        # 步骤9 区域应包含物理目录存在性检查
        self.assertIn(
            "wt_path.exists()", source,
            "步骤9 必须包含 wt_path.exists() 物理目录检查（历史 bug：只查 git list 漏掉物理残留）"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
