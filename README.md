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

## 使用

本仓库的可安装 Skill 在 `skills/diagnose-fde-workflow/`，其中 `SKILL.md` 是入口，`references/` 是判断规则，`scripts/workflow.py` 生成可核对的图和指标。

将整个技能文件夹放入支持 `SKILL.md` 的工具所使用的技能目录，再调用：

> 使用 $diagnose-fde-workflow 分析下面这套业务，判断值得优化的环节，比较方案，给出最小试点和前后场景图：……

个人 ChatGPT 安装状态由技能管理流程维护；本 GitHub 仓库保存源码与示例。

## 本地重现演示

Python 3，脚本仅使用标准库。以下命令在仓库根目录运行：

```bash
python3 skills/diagnose-fde-workflow/scripts/workflow.py validate examples/factory-quotation/workflow.json
python3 skills/diagnose-fde-workflow/scripts/workflow.py calculate examples/factory-quotation/workflow.json
python3 skills/diagnose-fde-workflow/scripts/workflow.py render examples/factory-quotation/workflow.json --output examples/factory-quotation/scene.html
python3 skills/diagnose-fde-workflow/scripts/workflow.py storyboard examples/factory-quotation/workflow.json --output examples/factory-quotation/storyboard.md
```

`validate` 只验证结构、引用和数值范围，不证明业务事实。缺少数据时不自动填收益；方案诊断不会自动连接、写入或上线企业系统。
