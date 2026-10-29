# 公共目录扩展验收记录（修复前历史记录）

运动模块现已在 main dcb9c4b 补齐；最新结果见 [全站复核记录](PUBLIC-CATALOG-FULL-ACCEPTANCE.md)。下文阻塞项和数量保留为当时记录。

日期：2026-10-28（北京时间）。分支：`feat/public-food-catalog`。基线：`efe2310286de5d9c5699cc8aaba0f3a675067238`。

## 已完成范围

从未改写的 v3 包生成独立只读公共库；匿名分类/搜索/详情；稳定公共键；006 独立迁移登记；按需私人食品引用；公共只读保护；库存、禁忌、营养快照、私人食谱复制与公共推荐；前端公共/私人入口、食品选择器及来源说明。算法仍使用原先禁忌硬过滤、评分及营养计算。

公共库 `backend/app/modules/diet/catalog_data/food_catalog.db`：651264 字节；134 食物、12 菜谱、48 食材依赖、9 食物分类、4 食谱分类。

文件 SHA256：`4ce321d96ee69fb277b1f7b1fd1fd70b078f5d4f00980d5e3c97811be328782c`。
逻辑内容 SHA256：`de5866e95e9476229adffbe2c9c49325a2c753f1110782700388339fb77aa107`。

食品/菜谱逐项与 v3 原始 payload 相同。公共审批元数据仅移除开发机器绝对路径、保留文件名及原审批文件和工作簿哈希；原署名、时间、批准范围、134/12/48 审批条目均保留。公共库不包含档案、账号、Token、健康记录或演示用户。

## 后端结果

独立测试 **231 项通过，0 失败**：原饮食回归 165、原 v2/v3 种子服务 25、原演示服务 7、本次公共目录专项 34。

实际执行证据：重建最终公共库后的主运行为 224 通过、7 阻塞；随后补跑 7 项独立演示服务测试全部通过。已把这 7 项纳入统一执行器，统一清单为 239 项：231 可执行、8 真实全站测试阻塞。

在 backend 目录执行：

```powershell
& ..\.venv\Scripts\python.exe -B tests/run_diet_isolated.py
```

执行器只注册真实 profile 与 diet 路由，使用真实账号注册、登录、健康数据授权及权限验证。所有数据库位于新的 TemporaryDirectory；在应用启动前设置绝对 HEALTH_DB_PATH，并与 Settings 保持一致。没有伪造认证、模拟 `/health` 或把独立启动当作五模块启动。原断言保留，只有明确依赖全站的案例列入阻塞清单。

公共专项覆盖：

- 两次构建文件字节/逻辑哈希一致；来源身份、营养数值、审批与 48 依赖逐项一致；只允许公开表和无开发者用户路径。
- 没有私人数据库或档案时公开浏览；搜索、分类、详情；公共 PUT/DELETE 拒绝；缺失、损坏、错误版本和异常 manifest 的明确 503。
- 真实匿名 401、无档案 409、无健康数据授权 403、查看者只读及敏感资料遮蔽；过期 Token 不阻塞公开浏览。
- 引用按需、幂等、并发唯一；私人和公共 ID 区分；API 及 SQLite 触发器禁止改写公共缓存。
- 私人历史营养快照保留，公共食品正确记账；库存及喜好映射；旧来源链接和真实导入标记中的禁忌继续生效；异常来源 JSON 不使推荐崩溃。
- 课程批准不解除未知过敏原的保守硬过滤。
- 12 道菜谱全部另存为私人食谱，48 条配料克重、份数、步骤、计算营养一致；编辑私人副本不改公共库，也不自动创建饮食记录。
- 006 前置条件、独立登记、幂等、并发、失败回滚、校验和冲突及未登记结构拒绝；临时生理期、运动、睡眠与档案数据不变。
- 饮水、目标、营养及日/周/月报告回归。

## 全站阻塞清单

当前 `backend/app/modules/exercise/service.py` 导入未提交的 `.recommendation`，导致真实 `app.main` 无法导入。未修改运动模块、未添加占位文件、未删除导入、未改 main.py。

独立执行器中明确阻塞的 8 项：

