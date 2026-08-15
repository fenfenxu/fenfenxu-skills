# find-thread 验证用例

在本 skill 根目录执行：

```bash
python3 scripts/verify-find-thread.py
python3 scripts/verify-find-thread.py -v
```

脚本会先按 `references/host-*.md` 的路径在本机抽样真实会话，再调用 `scripts/find-thread` 回查。

## 用例

| ID | 名称 | 操作 | 期望 |
|----|------|------|------|
| A | `{host} / full UUID` | `find-thread <uuid> -a <host> --all --json` | 命中，且 `path` / `session_id` 对上抽样文件 |
| B | `{host} / short UUID` | `find-thread <uuid前8位> -a <host> --all` | 仍能命中同一会话 |
| C | `workbuddy / keyword 水火箭` | `find-thread 水火箭 -a workbuddy --all` | 结果中含 `0d2e4064-…`（若本机有该文件；否则 SKIP） |
| D | `{host} / path equality` | 同 A | 返回的 `path` 与抽样文件**完全一致** |

覆盖宿主（本机有数据才测）：`cursor` `codex` `claude` `workbuddy` `kimi`。

## 手工等价命令（可选）

把下面的 `<uuid>` / 路径换成 `verify-find-thread.py` 打印的 Fixtures：

```bash
# 例：Cursor
python3 scripts/find-thread 93244b88-9875-461f-b7e8-fcca1a518644 -a cursor --all --json

# 例：Codex
python3 scripts/find-thread 01a002e3-01c6-7cc0-9775-392837f85901 -a codex --all --json

# 例：Claude
python3 scripts/find-thread c6516df6-28a4-489c-adc1-715d0e71120a -a claude --all --json

# 例：Workbuddy ID + 关键词
python3 scripts/find-thread 0d2e4064-c980-4fe7-8cee-89cc58d44e97 -a workbuddy --all --json
python3 scripts/find-thread 水火箭 -a workbuddy --all --json

# 例：kimi
python3 scripts/find-thread 9d7ab858-1d06-4135-b985-2b69d6668553 -a kimi --all --json
```

> 上面 UUID 是某次本机抽样值，会过期/因机器而异；以验证脚本打印的 Fixtures 为准。
