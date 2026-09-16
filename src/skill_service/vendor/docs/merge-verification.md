# 融合交付与验证

日期：2026-09-15。

## 输入

- book-to-skill-master.zip，SHA-256：
  EE7A5258794FFCAA2210776E048D03E2525D3167CDF9C8603B1E45C9A351C0DA
- MinerU-Ecosystem-main.zip，SHA-256：
  C373772ABCD63219C05F53A8E93DDB7F1C4669CE7859E3EB4EAE68DB6AFA4607

以 book-to-skill 的项目目录为主体，保留 Python 包、本地解析器、
scripts、tools、tests、docs、许可证和生成阶段。MinerU 通过官方 CLI
作为可选提取后端，新增 book_to_skill/mineru.py。
原始档案包含其他生态组件，未将与本工作流无关的 MCP、LangChain、
LlamaIndex 服务复制进融合包。

## 验证结果

- 完整 Python 回归：626 passed, 13 skipped（16.45 秒）。
- ruff check .：通过。
- tools/validate_skill.py SKILL.md：通过；753 行触发长度软提示。
- Codex quick_validate.py：通过。
- Airy Markdown 本地提取：complete，1 个来源，0 个失败；原路径保留。
- MinerU CLI 预检：v0.5.9，可从 Windows npm 安装调用。
- 新增后端测试：授权前不上传、Flash 页数限制、旧 Office 精度模式、
  带中文/特殊字符路径、网页来源脱敏、错误输出不泄漏、空结果拒绝、
  同名多来源隔离、部分失败返回非零。
- 安装路径搬移测试：Codex/Agents/Claude/Copilot/Hermes 目录均从自身
  Python 包运行，测试覆盖原入口及新的 local 后端。

远程调用使用模拟 CLI 结果完成回归；本次没有向 MinerU 上传实际文档，
没有完成在线 OCR/高精度账号端到端验收。13 个跳过用例涉及可选依赖或
平台条件。保留上游长 SKILL.md 是为了遵循本次文件架构要求。

## 分工与产物

Python 提取器输出 full_text.txt、metadata.json 和保留的 MinerU 中间文件。
Agent 按 SKILL.md 执行内容分析、生成、合并和扫描；Python 不替代知识生成。
最终知识 Skill 架构仍是 SKILL.md、chapters、glossary.md、
patterns.md、cheatsheet.md。
