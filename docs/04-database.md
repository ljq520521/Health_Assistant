# 数据库核心表设计

数据库：SQLite；初始化脚本：[`backend/sql/init.sql`](../backend/sql/init.sql)。v0.1 已建 **6 张业务表**，初始均为空。单个本地档案使用 `profiles.id=1`，其余五张表通过 `profile_id` 关联。

## 公共字段与规则

下面各表均包含这两个公共字段，不在每张表中重复列出：

| 字段名 | 类型 | 主键 / 索引 | 备注 |
| --- | --- | --- | --- |
| `created_at` | TEXT NOT NULL | — | 建表默认写入 UTC 时间 `YYYY-MM-DDTHH:mm:ssZ`；创建后不修改 |
| `updated_at` | TEXT NOT NULL | — | 创建时同上；未来更新接口必须主动刷新此字段，SQL 没有自动更新时间触发器 |

- `id` 为整数主键；除固定档案外，使用 AUTOINCREMENT。
- `profile_id` 为非空外键，默认 1；引用 `profiles(id)`，启用外键约束和 `ON DELETE CASCADE`。首轮不开放删除档案接口。
- 日期用 `YYYY-MM-DD`，睡眠时间与审计时间使用 UTC 文本；日期的业务含义按 `Asia/Shanghai` 解释。
- 标为可空的字段允许 NULL；其余必填。文本空值统一使用 `''`，不要把未知热量写成 0。
- 后续 API 用 Pydantic 校验合法日历日期和时区；SQL 的 CHECK 是补充约束，并非完整的日期校验器。

## 1. profiles（用户与基础，成员 A）

| 字段名 | 类型 | 主键 / 索引 | 备注 |
| --- | --- | --- | --- |
| `id` | INTEGER | 主键 | CHECK 限制为 1，仅有一份档案 |
| `display_name` | TEXT NOT NULL | — | 昵称，去除首尾空白后长度 1–50 |
| `height_cm` | REAL，可空 | — | 身高 cm，已填写时 > 0 |
| `weight_kg` | REAL，可空 | — | 体重 kg，已填写时 > 0 |
| `medical_history` | TEXT NOT NULL | — | 既往病史，默认空串 |
| `allergies` | TEXT NOT NULL | — | 过敏史，默认空串 |
| `medications` | TEXT NOT NULL | — | 用药备注，默认空串 |
| `preferences` | TEXT NOT NULL | — | 饮食禁忌、运动偏好、作息偏好，暂用自由文本，默认空串 |

本表为本地健康档案，不是账号表，不含用户名、密码或权限字段。

## 2. health_goals（用户与基础，成员 A）

| 字段名 | 类型 | 主键 / 索引 | 备注 |
| --- | --- | --- | --- |
| `id` | INTEGER | 主键，自增 | 目标 ID |
| `profile_id` | INTEGER NOT NULL | 外键；`idx_goals_profile` | 默认 1 |
| `title` | TEXT NOT NULL | — | 累计型目标名称，长度 1–100，如“本周步行 120 分钟” |
| `target_value` | REAL NOT NULL | — | 目标值 > 0 |
| `current_value` | REAL NOT NULL | — | 当前累计值 ≥ 0，默认 0，手动更新 |
| `unit` | TEXT NOT NULL | — | 长度 1–20，如“分钟”“次” |
| `due_date` | TEXT，可空 | — | 截止日期；暂不自动延期、提醒或标记逾期 |

进度由 API 返回 `min(current_value / target_value, 1) × 100`，不另存进度字段。首轮不支持体重下降等反向目标，也不自动关联其他模块的记录。

## 3. diet_records（饮食营养，成员 B）

