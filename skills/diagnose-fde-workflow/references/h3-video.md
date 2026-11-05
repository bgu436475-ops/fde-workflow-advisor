# H3 视频接入（可选）

仅在用户提供自己的 H3 API、宿主允许联网执行且用户要求生成视频时使用。此模块不改变无工具诊断模式，不附带任何作者密钥或共享额度。

## 从方案到短片

1. 先核对同一笔业务的前后动作、角色和异常责任，从制作稿提取一段短提示词。4 秒只能做概念样片，不能代替完整 SOP 教学。
2. 由宿主的秘密配置设置 `H3_BASE_URL` 与 `H3_API_KEY`。API base 以实际提供的版本路径为准，必须 HTTPS，不附带密钥、查询参数或 URL 用户名。不要把真实配置提交到 Git、客户报告、公开 ZIP、日志或前端。
3. 先 `models` 检查授权。已验证的最小文生视频参数为 `h3-text`、4 秒、`1280x720`。其他模型名称即使出现在列表中，也不代表首帧、参考图或续写的参数已经验证。
4. 只提交一次，把回执存到本次任务目录；排队、网络超时和错误均不自动重新付费生成。请求超时但没有回执时，先向服务方核对是否已受理。
5. 用回执中的真实编号查询。完成后再下载 MP4，并核对时长、能否解码播放、角色与动作、异常路径和字幕；通过后交付。失败或排队只说明实际状态，模型返回进度为空时不编造进度。

以下命令中的路径与任务编号需替换为实际值，密钥使用宿主秘密配置注入，不作为命令参数输入：

```bash
python3 <skill-dir>/scripts/video_h3.py models
python3 <skill-dir>/scripts/video_h3.py create --prompt-file <work-dir>/video-prompt.txt --seconds 4 --size 1280x720 --output <work-dir>/video-receipt.json
python3 <skill-dir>/scripts/video_h3.py status <receipt-id>
python3 <skill-dir>/scripts/video_h3.py download <receipt-id> --output <work-dir>/video.mp4
```

脚本仅使用 Python 标准库。宿主无法注入环境变量时，可通过 `--config-stdin` 从隐藏的标准输入传入含 `base_url`、`api_key` 的 JSON；不回显配置，不把 JSON 字面量放进 shell 命令或公开文件。不能安全传递配置时只交付分镜。

## 接口与核实范围

2026-11-05 在用户授权的 H3 实例实际验证：`GET /models`、`POST /videos` 文生视频成功排队、`GET /videos/{id}` 返回队列状态。生成服务可能长时间排队，估计等待仅供参考。

适配器的下载流程使用 `GET /videos/{id}/content`；必须在任务完成后对实际实例验证，不能仅凭代码存在就宣称成片或下载测试成功。API 版本变更时重新核对。跨域下载跳转移除授权头，避免把 API 密钥发送给存储域名。

| 步骤 | 请求 | 处理 |
| --- | --- | --- |
| 探测 | `GET /models` | 检查模型授权 |
| 提交 | `POST /videos` | JSON 含 model、prompt、seconds 字符串、size |
| 查询 | `GET /videos/{id}` | queued / in_progress / completed / failed 等，以实例返回为准 |
| 下载 | `GET /videos/{id}/content` | 仅 completed 后读取二进制；保存新文件，不覆盖已有成片 |

## 画面与网页边界

只呈现方案中真实改变：减少重复查找、统一记录、异常转给负责人、人工审核。不得把未核实库存画成已经发货，也不得用人物消失、现金或百分比暗示未经测量的收益。复杂文字、数字与旁白建议后期确定性制作；不同工具生成的静态预览与视频需注明分别制作。

API 密钥只存后端秘密环境。公开页面可播放选定样片和读取删减后的状态，不返回原始上游回执或报错。不得向匿名访客开放作者付费生成额度；新建任务需服务端鉴权、限额和防重复机制。当前脚本不提供面向公众的生成后台，也不将用户密钥共享给其他安装者。