1. `test_diet_migrations.MigrationTests.test_startup_never_migrates_and_explicit_migration_enables_library`
2. `test_nutrition.GoalsMigrationTests.test_concurrent_and_startup_does_not_apply_002`
3. `test_water.WaterMigrationTests.test_startup_does_not_apply_003`
4. `test_recipes.RecipeMigrationTests.test_unmigrated_app_compatibility`
5. `test_diet_demo.DemoTests.test_demo_config_and_normal_config_separate`
6. `usda_v2.test_seed.SeedTests.test_real_seed_api_search_nutrition_recommendation_and_cycle`
7. `usda_v3_course_demo.test_seed.CourseSeedTests.test_real_seed_api_search_nutrition_recommendation_and_cycle`
8. `usda_v3_course_demo.test_seed.CourseSeedTests.test_display_approval_is_bound_to_matching_imported_rows`

此外，真实应用相关的 `test_smoke.py` 3 项、`test_exercise.py` 6 项未执行，不计入通过数量。总计 17 项已知全站关联测试待成员 C 补交文件后执行。

共享 `test_smoke.py` 仅调整饮食认证前置测试：新增匿名 401，走真实注册/登录/健康数据授权后继续保留原来的无档案 409 断言。健康检查、CORS、五模块目录、其他数据库断言不变；由于真实 main 导入阻塞，该共享测试仍未计为通过。

已提供 `backend/tests/run_diet_full.py` 用于成员 C 修复后的真实全站验收。它不启用独立应用，且为原 v2/v3 包内两项旧联调测试绑定真实注册/登录/隐私授权客户端夹具，解决旧用例匿名调用私人 API 的问题；不改源包、不替换认证依赖或原断言。此入口当前只完成导入前置检查，确认真实运动模块仍阻塞，未宣称完整测试执行成功。

```powershell
# backend 目录，成员 C 补交缺失文件之后：
& ..\.venv\Scripts\python.exe -B tests/run_diet_full.py
```

## 前端及浏览器

前端 **66/66 通过**（饮食 61、运动原有逻辑 5），正式 `npm run build` 成功，117 个模块。未安装或升级依赖。

```powershell
# frontend 目录
node --test src/components/diet/*.test.js src/components/exercise/*.test.js
npm run build
```

浏览器连接独立临时验收后端 8018 与原 Vite 前端 5188，完成：

- 未建档/未登录直接浏览 134 食品、12 食谱；FDC 167746 搜索返回 1 项，水果分类返回 20 项；配料、步骤展开正常。公共资源没有编辑或归档按钮；匿名建立私人引用被拒绝。
- 通过真实 API 创建明确的临时测试账号/档案，再从界面登录。公共菜谱另存为私人副本成功；引用后不会自动创建饮食记录。
- 在记录表单选择公共柠檬，100g 显示并保存为 29kcal；私人库中的公共引用不能编辑。推荐显示 12 道公共食谱及 1 道私人副本，来源分别标注。
- 桌面 1280、手机 390px 和 320px 无横向溢出。320px 的传统滚动条触发了共享 body 最小宽度，修复仅写在 DietView 内，且只在饮食页面存在时生效；未修改共享 styles.css。
- PDF 与 PNG 实际下载成功。视觉检查 PNG、6 页 PDF 的首页和末页，均保留开发演示、非真实健康记录及课程审批标记；原导出逻辑自动化测试验证每页标记及普通环境无误标。
- 本轮创建的验收服务已停止，临时用户库及目录已清理；原用户服务未操作。截图/导出只在本机验收目录或 Downloads，不纳入 Git。

## 保护与限制

- 没有运行正式健康库、旧演示库或备份的迁移和数据写入；全部个人数据测试只使用独立临时库。
- 运动、用户、生理期、睡眠业务目录、公共认证/数据库配置、main.py、client.js、公共导航/共享样式均无 Git 差异。
- 已发布 001～004 与原 v2/v3 数据包无 Git 差异；未实现 005。
- `.gitignore` 仅放行公共目录中精确的 `food_catalog.db` 路径，其他 SQLite、sidecar、缓存、虚拟环境与本地配置继续忽略。
- 当前仍是团队共享单档案1；没有实现多档案归属，也没有以账号ID代替档案ID。
- 推荐“全部分类”包含公共和私人菜谱；指定私人分类时只推荐该私人分类，界面已注明。
- 数据只获课程演示批准；未完成实际试做或全面过敏安全核验。
- 没有执行 Git add、commit、push 或 merge。