| 字段名 | 类型 | 主键 / 索引 | 备注 |
| --- | --- | --- | --- |
| `id` | INTEGER | 主键，自增 | 饮食记录 ID |
| `profile_id` | INTEGER NOT NULL | 外键；联合索引首列 | 默认 1 |
| `record_date` | TEXT NOT NULL | 联合索引第二列 | 饮食日期 |
| `meal_type` | TEXT NOT NULL | — | `breakfast/lunch/dinner/snack` |
| `food_name` | TEXT NOT NULL | — | 食物名称，长度 1–100 |
| `amount_g` | REAL NOT NULL | — | 克重 > 0 |
| `calories_kcal` | REAL，可空 | — | 本条食物总热量 kcal，≥ 0；未知为 NULL，不是每 100g 的值 |
| `notes` | TEXT NOT NULL | — | 备注，默认空串 |

索引：`idx_diet_profile_date(profile_id, record_date)`。前端合计非空热量，并另显示未填写热量的记录数。

## 4. exercise_records（运动健身，成员 C）

| 字段名 | 类型 | 主键 / 索引 | 备注 |
| --- | --- | --- | --- |
| `id` | INTEGER | 主键，自增 | 运动记录 ID |
| `profile_id` | INTEGER NOT NULL | 外键；联合索引首列 | 默认 1 |
| `record_date` | TEXT NOT NULL | 联合索引第二列 | 运动日期 |
| `exercise_type` | TEXT NOT NULL | — | 自由文本，长度 1–50，如“快走” |
| `duration_minutes` | INTEGER NOT NULL | — | 正整数，分钟 |
| `intensity` | TEXT NOT NULL | — | `low/medium/high`，用户主观选择 |
| `notes` | TEXT NOT NULL | — | 备注，默认空串 |

索引：`idx_exercise_profile_date(profile_id, record_date)`。不估算消耗热量，不采集心率。

## 5. sleep_records（睡眠监测，成员 D）

| 字段名 | 类型 | 主键 / 索引 | 备注 |
| --- | --- | --- | --- |
| `id` | INTEGER | 主键，自增 | 睡眠记录 ID |
| `profile_id` | INTEGER NOT NULL | 外键；联合索引首列 | 默认 1 |
| `sleep_at` | TEXT NOT NULL | 联合索引第二列 | 入睡时间，规范化为 UTC |
| `wake_at` | TEXT NOT NULL | — | 醒来时间，必须晚于入睡时间 |
| `quality` | INTEGER，可空 | — | 主观评分 1–5；不是医疗评估结果 |
| `notes` | TEXT NOT NULL | — | 备注，默认空串 |

索引：`idx_sleep_profile_time(profile_id, sleep_at)`。API 根据两个时间计算 `duration_minutes`（保留 1 位小数），不重复存储。列表日期筛选按上海时区的醒来日期，后续若数据量增大再添加 `wake_at` 索引。

## 6. cycle_records（生理期管理，成员 E）

| 字段名 | 类型 | 主键 / 索引 | 备注 |
| --- | --- | --- | --- |
| `id` | INTEGER | 主键，自增 | 经期记录 ID |
| `profile_id` | INTEGER NOT NULL | 外键；联合索引首列 | 默认 1 |
| `start_date` | TEXT NOT NULL | 联合索引第二列 | 开始日期 |
| `end_date` | TEXT，可空 | — | 结束日期 ≥ 开始日期；NULL 表示尚未结束 |
| `flow_level` | TEXT，可空 | — | 本次整体流量，`light/medium/heavy` |
| `symptoms` | TEXT NOT NULL | — | 本次症状备注，默认空串 |
| `mood` | TEXT NOT NULL | — | 本次情绪备注，默认空串 |
| `notes` | TEXT NOT NULL | — | 其他备注，默认空串 |

索引：`idx_cycle_profile_date(profile_id, start_date)`。已结束记录返回持续天数 `end_date - start_date + 1`；进行中返回 NULL。首轮不做逐日症状曲线或周期预测。

## 初始化与后续演进

在 `backend/` 执行 `python scripts/init_db.py`，内部读取 `sql/init.sql`，在事务中创建表与索引；重复执行不清空数据。数据库文件被 Git 忽略，仓库只提交 SQL。

SQL 与本文件是一一对应的。后续修改字段时同步更新数据库文档、接口文档并新增迁移脚本；不要将本地数据库提交到仓库。
