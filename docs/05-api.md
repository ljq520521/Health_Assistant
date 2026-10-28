# 接口清单

## v0.1 已实现

默认后端地址 `http://127.0.0.1:8000`，以 JSON 返回数据，无鉴权。Swagger `/docs` 仅列出当前实际实现的接口。

| 路径 | 方法 | 入参 | 出参 / 状态 |
| --- | --- | --- | --- |
| `/health` | GET | 无 | 200：`{"status":"ok","database":"ok","version":"0.1.0"}`；数据库异常为 503：`{"detail":"数据库不可用"}` |
| `/api/modules` | GET | 无 | 200：数组，每项为 `{code,name,owner,route,status}`，`status` 固定为 `planned`；共 5 项 |

模块 code：`profile/diet/exercise/sleep/cycle`。`route` 是对应前端路径。v0.1 的其余业务接口均未实现，请求会返回 404；空路由文件只预留模块位置。

## v0.2 约定（全部待开发）

### 公共约定

- 入参为 JSON；列表过滤用 Query；`id` 用 Path。字段使用 snake_case。
- 不接收 `profile_id`、`id`、创建/更新时间作为可写入参，服务端固定归属档案 1 并生成 ID 与时间。响应直接返回对象，不额外包 `data`。
- 列表返回 `{items: [...]}`，空列表 `{items: []}`；首轮不分页，以完整筛选结果供前端汇总。
- 新建记录返回 201；读取/修改返回 200；删除返回 204（无响应体）。PUT 为完整替换：必填字段必须提供，省略可选字段按默认值处理。
- 资源不存在返回 404；业务模块在未建档时返回 409；非法日期、数值和枚举返回 422。业务错误返回 `{detail: "说明"}`；Pydantic 校验错误的 `detail` 为数组。
- 所有输出资源包含数据库字段（含 `id`、`created_at`、`updated_at`，非档案资源还含 `profile_id`）；计算字段见下表。
- 列表按业务日期/时间倒序，再按 `id` 倒序；目标按 `created_at`、`id` 倒序。日期范围筛选包含首尾；起始大于结束返回 422。
- 日期格式 `YYYY-MM-DD`；睡眠时间接受带时区的 ISO 8601，例如 `2026-09-23T23:00:00+08:00`，拒绝不带时区的时间，存储与输出统一为 UTC `Z` 格式。

### 1. 用户与基础（成员 A）

| 路径 | 方法 | 入参 | 出参 |
| --- | --- | --- | --- |
| `/api/profile` | GET | 无 | `Profile`；未建档为 404 |
| `/api/profile` | PUT | `ProfileInput` | 创建或替换唯一档案，均返回 200 `Profile` |
| `/api/profile/goals` | GET | 无 | `{items: Goal[]}` |
| `/api/profile/goals` | POST | `GoalInput` | `Goal` |
| `/api/profile/goals/{id}` | GET | `id` | `Goal` |
| `/api/profile/goals/{id}` | PUT | `id`、`GoalInput` | `Goal` |
| `/api/profile/goals/{id}` | DELETE | `id` | 204，无响应体 |

### 2. 饮食营养（成员 B）

| 路径 | 方法 | 入参 | 出参 |
| --- | --- | --- | --- |
| `/api/diet-records` | GET | 可选 `date_from`、`date_to`，按 `record_date` 筛选 | `{items: DietRecord[]}` |
| `/api/diet-records` | POST | `DietInput` | `DietRecord` |
| `/api/diet-records/{id}` | GET | `id` | `DietRecord` |
| `/api/diet-records/{id}` | PUT | `id`、`DietInput` | `DietRecord` |
| `/api/diet-records/{id}` | DELETE | `id` | 204，无响应体 |

### 3. 运动健身（成员 C）

| 路径 | 方法 | 入参 | 出参 |
| --- | --- | --- | --- |
| `/api/exercise-records` | GET | 可选 `date_from`、`date_to`，按 `record_date` 筛选 | `{items: ExerciseRecord[]}` |
| `/api/exercise-records` | POST | `ExerciseInput` | `ExerciseRecord` |
| `/api/exercise-records/{id}` | GET | `id` | `ExerciseRecord` |
| `/api/exercise-records/{id}` | PUT | `id`、`ExerciseInput` | `ExerciseRecord` |
| `/api/exercise-records/{id}` | DELETE | `id` | 204，无响应体 |
| `/api/exercise-records/recommendation` | GET | 无 | `ExerciseRecommendation`；根据档案与最近 7 天记录生成的只读推荐 |

