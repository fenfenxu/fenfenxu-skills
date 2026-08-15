# find-thread 验证用例（要有说服力）

在本 skill 根目录执行：

```bash
python3 scripts/verify-find-thread.py
python3 scripts/verify-find-thread.py -v
```

脚本按 `references/host-*.md` 在本机抽样真实会话，再对每个宿主跑 **2×2 矩阵**：

|  | 应命中（+） | 不应命中（−） |
|--|------------|--------------|
| **按会话 ID** | 真实 UUID / 短 UUID → 必须命中，且路径一致 | 伪造 UUID `deadbeef-…` → 必须 0 命中 |
| **按名称** | 从该会话首条用户消息抽出的特征子串 → 必须命中该会话 | 无意义词 `zzznomatchqx9plumcake-…` → 必须 0 命中 |

名称查询**不写死外机 ID**，而是从本机 fixture 的 prompt 现抽（例如「水火箭」「找到 thread」），换机器也能跑。

覆盖宿主（本机有数据才测）：`cursor` `codex` `claude` `workbuddy` `kimi`。

## 用例清单（每个有数据的宿主各一套）

| 标记 | 含义 | 期望 |
|------|------|------|
| `ID+` full UUID | 用真实会话 ID 查 | 命中，且 `path` 与抽样文件完全一致 |
| `ID+` short UUID | 用 ID 前 8 位查 | 仍命中同一会话 |
| `ID−` fake UUID | 用绝不存在的 UUID 查 | **零**命中 |
| `name+` | 用从 prompt 抽出的名称/关键词查 | 结果中含该会话 |
| `name−` | 用无意义字符串查 | **零**命中 |

只有「全能命中」不够；没有负例，验证没有说服力。
