# 饮食模块交付文件清单

这是当前文件的完整范围清单和SHA256，不是假定的Git变更列表。项目缺少.git，新增/修改的最终判定必须由团队基线diff完成。
业务范围：backend/app/modules/diet、frontend/src/components/diet、DietView、6个饮食API封装及饮食测试。test_smoke.py和其他公共文件需要逐块核对，不能整文件覆盖团队版本。

| 文件 | 职责/顶层符号 |
| --- | --- |
| `backend/app/modules/diet/__init__.py` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `backend/app/modules/diet/build_import_preview.py` | write, build, main |
| `backend/app/modules/diet/data/import_preparation/food.schema.json` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `backend/app/modules/diet/data/import_preparation/food_candidates_150.json` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `backend/app/modules/diet/data/import_preparation/food_matches.json` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `backend/app/modules/diet/data/import_preparation/manifest.schema.json` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `backend/app/modules/diet/data/import_preparation/recipe.schema.json` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `backend/app/modules/diet/data/import_preparation/recipe_drafts_30.json` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `backend/app/modules/diet/demo_environment.py` | safe_path, read_context, labelled_payloads, initialize_empty, create_demo, main |
| `backend/app/modules/diet/demo_server.py` | create_demo_app |
| `backend/app/modules/diet/dev_database.py` | main |
| `backend/app/modules/diet/import_data.py` | main |
| `backend/app/modules/diet/import_schemas.py` | Strict, FileRef, Source, Manifest, Food, Ingredient, Recipe |
| `backend/app/modules/diet/import_service.py` | verify_review_state, _no_bools, _csv, load_package, database, snapshot, marker, note, food_payload, recipe_payload, _category, _same_food, _same_recipe, plan, verify_audit_history, dry_run, write_audit, apply_package |
| `backend/app/modules/diet/library_router.py` | LibraryRoute, database_path, config, categories, create_category, get_category, update_category, delete_category, foods, create_food, get_food, update_food, archive_food |
| `backend/app/modules/diet/library_schemas.py` | CategoryInput, CategoryRecord, CategoryList, FoodInput, FoodRecord, FoodList |
| `backend/app/modules/diet/library_service.py` | LibraryError, ready, category_row, categories, get_category, save_category, delete_category, food_row, foods, get_food, save_food, save_food_in_connection, archive_food |
| `backend/app/modules/diet/migration_002.py` | verify_schema, ready, migrate_goals, main |
| `backend/app/modules/diet/migration_003.py` | verify_schema, ready, migrate_water, main |
| `backend/app/modules/diet/migration_004.py` | verify_schema, ready, migrate_recipes, main |
| `backend/app/modules/diet/migrations.py` | _tables, _verify_schema, migration_ready, migrate_diet, initialize_diet_schema, main |
| `backend/app/modules/diet/nutrition_math.py` | number, scale, total, percent |
| `backend/app/modules/diet/nutrition_router.py` | goal, history, save, summary, record_summary |
| `backend/app/modules/diet/nutrition_schemas.py` | GoalChanges |
| `backend/app/modules/diet/nutrition_service.py` | require_goals, effective, get_goal, history, save_goal, period, summary, summarize_rows, record_summary |
| `backend/app/modules/diet/prepare_sources.py` | prepare, main |
| `backend/app/modules/diet/recipe_preference_router.py` | inventory, add_inventory, get_inventory, update_inventory, delete_inventory, resolve, terms, create_term, term, update_term, delete_term, composition, update_composition, preferences, create_preference, preference, update_preference, delete_preference |
| `backend/app/modules/diet/recipe_preference_schemas.py` | InventoryInput, TermInput, CompositionTerm, CompositionInput, PreferenceInput |
| `backend/app/modules/diet/recipe_preference_service.py` | transaction, inventory, save_inventory, delete_inventory, term_row, terms, resolve, save_term, delete_term, composition_row, composition, save_composition, preferences, save_preference, delete_preference |
| `backend/app/modules/diet/recipe_recommendation.py` | RecommendationInput, matches, recommend |
| `backend/app/modules/diet/recipe_recommendation_router.py` | preview |
| `backend/app/modules/diet/recipe_router.py` | categories, create_category, category, update_category, delete_category, recipes, create, get, update, archive, refresh |
| `backend/app/modules/diet/recipe_schemas.py` | Input, Revision, IngredientInput, RecipeInput |
| `backend/app/modules/diet/recipe_service.py` | key, require_recipes, conflict, one, categories, category, save_category, delete_category, nutrition, detail, get, recipes, save, save_in_connection, refresh, archive |
| `backend/app/modules/diet/report_router.py` | get_report |
| `backend/app/modules/diet/report_service.py` | today, average, report |
| `backend/app/modules/diet/router.py` | database_path, list_records, create_record, get_record, update_record, delete_record |
| `backend/app/modules/diet/schemas.py` | calendar_date, DietInput, CatalogInput, DietRecord, DietList |
| `backend/app/modules/diet/service.py` | require_profile, find_record, list_records, get_record, save_record, delete_record |
| `backend/app/modules/diet/settings.py` | utc_now |
| `backend/app/modules/diet/source_mapping.py` | ImportRejected, sha, canonical, digest, _pairs, json_read, local_file, verified_bytes, archive_records, mapped_nutrients, verify_foods |
| `backend/app/modules/diet/verify_import_preview.py` | verify, main |
| `backend/app/modules/diet/water_router.py` | records, create, get, update, delete, summary, reminder, save_reminder |
| `backend/app/modules/diet/water_schemas.py` | timestamp, WaterInput, ReminderInput |
| `backend/app/modules/diet/water_service.py` | require_water, utc, boundary, row, get, records, save, delete, summary, summarize_amounts, reminder_row, get_reminder, save_reminder |
| `backend/tests/diet_import_fixtures.py` | write_json, fixture, rehash |
| `backend/tests/test_diet.py` | DietTests |
| `backend/tests/test_diet_demo.py` | DemoTests |
| `backend/tests/test_diet_import.py` | ImportTests |
| `backend/tests/test_diet_import_recommendation.py` | ImportedRecommendationTests |
| `backend/tests/test_diet_migrations.py` | MigrationTests, MigratedDietTests |
| `backend/tests/test_food_library.py` | FoodLibraryTests |
| `backend/tests/test_nutrition.py` | NutritionTests, GoalsMigrationTests, FullSchemaDietTests, FullSchemaFoodTests |
| `backend/tests/test_recipe_preferences.py` | RecipePreferencesTests |
| `backend/tests/test_recipe_recommendation.py` | RecommendationTests |
| `backend/tests/test_recipes.py` | RecipeFixture, RecipeTests, RecipeMigrationTests |
| `backend/tests/test_reports.py` | ReportTests |
| `backend/tests/test_smoke.py` | ScaffoldTests |
| `backend/tests/test_water.py` | WaterTests, WaterMigrationTests |
| `frontend/src/api/diet.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/api/foodLibrary.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/api/nutrition.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/api/recipes.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/api/reports.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/api/water.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/DailyGoalsDialog.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/DietRecordsPanel.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/DietReportPanel.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/FoodLibraryPanel.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/NutritionAnalysisPanel.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/NutritionTrendChart.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/RecipeInventoryPanel.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/RecipeLibraryPanel.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/RecipeNutrition.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/RecipePreferencePanel.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/RecipeRecommendationPanel.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/recipeUI.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/RecipeWorkspace.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/report.test.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/ReportChart.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/reportExport.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/reportPdf.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/reportPresentation.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/WaterPanel.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/waterReminder.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/waterReminder.test.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/WaterReminderHost.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/components/diet/waterTime.js` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
| `frontend/src/views/DietView.vue` | 前端组件/逻辑/接口或数据准备资料，依赖见DEPENDENCIES.json |
