# mineru-book-mcp

独立 stdio MCP 服务：分块上传、SHA-256 校验、MinerU Agent/Standard 解析、本地回退，以及 book-to-skill 工作流和 Skill ZIP 打包。

启动：

    uvx --from git+https://github.com/TerryHank/mineru-book-mcp.git mineru-book-mcp

Standard API 使用服务环境变量 `MINERU_TOKEN`；仓库不包含任何凭据。
