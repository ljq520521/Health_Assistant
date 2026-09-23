# 五人分工与协作

尚未提供组员姓名，先用成员 A–E 占位；每人负责一个完整业务模块，而不是仅负责一篇文档。

| 负责人 | 模块 | v0.2 核心工作 | 独立维护的文件 / 数据表 |
| --- | --- | --- | --- |
| A | 用户与基础 | 档案与偏好维护、累计型目标 CRUD、手动进度 | `frontend/src/views/ProfileView.vue`；`backend/app/modules/profile/`；`profiles`、`health_goals` |
| B | 饮食营养 | 饮食 CRUD、日期筛选、已知热量合计 | `frontend/src/views/DietView.vue`；`backend/app/modules/diet/`；`diet_records` |
| C | 运动健身 | 运动 CRUD、日期筛选、时长合计 | `frontend/src/views/ExerciseView.vue`；`backend/app/modules/exercise/`；`exercise_records` |
| D | 睡眠监测 | 睡眠 CRUD、跨夜时间计算、主观评分 | `frontend/src/views/SleepView.vue`；`backend/app/modules/sleep/`；`sleep_records` |
| E | 生理期管理 | 经期 CRUD、流量/症状/情绪备注 | `frontend/src/views/CycleView.vue`；`backend/app/modules/cycle/`；`cycle_records` |

每位组员在所属目录新增 `schemas.py`、`service.py` 等即可，按复杂度增加文件，不必提前拆出空层。前端复杂表单可放 `frontend/src/components/<模块名>/`，API 调用放 `frontend/src/api/<模块名>.js`。

## 开发顺序

1. 全员先依照 README 启动 v0.1，确认健康检查正常、前端可访问。
2. 全员对照同一套页面、表结构、接口文档开发。成员 A 优先实现档案 GET/PUT，供其他模块真实联调。
3. B–E 可先独立编写界面和校验；自动检查使用临时数据库和测试档案，不将测试数据写入仓库。
4. 每个模块完成后自测“新增 → 查询 → 修改 → 删除”，再联调空状态、输入非法和请求失败场景。
5. 成员 A 组织最终集成；每人仍负责自己模块缺陷的修复。

## 公共文件约定

成员 A 兼任公共文件维护人：`App.vue`、`router/index.js`、`styles.css`、`data/modules.js`、`app/main.py`、`config.py`、`database.py`、`modules/catalog.py`、`sql/init.sql` 以及依赖与配置文件。

其他成员确有需要可在自己的 PR 中修改公共文件，由 A 统一复核。涉及字段或接口变更时，同时更新 `docs/04-database.md` 和 `docs/05-api.md`，不要单方面改变已约定的名称。

## Git 协作

建议分支：`codex/profile`、`codex/diet`、`codex/exercise`、`codex/sleep`、`codex/cycle`。各人从最新 main 建分支，用 PR 合并；初始骨架准备好不代表这些分支已经创建。

提交前检查：不带 `.env`、数据库、虚拟环境、`node_modules`；提交依赖锁文件；后端冒烟检查和前端构建通过。功能 PR 附上模块验证结果。

## 验收边界

| 版本 | 验收内容 |
| --- | --- |
| v0.1（本次） | 文档齐全；前后端可启动；健康检查实际访问数据库；五个模块有独立入口；SQL 可重复建表；依赖可复现 |
| v0.2（下一步） | 五个模块核心业务可增删改查（档案为读取/保存）；页面按约定筛选、计算、报错；记录持久化；前后端联调通过 |
| 后续扩展 | 从原始需求中另行选择功能，先确认范围和接口，再开发 |
