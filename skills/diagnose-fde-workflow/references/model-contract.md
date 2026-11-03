# 模型约定

使用 UTF-8 JSON。未知用 null 或空列表并写入 unknowns，不用零表示未知耗时。参考 assets/quotation-example.json。

## 主字段

| 字段 | 类型 |
| --- | --- |
| title / goal / scope / case | 非空字符串；case 标明真实或演示及前后同一业务 |
| decision | pilot / defer / needs_input |
| evidence | [{id, status, note}]，status 为 user_reported / verified / inference / unknown / hypothetical |
| before / after | 节点列表；暂缓和待补充允许空 after；现状未知可空 before |
| opportunities | [{id, step_ids, type, reason, prerequisites, owner, acceptance, evidence_refs}]；字符串字段或字符串列表依样例 |
| self_checks | [{failure, verify, response}] |
| rollout | {scope, samples, baseline, owner, reviewer, maintainer, gates, stop, fallback}，值为字符串，未知写待确认 |
| unknowns | 字符串列表 |
| questions | [{text, changes_decision}]，当前轮最多 3 个 |
| metrics | null 或下述人工工时模型 |

evidence.note 保留来源定位及简短含义。verified 需实际核验，脚本不能证明事实。所有机会和节点 evidence_refs 仅引用存在的 evidence.id。

## 节点与边

节点包含全局唯一 id、actor、action、input、output 字符串；mode 为 rules / ai / human / mixed / unknown；basis 使用上述证据状态；evidence_refs 为列表；next 为 [{to, condition, exception}]。

to 需在同一张图内，condition 非空，exception 为布尔值。列表第一项为起点，所有节点需可达；每个节点需能到一个 next=[] 的终点。可补问回路，但必须有退出或人工结案路径。列表顺序只控制布局，边决定执行。单图最多 18 节点；过大先切子流程。

## 工时参数

metrics=null 时不算收益。可计算时字段为：
- status：证据状态，unknown 不可计算。
- source_note：参数来源与采样条件；unit 固定 labor_minutes_per_case。
- comparable_scope：布尔值，只有 true 才能前后比较。
- routes：[{name, weight, before_min, after_min, before_extra_min, after_extra_min}]，互斥完整且权重总和为 1。
- excluded_costs：未计入成本的字符串列表。
- cases_per_day / working_days_per_month：非负有限数或 null；未知时不输出对应容量。

before/after 是所有角色合计的每单人工分钟，extra 为尚未包括的额外人工，不重复计入。不得混入等待或端到端周期。所有值有限且非负；基线为零不算百分比；结果可以变差。推断或演示必须显著标注，未测量不标为实测。

## 命令与输出

validate 成功退出 0，失败退出 2 并列明错误。calculate 输出 JSON；缺参数时 available=false，不填零。render 输出自包含 HTML 及同名 SVG，从同一模型生成前后图、条件边、依据、指标和未知；不是已部署系统或视频。storyboard 输出同一 case 的 60 秒分镜草案，保留步骤编号，注明成片尚未生成。

业务摘要展示目标、已知问题、机会依据、推荐试点、效果前提和图。工程交接补字段来源、接入、规则、审核、异常队列、重试去重、日志与验收。真实客户模型和生成文件写到任务目录并按 Library 规则保存，不写入技能资源。