`ExerciseRecommendation` 不是业务记录，不写库：服务端读取档案的身高体重、既往病史、运动偏好、健康目标与最近 7 天运动记录，返回 `focus`、`weekly_target_minutes`、`weekly_done_minutes`、`weekly_progress_percent`、`suggestions[]`、`safety_notes[]`、`evidence[]` 等字段。未建档返回 409；规则与字段说明见 `backend/app/modules/exercise/README.md`。

### 4. 睡眠监测（成员 D）

| 路径 | 方法 | 入参 | 出参 |
| --- | --- | --- | --- |
| `/api/sleep-records` | GET | 可选 `date_from`、`date_to`，按 `Asia/Shanghai` 醒来日期筛选 | `{items: SleepRecord[]}` |
| `/api/sleep-records` | POST | `SleepInput` | `SleepRecord` |
| `/api/sleep-records/{id}` | GET | `id` | `SleepRecord` |
| `/api/sleep-records/{id}` | PUT | `id`、`SleepInput` | `SleepRecord` |
| `/api/sleep-records/{id}` | DELETE | `id` | 204，无响应体 |

### 5. 生理期管理（成员 E）

| 路径 | 方法 | 入参 | 出参 |
| --- | --- | --- | --- |
| `/api/cycle-records` | GET | 可选 `date_from`、`date_to`，按 `start_date` 筛选 | `{items: CycleRecord[]}` |
| `/api/cycle-records` | POST | `CycleInput` | `CycleRecord` |
| `/api/cycle-records/{id}` | GET | `id` | `CycleRecord` |
| `/api/cycle-records/{id}` | PUT | `id`、`CycleInput` | `CycleRecord` |
| `/api/cycle-records/{id}` | DELETE | `id` | 204，无响应体 |

### 输入与输出字段

`?` 表示可省略/可空，其他为必填。带默认值的文本可省略但不能为 null。更具体的长度和取值范围见 [数据库设计](04-database.md)。

| 输入对象 | 必填字段 | 可选字段 / 默认值 | 输出对象的额外计算字段 |
| --- | --- | --- | --- |
| `ProfileInput` | `display_name:string` | `height_cm:number?`、`weight_kg:number?` 默认 null；`medical_history`、`allergies`、`medications`、`preferences` 均为 string，默认 `""` | `Profile` 无额外计算字段 |
| `GoalInput` | `title:string`、`target_value:number`、`unit:string` | `current_value:number=0`（不可为 null）；`due_date:date?=null` | `Goal.progress_percent:number`，0–100，保留 1 位小数 |
| `DietInput` | `record_date:date`、`meal_type:string`、`food_name:string`、`amount_g:number` | `calories_kcal:number?=null`；`notes:string=""` | `DietRecord` 无额外计算字段 |
| `ExerciseInput` | `record_date:date`、`exercise_type:string`、`duration_minutes:integer`、`intensity:string` | `notes:string=""` | `ExerciseRecord` 无额外计算字段 |
| `SleepInput` | `sleep_at:datetime`、`wake_at:datetime` | `quality:integer?=null`；`notes:string=""` | `SleepRecord.duration_minutes:number`，时间差分钟数，保留 1 位小数 |
| `CycleInput` | `start_date:date` | `end_date:date?=null`、`flow_level:string?=null`；`symptoms`、`mood`、`notes` 均为 string，默认 `""` | `CycleRecord.period_days:integer或null`，结束减开始再加 1；进行中为 null |

枚举：餐次 `breakfast/lunch/dinner/snack`；运动强度 `low/medium/high`；经期流量 `light/medium/heavy`。目标仅做手动累计进度；饮食合计与运动每日汇总在前端根据列表计算，不额外增加统计接口。

### 联调示例（仅示例，v0.2 实现后可调用）

```http
POST /api/diet-records
Content-Type: application/json

{"record_date":"2026-09-23","meal_type":"lunch","food_name":"示例食物","amount_g":100,"calories_kcal":null,"notes":""}
```

```json
{
  "id": 1,
  "profile_id": 1,
  "record_date": "2026-09-23",
  "meal_type": "lunch",
  "food_name": "示例食物",
  "amount_g": 100,
  "calories_kcal": null,
  "notes": "",
  "created_at": "2026-09-23T04:00:00Z",
  "updated_at": "2026-09-23T04:00:00Z"
}
```
