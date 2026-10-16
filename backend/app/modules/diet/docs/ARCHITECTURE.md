# 前后端组件与依赖关系

## 请求链

`/diet → DietView.vue → 功能组件 → frontend/src/api/饮食封装 → FastAPI diet/router.py → 子路由 → schemas + service → app.database.connect → SQLite`

前端6个API封装都属于饮食模块。数据库路径来自`request.app.state.settings.database_path`，业务服务不选择正式/测试数据库。公共`database.connect()`逐次启用外键、提交/回滚并关闭连接。`settings.py`集中维护Asia/Shanghai，时间戳由UTC生成；前端从GET /api/diet/config读取业务时区。

## 前端组件

| 功能 | 文件 | 依赖与责任 |
| --- | --- | --- |
| 页面入口 | views/DietView.vue | 六页签、配置、演示横幅；不修改公共导航 |
| 饮食记录 | DietRecordsPanel.vue | api/diet.js、api/nutrition.js及食物库接口；手动/食物库模式、预览、CRUD |
| 食物库 | FoodLibraryPanel.vue | api/foodLibrary.js；分类/食物表单、搜索、归档 |
| 营养分析 | NutritionAnalysisPanel.vue | api/nutrition.js；范围及日周月分组 |
| 目标弹窗 | DailyGoalsDialog.vue | 按生效日期读写目标；明确提交字段 |
| 营养图 | NutritionTrendChart.vue | 原生SVG，未知/无记录断点，消费后端daily |
| 饮水 | WaterPanel.vue | api/water.js；饮水CRUD、目标及提醒设置 |
| 提醒宿主 | WaterReminderHost.vue | waterReminder.js、waterTime.js；在/diet层生命周期内检查 |
| 提醒纯逻辑 | waterReminder.js、waterTime.js | localStorage槽位去重、Web Locks、通知权限、时区转换 |
| 食谱工作区 | RecipeWorkspace.vue | 库/库存/成分偏好/推荐子页 |
| 食谱库 | RecipeLibraryPanel.vue、RecipeNutrition.vue | api/recipes.js；成分和步骤、营养快照、归档 |
| 库存 | RecipeInventoryPanel.vue | 食材克重及修订；不会自动扣库存 |
| 偏好 | RecipePreferencePanel.vue | 术语、别名、组成、喜好/过敏/禁用 |
| 推荐结果 | RecipeRecommendationPanel.vue | 条件→推荐preview；展示分数、实际权重、缺料及风险 |
| 食谱公共工具 | recipeUI.js | 本模块格式化/表单辅助 |
| 报告 | DietReportPanel.vue | api/reports.js，后端只读汇总 |
| 报告图/展示 | ReportChart.vue、reportPresentation.js | SVG图、状态说明、数据字段到图表映射 |
| 导出 | reportExport.js、reportPdf.js | Canvas绘制高分辨率图像、原生PDF字节；不调用收费API |
| 逻辑测试 | waterReminder.test.js、report.test.js | Node内置测试，不依赖浏览器授权 |

以上除入口外组件位于`frontend/src/components/diet/`。准确逐文件import列表见DEPENDENCIES.json，六个API封装为diet.js、foodLibrary.js、nutrition.js、water.js、recipes.js、reports.js。

## 后端分层

| 领域 | 文件组 |
| --- | --- |
| 路由组合与饮食记录 | router.py、schemas.py、service.py |
| 食物/分类/统一业务错误 | library_router.py、library_schemas.py、library_service.py |
| 营养目标与统计 | nutrition_router.py、nutrition_schemas.py、nutrition_service.py、nutrition_math.py |
| 饮水与提醒设置 | water_router.py、water_schemas.py、water_service.py |
| 食谱与营养快照 | recipe_router.py、recipe_schemas.py、recipe_service.py |
| 术语/库存/成分/偏好 | recipe_preference_router.py、recipe_preference_schemas.py、recipe_preference_service.py |
| 本地推荐 | recipe_recommendation_router.py、recipe_recommendation.py |
| 报告 | report_router.py、report_service.py，复用nutrition_service.summarize_rows及water_service.summarize_amounts |
| 迁移 | migrations.py、migration_002.py、migration_003.py、migration_004.py |
| 开发测试库 | dev_database.py（新临时库）、demo_environment.py及demo_server.py（严格演示上下文） |
| 来源准备与导入 | source_mapping.py、prepare_sources.py、build_import_preview.py、verify_import_preview.py、import_schemas.py、import_service.py、import_data.py及data/import_preparation/ |

