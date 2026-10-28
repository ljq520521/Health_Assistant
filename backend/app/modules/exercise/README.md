# 运动健身模块（成员 C）

F004「录入运动数据，统计展示记录与趋势」的实现。只维护 `exercise_records` 一张表，所有记录归属唯一的本地档案 `profile_id = 1`。

## 范围

已实现（P0）：

- 运动记录的新增、查看、编辑、删除；
- 按 `record_date` 的日期范围筛选，起止日期均包含；
- 前端按日期汇总当日总时长，并展示近 14 天时长趋势与强度分布。

明确不做：

- 不估算热量消耗、不采集心率（见 `docs/04-database.md`）；
- 复杂训练计划属于 P1，不在本模块；
- 不新增统计接口，每日汇总与趋势由前端根据列表计算（见 `docs/05-api.md`）。

## 接口

前缀 `/api`，完整路径为 `/api/exercise-records`。

| 路径 | 方法 | 入参 | 出参 |
| --- | --- | --- | --- |
| `/api/exercise-records` | GET | 可选 Query `date_from`、`date_to` | 200 `{items: ExerciseRecord[]}` |
| `/api/exercise-records` | POST | `ExerciseInput` | 201 `ExerciseRecord` |
| `/api/exercise-records/{id}` | GET | Path `id` | 200 `ExerciseRecord` |
| `/api/exercise-records/{id}` | PUT | Path `id` + `ExerciseInput`（完整替换） | 200 `ExerciseRecord` |
| `/api/exercise-records/{id}` | DELETE | Path `id` | 204，无响应体 |

`ExerciseRecord` 字段：`id`、`profile_id`、`record_date`、`exercise_type`、`duration_minutes`、`intensity`、`notes`、`created_at`、`updated_at`。列表按 `record_date`、`id` 倒序。

## 校验与错误

| 情况 | 结果 |
| --- | --- |
| `record_date` 不是合法日历日期 | 422 |
| `exercise_type` 去空白后不足 1 或超过 50 字 | 422 |
| `duration_minutes` 不是 1–1440 的整数 | 422 |
| `intensity` 不是 `low/medium/high` | 422 |
| `notes` 超过 500 字 | 422 |
| 传入了 `id`、`profile_id`、`created_at` 等只读字段 | 422 |
| `date_from` 晚于 `date_to` | 422 `{"detail": "起始日期不能晚于结束日期"}` |
| 尚未建立个人档案 | 409 `{"detail": "请先建立个人档案"}` |
| 记录不存在 | 404 `{"detail": "运动记录不存在"}` |

`updated_at` 由服务端在每次 PUT 时刷新；`created_at` 与 `profile_id` 由服务端生成。

## 文件

后端：

- `schemas.py`：入参 / 出参模型与字段约束；
- `service.py`：SQL 读写、档案检查、时间戳；
- `router.py`：路由与状态码；
- `../../../tests/test_exercise.py`：接口测试。

前端：

- `frontend/src/api/exercise.js`：接口封装与错误信息转换；
- `frontend/src/components/exercise/exerciseStats.js`：汇总、分组、趋势、日期工具（纯函数）；
- `frontend/src/components/exercise/exerciseStats.test.js`：纯函数测试；
- `frontend/src/components/exercise/ExerciseFormDialog.vue`：新增 / 编辑弹窗；
- `frontend/src/components/exercise/ExerciseTrendChart.vue`：14 天时长趋势图；
- `frontend/src/views/ExerciseView.vue`：页面入口 `/exercise`。

## 测试

```powershell
cd backend
..\.venv\Scripts\python.exe -m unittest tests.test_exercise -v
```

```powershell
cd frontend
node --test src/components/exercise/exerciseStats.test.js
```
