"""
批量把 frontend 各组件里的 ElMessage.error(...) 替换为左下角 showError(...)。

规则：
1. 对象形态 ElMessage.error({ message: '...', duration: N })  →  showError('...', { duration: N })
2. 字符串形态 ElMessage.error('...')  /  ElMessage.error(`...`)  →  showError('...') / showError(`...`)
3. 每个文件：
   - 若替换后该文件不再有任何 ElMessage.*（success/warning/info）调用，则把 import 行从 'element-plus' 移除；
   - 否则保留 import。
   - 新增 `import { showError } from '@/utils/message'`（若该文件尚无此 import）。

注意：仅处理 .error( 调用，不动 .success/.warning/.info。
仅扫 frontend/src 下 .vue 和 .ts。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path("frontend/src")
SHOW_ERROR_IMPORT = "import { showError } from '@/utils/message'"


def convert_object_form(code: str) -> tuple[str, int]:
    """处理 ElMessage.error({ message: '...', duration: N }) 形态。
    只匹配单行、message + 可选 duration 两个已知字段的对象（本项目就这种）。
    """
    pattern = re.compile(
        r"ElMessage\.error\(\{\s*"
        r"message:\s*('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|`(?:[^`\\]|\\.)*`)\s*,\s*"
        r"duration:\s*(\d+)\s*"
        r"\}\)"
    )
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        count += 1
        msg = m.group(1)
        dur = m.group(2)
        return f"showError({msg}, {{ duration: {dur} }})"

    new_code = pattern.sub(repl, code)
    return new_code, count


def convert_string_form(code: str) -> tuple[str, int]:
    """处理 ElMessage.error(<expr>) 形态。<expr> 为字符串/模板字符串/变量/三元等。
    用正则匹配 ElMessage.error( 直到匹配的右括号（处理一层嵌套括号）。
    """
    out = []
    i = 0
    n = len(code)
    count = 0
    needle = "ElMessage.error("
    while i < n:
        idx = code.find(needle, i)
        if idx == -1:
            out.append(code[i:])
            break
        # 写入 needle 之前的内容
        out.append(code[i:idx])
        # 解析括号
        j = idx + len(needle)
        depth = 1
        while j < n and depth > 0:
            ch = code[j]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            j += 1
        inner = code[idx + len(needle) : j - 1]
        # 若 inner 以 { 开头（对象形态），交给对象处理；此处跳过已被对象处理过的（已变 showError）
        # 这里 inner 是字符串形态（对象形态已被上一步转成 showError）
        out.append(f"showError({inner})")
        count += 1
        i = j
    return "".join(out), count


def fix_imports(code: str, file_changed: bool) -> tuple[str, bool]:
    """调整 import：
    - 若文件已无任何 ElMessage. 调用，移除从 element-plus 的 ElMessage import（注意可能同行还有别的符号）。
    - 增加 showError import（若不存在）。
    返回 (新代码, 是否改动)。
    """
    changed = False

    # 是否还存在其它 ElMessage. 调用（success/warning/info/任何）
    has_other_elmessage = bool(re.search(r"\bElMessage\.", code))

    # 1) 处理 element-plus import 行
    # 形态 A: import { ElMessage } from 'element-plus'
    # 形态 B: import { ElMessage, ElMessageBox } from 'element-plus'
    elmessage_import_re = re.compile(
        r"^(\s*import\s*\{)([^}]*)(\}\s*from\s*['\"]element-plus['\"]\s*)$",
        re.MULTILINE,
    )

    def import_repl(m: re.Match) -> str:
        nonlocal changed
        head = m.group(1)
        symbols = m.group(2)
        tail = m.group(3)
        names = [s.strip() for s in symbols.split(",") if s.strip()]
        if has_other_elmessage:
            # 保留 ElMessage
            if "ElMessage" not in names:
                names.append("ElMessage")
            new_syms = ", ".join(names)
            return f"{head} {new_syms} {tail}"
        else:
            # 移除 ElMessage
            names = [s for s in names if s != "ElMessage"]
            if not names:
                # 整行删掉
                changed = True
                return ""
            new_syms = ", ".join(names)
            changed = True
            return f"{head} {new_syms} {tail}"

    code = elmessage_import_re.sub(import_repl, code)
    # 清理因整行删除留下的多余空行（仅当删除发生在 import 区，保守地：把连续 2+ 空行压成 1 个空行）
    code = re.sub(r"\n\n\n+", "\n\n", code)

    # 2) 增加 showError import（若文件被改且尚无）
    if file_changed and SHOW_ERROR_IMPORT not in code:
        # 在最后一个顶层 import 行之后插入；找不到就放最前
        lines = code.splitlines(keepends=True)
        last_import = -1
        for k, line in enumerate(lines):
            if line.lstrip().startswith("import "):
                last_import = k
        insert_line = f"{SHOW_ERROR_IMPORT}\n"
        if last_import >= 0:
            lines.insert(last_import + 1, insert_line)
        else:
            lines.insert(0, insert_line)
        code = "".join(lines)
        changed = True

    return code, changed


def process_file(path: Path) -> int:
    raw = path.read_text(encoding="utf-8")
    original = raw

    # 先对象形态
    raw, c1 = convert_object_form(raw)
    # 再字符串形态
    raw, c2 = convert_string_form(raw)
    total = c1 + c2
    if total == 0:
        return 0

    # 调整 import
    raw, _ = fix_imports(raw, file_changed=True)

    if raw != original:
        path.write_text(raw, encoding="utf-8")
    return total


def main() -> int:
    if not SRC.exists():
        print(f"源目录不存在: {SRC}", file=sys.stderr)
        return 1
    total_files = 0
    total_calls = 0
    for p in sorted(SRC.rglob("*")):
        if p.suffix not in (".vue", ".ts"):
            continue
        if "node_modules" in p.parts:
            continue
        n = process_file(p)
        if n > 0:
            total_files += 1
            total_calls += n
            print(f"  {p}: {n} 处")
    print(f"\n合计：{total_files} 个文件，{total_calls} 处替换")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