数据库没有持久化报告表，推荐preview与报告都是实时计算。推荐优先硬过滤，匹配营养/库存/偏好的原始权重0.5/0.3/0.2，仅对有效维度重新归一化。未知营养不补0；数据缺失罚分独立展示，不当作营养不足。

## 数据关联

- profiles → diet_records、food_categories、food_items、diet_daily_goals、water_records、water_reminder_settings及004各领域根表。
- food_items → diet_records.food_id与四项快照；food_items归档不改历史饮食记录。
- diet_recipe_categories → diet_recipes → diet_recipe_ingredients、diet_recipe_steps；食材关联food_items且保存四项营养、名称、来源、更新时间快照。
- diet_inventory_items关联food_items，数量为g；推荐计算需求与库存差，不写入消费。
- diet_ingredient_terms → aliases；food_composition + composition_terms保存contains/may_contain；food_preferences的food_id与term_id恰好一个非空。
- diet_daily_goals按effective_from版本读取，营养与water_ml共享同一版本表；未提交目标字段不清空。

全部列、NULL/default、CHECK、唯一约束、外键动作与索引详见DATABASE-CATALOG.md。food_items及部分004食物引用是单列外键，不能把当前模型直接当成多租户隔离模型。

## 共享依赖与集成点

- backend/app/main.py：保留五模块路由挂载、原有基础表初始化、CORS及`application.state.settings`注入；不导入或调用`initialize_diet_schema`。普通FastAPI启动不执行饮食001～004，即使`DIET_APPLY_MIGRATIONS=1`也不触发迁移。不能覆盖其他成员路由。
- backend/app/database.py与config.py、backend/sql/init.sql：只依赖、不在本轮修改。connect的事务约定是迁移和服务正确性的前提。
- backend/requirements.txt：现有tzdata用于Windows IANA时区；不新增PDF或图表依赖。
- frontend/router/index.js中的已有/diet路由，以及styles.css公共button/panel基础样式：只复用，不替换公共导航或布局。
- .env环境变量：HEALTH_DB_PATH、API_PROXY_TARGET、VITE_API_BASE_URL、ALLOWED_ORIGINS；数据库切换通过进程配置而不是替换文件。

本轮没有改变上述共享文件。今后接入鉴权或更换事务机制应由团队共同确认并增加跨模块回归。

## 显式迁移与测试隔离

部署准备与服务启动分开：在获授权的目标库上先完成基础初始化，再依次显式执行001食物库、002营养目标、003饮水、004食谱迁移；之后才启动应用。各迁移使用独立事务及登记校验，不修改已发布SQL，也不靠重启补做迁移。普通启动只保留团队已有的基础表初始化，不代表饮食扩展结构已就绪。

`migrations.initialize_diet_schema`是仍保留的旧辅助函数，直接调用且环境变量为1时可能执行001；当前团队启动路径不调用它。显式迁移及相关业务请求负责检查迁移状态，不能再宣称所有饮食校验和异常都会在应用启动阶段被统一发现。

新环境使用Python 3.12和固定依赖。安全的临时库初始化、逐条`--database ... --apply`迁移、启动及测试步骤见[饮食README](../README.md#初始化与001004迁移)。`dev_database`是显式创建全新临时库并调用001～004的准备工具，不是FastAPI启动钩子；不传`--demo`，不操作演示库或默认正式数据库。

自动测试使用TemporaryDirectory及独立SQLite夹具。在启动测试进程前，将HEALTH_DB_PATH明确指向临时库，并向create_app传入对应测试Settings；其他成员服务可能直接调用get_settings()，仅注入应用state不足以隔离这些调用。验证缺迁移503前必须有合法测试档案，否则会先返回409 PROFILE_REQUIRED。

迁移策略测试覆盖环境变量为0和1时启动不改结构、001未完成时食物库503、显式001后正常访问，以及重启不自动执行002～004。原有失败回滚、幂等性、校验和冲突和历史数据保护测试保留。正式库升级另需授权、备份及恢复验证、停写和副本演练；测试或文档示例不构成正式库迁移授权。