成员 C 修复后应使用全新临时个人库运行真实 main，验证健康检查/CORS/五模块目录、真实 profile 认证与饮食权限、饮食与生理期/运动/睡眠共存、公开目录故障隔离、原演示服务器及 PDF/PNG 导出，再确认完整集成验收结论。独立开发结果已具备进入该阶段的条件，但不能宣称全站验收通过。

## Git 最终变更清单

共 29 个已有文件修改、23 个新增文件（均未暂存）。完整清单如下；最大新增文件为公共数据库 651264 字节。

| 状态 | 路径 |
|---|---|
| M | `.gitignore` |
| M | `backend/app/modules/diet/README.md` |
| M | `backend/app/modules/diet/docs/API-CATALOG.md` |
| M | `backend/app/modules/diet/docs/ARCHITECTURE.md` |
| M | `backend/app/modules/diet/library_schemas.py` |
| M | `backend/app/modules/diet/library_service.py` |
| M | `backend/app/modules/diet/recipe_recommendation.py` |
| M | `backend/app/modules/diet/router.py` |
| M | `backend/tests/test_diet.py` |
| M | `backend/tests/test_diet_demo.py` |
| M | `backend/tests/test_diet_migrations.py` |
| M | `backend/tests/test_food_library.py` |
| M | `backend/tests/test_nutrition.py` |
| M | `backend/tests/test_recipes.py` |
| M | `backend/tests/test_smoke.py` |
| M | `backend/tests/test_water.py` |
| M | `frontend/src/api/diet.js` |
| M | `frontend/src/api/foodLibrary.js` |
| M | `frontend/src/components/diet/DietRecordsPanel.vue` |
| M | `frontend/src/components/diet/FoodNutritionCard.vue` |
| M | `frontend/src/components/diet/RecipeInventoryPanel.vue` |
| M | `frontend/src/components/diet/RecipeLibraryPanel.vue` |
| M | `frontend/src/components/diet/RecipePreferencePanel.vue` |
| M | `frontend/src/components/diet/RecipeRecommendationPanel.vue` |
| M | `frontend/src/components/diet/RecipeWorkspace.vue` |
| M | `frontend/src/components/diet/WaterReminderHost.vue` |
| M | `frontend/src/components/diet/foodPresentation.js` |
| M | `frontend/src/components/diet/recipeSource.js` |
| M | `frontend/src/views/DietView.vue` |
| ?? | `backend/app/modules/diet/access.py` |
| ?? | `backend/app/modules/diet/build_catalog.py` |
| ?? | `backend/app/modules/diet/catalog_data/.gitattributes` |
| ?? | `backend/app/modules/diet/catalog_data/README.md` |
| ?? | `backend/app/modules/diet/catalog_data/SHA256SUMS.txt` |
| ?? | `backend/app/modules/diet/catalog_data/catalog-release.json` |
| ?? | `backend/app/modules/diet/catalog_data/food_catalog.db` |
| ?? | `backend/app/modules/diet/catalog_links.py` |
| ?? | `backend/app/modules/diet/catalog_preview.py` |
| ?? | `backend/app/modules/diet/catalog_repository.py` |
| ?? | `backend/app/modules/diet/catalog_router.py` |
| ?? | `backend/app/modules/diet/docs/PUBLIC-CATALOG-ACCEPTANCE.md` |
| ?? | `backend/app/modules/diet/docs/PUBLIC-CATALOG.md` |
| ?? | `backend/app/modules/diet/migration_006.py` |
| ?? | `backend/tests/diet_catalog_app.py` |
| ?? | `backend/tests/diet_test_runtime.py` |
| ?? | `backend/tests/run_diet_full.py` |
| ?? | `backend/tests/run_diet_isolated.py` |
| ?? | `backend/tests/test_public_catalog.py` |
| ?? | `frontend/src/api/catalog.js` |
| ?? | `frontend/src/components/diet/CatalogPanel.vue` |
| ?? | `frontend/src/components/diet/PublicFoodPicker.vue` |
| ?? | `frontend/src/components/diet/catalogPresentation.test.js` |
