# ASAR CLI (asar_cli.mjs) 开发与使用文档

`asar_cli.mjs` 是一个针对 `bundled_asar` 的 Node.js 命令行包装工具。它为 Python 主程序（`core/patcher.py` 等）提供了一个统一、稳定且跨平台的接口，用于直接操作 ASAR 归档文件（读取、解包、打包、哈希计算等）。

由于 Python 直接处理 ASAR 格式较为复杂且性能不佳，本工具通过调用打包好的 Node.js ASAR 库 (`bundled_asar/index.mjs`) 来完成底层操作，并通过 **标准输出 (stdout)** 返回严格的 **JSON 格式** 数据供 Python 解析。

`bundled_asar/` 目录包含 ASAR Node.js 核心库 (`index.mjs`)，这是程序自带的 ASAR 操作依赖库，脱离系统环境限制。

---

## 1. 核心设计原则

1. **JSON 响应**：所有命令（除明确说明外）的正常输出（`stdout`）均为合法的 JSON 字符串。Python 层可以通过 `json.loads(stdout)` 直接解析。
2. **错误处理**：发生错误时，程序将以非零状态码退出（`exit(1)`），并在 **标准错误输出 (stderr)** 中返回 JSON 格式的错误详情。
3. **临时文件安全**：对于需要提取文件进行哈希计算或读取的操作，工具会在系统临时目录或当前目录创建带时间戳的临时文件夹（如 `__temp_hash_1712345678901__`），操作完成后会利用重试机制（`maxRetries`）确保临时文件被安全清理，防止杀毒软件锁定导致的文件残留。
4. **路径规范化**：工具内部通过 `path.normalize()` 自动处理 Windows (`\`) 和 POSIX (`/`) 的路径分隔符差异，确保在各平台上均能正确访问 ASAR 内部树结构。

---

## 2. 命令参考与输出格式

### 2.1 获取文件信息 (`stat`)

获取 ASAR 归档中特定文件的大小和状态信息。

**命令**：
```bash
node asar_cli.mjs stat <asar_path> <file_path>
```

**成功输出 (stdout)**：
```json
{
    "success": true,
    "size": 10245,
    "offset": 0,
    "executable": false,
    "mtime": null,
    "atime": null
}
```

---

### 2.2 提取单文件文本内容 (`extract-file`)

将 ASAR 归档中的特定文件提取并以 `utf8` 文本格式输出到控制台。
*注意：此命令仅适用于文本文件（如 `.js`, `.json`, `.txt` 等）。对于二进制文件（如字体、图片），请使用 `hash-file` 或直接解包，否则会损坏二进制数据。*

**命令**：
```bash
node asar_cli.mjs extract-file <asar_path> <file_path>
```

**成功输出 (stdout)**：
文件的纯文本内容（非 JSON）。

---

### 2.3 计算单文件 SHA256 哈希 (`hash-file`)

直接计算 ASAR 归档内特定文件的 SHA256 哈希值，完美支持二进制文件（如 `.ttf`, `.png` 等），不会发生编码截断问题。
*注意：在最新的架构中，为了提升性能并减少进程开启的开销，Steam 更新检测机制（如 `core/patcher.py` 中的 `get_file_hash_in_asar`）已改用纯 Python 内存解析实现。此命令目前作为后备或调试工具保留。*

**命令**：
```bash
node asar_cli.mjs hash-file <asar_path> <file_path>
```

**成功输出 (stdout)**：
```json
{
    "success": true,
    "hash": "1f60cfe246886a1f16ebeac4d3bf2243a034df0ed9cbc8b75d37a7092a746381"
}
```

---

### 2.4 列出所有文件 (`list`)

获取 ASAR 归档内的所有文件路径列表。

**命令**：
```bash
node asar_cli.mjs list <asar_path>
```

**成功输出 (stdout)**：
```json
{
    "success": true,
    "files": [
        "package.json",
        "data/others/craftmincho.ttf",
        "tyrano/lang.js"
    ]
}
```

---

### 2.5 完整解包 (`extract`)

将整个 ASAR 归档解压到指定的目录。

**命令**：
```bash
node asar_cli.mjs extract <asar_path> <dest_dir>
```

**成功输出 (stdout)**：
```text
SUCCESS
```

---

### 2.6 打包为 ASAR (`pack`)

将指定目录打包为 ASAR 归档文件。支持排除特定文件不被打包进 ASAR（例如排除二进制 Node 模块或可执行文件）。

**命令**：
```bash
node asar_cli.mjs pack <src_dir> <dest_file> [--unpack <pattern>]
```

**成功输出 (stdout)**：
```text
SUCCESS
```

---

## 3. 错误输出格式 (stderr)

当任何命令执行失败时，`asar_cli.mjs` 会在 `stderr` 中输出统一格式的 JSON 错误信息。Python 调用方可以通过解析 `e.stderr` 获取错误原因。

**常见错误格式**：
```json
{
    "success": false,
    "error": "Error details here...",
    "error_type": "file_not_found"
}
```

**支持的 `error_type` 枚举**：
- `invalid_args`：缺少必需的命令行参数。
- `file_not_found`：目标文件在 ASAR 归档中不存在（常见且通常属于正常逻辑分支，例如游戏原版不包含某个第三方字体）。
- `file_corrupted`：ASAR 文件已损坏、无效或格式错误。
- `invalid_asar`：目标路径不是一个有效的 ASAR 文件。
- `permission_error`：文件或目录读写权限被拒绝。
- `unknown`：未知的内部错误。

## 4. 在 Python 中调用的最佳实践

Python 端调用示例（基于 `subprocess`）：

```python
import json
import subprocess

def call_asar_cli(core, command, *args):
    cmd = [core.node_path, core.script_path, command] + list(args)
    try:
        proc_result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=True, encoding='utf-8')
        # 对于 extract-file、extract、pack 命令，视情况解析 JSON
        return json.loads(proc_result.stdout.strip())
    except subprocess.CalledProcessError as e:
        try:
            error_data = json.loads(e.stderr.strip())
            # 根据 error_type 优雅地处理预期内的异常（如文件不存在）
            if error_data.get('error_type') == 'file_not_found':
                return None
            else:
                logger.warning(f"ASAR CLI Error: {error_data.get('error')}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse stderr: {e.stderr}")
        return None
```
