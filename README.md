# 流程改造顾问 · FDE Workflow Advisor

一个业务流程诊断 Skill：把一句宏大的“我们想用 AI 改造公司”，拆成有依据的改造机会、可执行的小试点和能讲清楚的前后场景。

支持 SOP、口述和业务材料。先看删除、合并、统一规则等简单办法，再判断哪里值得用 AI；也允许结论是暂缓建设。

## 从演示开始

- [模拟需求与完整问答](examples/factory-quotation/simulation.md)
- [一页完整演示](examples/factory-quotation/report.html)（下载后打开，包含对话、方案、指标、场景与分镜）
- [诊断结果、方案比较与试点](examples/factory-quotation/diagnosis.md)
- [前后场景图](examples/factory-quotation/scene.svg)
- [下载 HTML 场景报告](examples/factory-quotation/scene.html)（下载后浏览器打开）
- [60 秒视频分镜](examples/factory-quotation/storyboard.md)
- [同源结构化模型](examples/factory-quotation/workflow.json)

演示里的客户、订单、单量和工时全部虚构。人工工时下降不代表报价周期、现金支出或营收同比改善。视频目前输出分镜，尚未生成成片。

## 安装后直接使用

本技能使用开放的 `SKILL.md` 目录格式，没有作者账号、API Key、ChatGPT Library、MCP 或其他插件依赖。分析能力由你使用的 AI 提供，技能本身不包含大模型。

### 命令行 AI 工具

已安装 Node.js/npm 的用户，在需要使用技能的项目目录运行：

```bash
npx skills add bgu436475-ops/fde-workflow-advisor --skill diagnose-fde-workflow
```

按提示选择你的工具。也可明确指定目标，例如：

```bash
npx skills add bgu436475-ops/fde-workflow-advisor --skill diagnose-fde-workflow -a claude-code --copy
npx skills add bgu436475-ops/fde-workflow-advisor --skill diagnose-fde-workflow -a codex --copy
npx skills add bgu436475-ops/fde-workflow-advisor --skill diagnose-fde-workflow -a cursor --copy
```

`skills` 是第三方安装工具，负责将文件放到其支持的宿主目录；本技能运行时不依赖该工具。以上默认只安装到当前项目；希望跨项目使用时按安装工具的提示选择用户级范围。

### 支持导入技能包的 AI

从 [dist/diagnose-fde-workflow.zip](dist/diagnose-fde-workflow.zip) 下载原始文件，在宿主的自定义技能导入处上传并启用。请上传这个技能 ZIP，而不是整个 GitHub 仓库的 ZIP。包内只有一个 `diagnose-fde-workflow/` 文件夹，入口是 `SKILL.md`。具体导入入口和权限取决于宿主。

### 其他环境

把 `skills/diagnose-fde-workflow/` 整个文件夹复制到宿主实际支持的技能目录。不支持原生安装的聊天工具，可粘贴 [单文件提示词](dist/workflow-advisor-prompt.md)，作为会话指令使用；这不等于永久安装。

安装并启用后，直接说：

> 用流程改造顾问分析：我们每天从客户消息中整理需求，再交技术报价，经常缺资料来回问。帮我判断值得改造的部分，给出最小试点和前后场景。

不需要记住美元符号或斜杠命令。若宿主没有自动加载新技能，按其提示刷新技能列表或重新开启会话。

## 能力范围

| 宿主能力 | 可以交付 |
| --- | --- |
| 能理解自定义指令 | 需求分析、三问以内的关键追问、方案比较、反证、试点与前后步骤表；Mermaid 以源码交付 |
| 另能读写文件 | Markdown 方案、JSON 模型；无脚本时注明尚未校验 |
| 另能运行 Python 3.9+ | 确定性校验和测算、离线 HTML/SVG 场景报告、视频分镜 |
| 另有视频制作能力 | 在用户要求和宿主允许时继续制作；本包不内置视频生成服务 |

工具能力不足时自动选择可用输出，分析不因缺少脚本或插件而停止。不同 AI 的推理质量和权限不同；不承诺所有产品都支持原生安装或产出完全一致。

本技能不会联网安装依赖，也不会请求作者的账号；实际业务连接是可选增强，需由使用者单独授权。

## 安装后验收

把这句话发给已启用技能的 AI：

> 我每月只有3个人各花10分钟汇总供应商表，想做一个AI系统。请判断是否值得，给前后流程。没有工时改善数据，不要替我编。

应能得到有依据的方案比较和前后场景；不应为了“做AI”直接承诺收益、要求作者账号或让你先安装额外插件。

Python 增强模式可以在已安装的技能目录运行一次离线演示（输出目录须为空，Python 命令按本机实际名称调整）：

```bash
python3 scripts/quickstart.py --output ./demo-output
```

示例完全离线；生成的数字为演示假设，不表示真实业务收益。首次演示使用包内询价样例，与上面的完整模拟案例参数不同。

## 本地重现演示

Python 3，脚本仅使用标准库。以下命令在仓库根目录运行：

```bash
python3 skills/diagnose-fde-workflow/scripts/workflow.py validate examples/factory-quotation/workflow.json
python3 skills/diagnose-fde-workflow/scripts/workflow.py calculate examples/factory-quotation/workflow.json
python3 skills/diagnose-fde-workflow/scripts/workflow.py render examples/factory-quotation/workflow.json --output examples/factory-quotation/scene.html
python3 skills/diagnose-fde-workflow/scripts/workflow.py storyboard examples/factory-quotation/workflow.json --output examples/factory-quotation/storyboard.md
```

`validate` 只验证结构、引用和数值范围，不证明业务事实。缺少数据时不自动填收益；方案诊断不会自动连接、写入或上线企业系统。

## 重建分发文件

```bash
python3 scripts/build_distribution.py
```

安装包与单文件提示词均由同一份技能源码生成，避免两个版本内容分叉。验证范围见 [兼容性与验收](docs/compatibility.md)。

安装工具和格式依据：[Skills CLI 官方仓库](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)、[Agent Skills 规范](https://agentskills.io/specification)、[Claude 自定义技能文档](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)。
