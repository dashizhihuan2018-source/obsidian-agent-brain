# 官方来源与兼容边界

文档核对日期：2026-10-15。下面是入口依据，不是对每个客户端版本的运行保证；变更时以当前官方说明及实际环境为准。正文为原创操作方案，未复制官方手册全文。

| 来源 | 本方案采用的依据 |
| --- | --- |
| [Obsidian：创建仓库](https://obsidian.md/help/vault) | 可创建新库，也可把已有文件夹打开为库 |
| [Obsidian：数据存储](https://obsidian.md/help/data-storage) | 核心笔记是本地 Markdown 文件，配置目录与正文分开 |
| [Codex：Skills](https://developers.openai.com/codex/skills) | 技能目录、SKILL.md 与当前公开的发现位置 |
| [Codex：AGENTS.md](https://developers.openai.com/codex/guides/agents-md) | 全局/项目范围与 override 优先级，规则需由入口实际加载 |
| [WorkBuddy：技能](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market) | 桌面端本地技能包导入、开启与关闭 |
| [WorkBuddy：项目](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project) | 代码开发项目配置和 AGENTS.md 兼容；不外推到所有模式 |
| [WorkBuddy：记忆](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Memory) | 产品内置记忆另有提取和管理机制，不是 vault 同步接口 |

基础版不依赖模型 API、特定模型名称、远程服务、MCP、付费同步或社区插件。没有声称通过 WorkBuddy GUI、Codex 新会话、多设备或 Windows/macOS 全平台运行验收；使用者必须按验收清单在自己的环境验证。
