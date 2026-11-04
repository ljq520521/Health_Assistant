# 睡眠监测模块（已实现）

入口：`/sleep`。本模块覆盖原始需求中的六项功能，取代旧文档中“睡眠待开发”的描述；其他业务模块仍为占位页。

## 功能与操作

| 功能 | 已实现内容 |
| --- | --- |
| 睡眠记录 | 增删改查入睡/醒来时间、可选深浅睡分钟数、夜醒次数、主观感受与备注；按醒来日期筛选 |
| 睡眠质量评估 | 时长、夜醒、规律性、感受四个维度；点击分数查看得分明细和偏离提示 |
| 趋势与异常识别 | 近 7 / 30 天，可指定截止日；每日累计时长、目标线、均值、前期比较、覆盖率和偏离提示 |
| 助眠内容管理 | 内置合成白噪音、低频雨声音景、冥想音景；播放/停止、音量、定时停止；收藏、编辑、删除、上传本地音频及添加直链 |
| 作息提醒与闹钟 | 睡前提醒、每周重复日期、闹钟试听、页面横幅和可选桌面通知、5 分钟稍后提醒、估算唤醒时间 |
| 睡眠报告 | 当前周期统计、阶段录入小结与明细；CSV 下载；浏览器打印或存为 PDF |

页面分为“记录与分析 / 助眠音频 / 作息与闹钟 / 睡眠报告”四个选项卡，包含加载、空数据、错误提示和重试。手机宽表格与 30 天图可以横向滚动。

首次使用在睡眠页输入称呼并建立本地档案。已有档案直接复用，不覆盖姓名或其他模块资料。数据保存在本地 SQLite，没有登录或多人隔离。

## 记录、评分与统计

- 输入和展示统一为 Asia/Shanghai；接口必须传带时区的 ISO 8601，后端规范化为 UTC。按醒来日期归档，支持跨夜。
- 单条时长为 1 分钟至 24 小时，醒来不能晚于当前时间，记录不能重叠，相邻时间允许。深睡与浅睡之和不能超过总时长；未知阶段留空，不自动推断。
- 夜醒次数为 0–50 的整数；感受为 1–5 或空；备注最长 2000 字。
- 单日多次记录相加时长，再对有记录的日期求均值。缺失日期为 null，不补 0。每日分数是该日记录的算术平均；本期分数是全部记录的算术平均。
- 周/月指截止日向前 7 / 30 天（含截止日），对比前一个等长周期。任一期无数据时不返回变化量，同时展示两期覆盖天数。

评分为本项目的**个人作息参考算法，不是医学量表**；按当前目标重新计算，修改目标也会影响历史评分。

| 维度 | 权重 | 计算规则 |
| --- | --- | --- |
| 目标时长 | 40 | `min(时长/目标, 1) × 40` |
| 连续性 | 25 | `max(0, 25 - 夜醒次数 × 5)` |
| 规律性 | 15 | 与计划入睡时间的最短时钟差（跨午夜）；`max(0, 1 - 分钟差/180) × 15` |
| 主观感受 | 20 | 用户 1–5 分乘以 4；未填则不参与 |

总分除以参与维度的权重之和，换算为 0–100 整数。感受未填时标明“评估不完整”，不虚构分数。

偏离提示规则：单条时长偏离目标至少 120 分钟、入睡偏离计划至少 120 分钟、夜醒至少 3 次、感受不高于 2 分。这些是记录提示，不代表临床异常；深浅睡仅展示输入，不推算 REM 或真实周期。

## 音频与提醒边界

- 内置音景由 Web Audio 本地合成；冥想音景为环境音而非语音指导。播放需用户点击，离开睡眠页或切换选项卡会停止。
- 上传 MP3/WAV/OGG/M4A，最多 20 MB，检查 MIME 与文件头；编码不受浏览器支持时显示播放失败。文件位于数据库同级 `sleep-audio/`，默认被 Git 忽略。删除条目同时删除上传文件。
- HTTP(S) 直链由浏览器直接播放，后端不下载；需直指可访问音频。HTTPS 页面需使用 HTTPS 音频以避免混合内容限制。
- 提醒规则保存后，点击**开启本次提醒与声音**。刷新后需重新启用；页面须打开且设备唤醒，关闭页面、系统休眠、浏览器暂停计时后不保证响铃或准时停止音频。
- 站内切换页面不中断提醒。通知被拒绝/不支持时保留页面横幅。响铃最长 60 秒，可停止或 5 分钟后重响。错过超过 90 秒的事件不补响。
- 智能闹钟只是**计划时间估算**：从计划入睡起按 90 分钟步长，选择最晚起床前 30 分钟内的候选；没有候选则准点响铃。不感知真实浅睡、不保证按生理周期唤醒。
- 重复日期分别属于计划入睡日和计划起床日；提前提醒跨到前一天时仍按计划日的星期判断。

实现参考：[Web Audio 交互要求](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices)、[浏览器自动播放限制](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay)、[通知安全上下文](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts/features_restricted_to_secure_contexts)。

## 数据库迁移

启动时先执行原始 `init.sql`，再按顺序执行 `sql/migrations/*.sql`；`schema_migrations(name)` 记录版本，每份迁移在事务中执行。重复启动不重复 ALTER 或播种音频，原有健康数据保留。

| 表 | `001_sleep.sql` 变更 |
| --- | --- |
| `sleep_records` | 新增 `deep_minutes INTEGER NULL`、`light_minutes INTEGER NULL`、`awakenings INTEGER DEFAULT 0`；新增索引 `(profile_id,wake_at)` |
| `sleep_settings` | `profile_id INTEGER PK/FK`、`target_minutes INTEGER`、`bedtime/alarm_time TEXT`、`reminder_minutes INTEGER`、`bedtime_enabled/alarm_enabled/smart_alarm INTEGER(0/1)`、`weekdays TEXT(JSON)`、`updated_at TEXT` |
| `sleep_content` | `id INTEGER PK`、`title TEXT`、`category TEXT(noise/meditation)`、`source_type TEXT(generated/url/upload)`、`source TEXT`、`favorite INTEGER(0/1)`、`created_at TEXT` |

每份档案一行设置：目标 180–720 分钟，提前提醒 0–120 分钟，星期 0=周一至 6=周日；默认提醒关闭。上传响应只暴露播放接口，不暴露磁盘文件名。

## 接口清单

统一前缀 `/api`。开发服务仅绑定本机，无鉴权；后端 `/docs` 可查看请求结构。

| 路径 | 方法 | 入参 / 出参 |
| --- | --- | --- |
| `/sleep/profile` | GET / POST | POST `{display_name}`；返回 `{profile: {id,display_name} 或 null}`；仅初始化，不覆盖 |
| `/sleep-records` | GET | 可选 `date_from/date_to`；返回 `{items: SleepRecord[]}` |
| `/sleep-records` | POST | `sleep_at,wake_at,deep_minutes?,light_minutes?,awakenings,quality?,notes`；返回 201 记录 |
| `/sleep-records/{id}` | GET / PUT / DELETE | PUT 同 POST；返回记录 / 更新记录 / 204 |
| `/sleep/settings` | GET / PUT | 设置表可写字段，weekdays 为数组；返回设置及 `effective_alarm_time/reminder_time` |
| `/sleep/analysis` | GET | `period=week或month`、可选 `end_date`；返回范围、设置、summary、daily、records、observations、notice |
| `/sleep/report` | GET | 同分析，`format=json或csv`；返回 JSON 报告或带 UTF-8 BOM 的 CSV 附件 |
| `/sleep/content` | GET / POST | POST `{title,category,url}`；返回列表 / 201 条目 |
| `/sleep/content/upload` | POST | Query `title,category`；原始音频 Body 与正确 Content-Type；返回 201 条目 |
| `/sleep/content/{id}` | PUT / DELETE | PUT `{title,category,favorite}`；返回条目 / 204 |
| `/sleep/content/{id}/audio` | GET | 返回上传的音频文件，支持浏览器范围请求 |

SleepRecord 额外返回 `duration_minutes,wake_date,score,dimensions,alerts,stage_unrecorded_minutes,assessment_complete`。空列表为 200，未建档写记录/设置及重叠为 409，非法输入 422，资源不存在 404，不支持的格式 415，文件过大 413。

CSV 备注做公式前缀转义；PDF 使用浏览器打印，无服务端 PDF 依赖。没有记录的周期不会输出评分结论。

## 验证与维护

后端：在 `backend/` 使用虚拟环境运行 `python -m unittest discover -s tests -v`。前端：在 `frontend/` 运行 `npm test` 和 `npm run build`。

检查覆盖旧库迁移、档案复用、记录 CRUD、重叠/时区/非法值、缺失数据、周期对比、设置、上传清理、CSV，以及跨午夜、星期归属、重复和错过的提醒。

主要文件：`backend/app/modules/sleep/`、`backend/sql/migrations/001_sleep.sql`、`frontend/src/views/SleepView.vue`、`frontend/src/components/sleep/`、`frontend/src/api/sleep.js`。后台推送、穿戴设备和真实睡眠分期需后续专门集成，当前不模拟这些能力。
