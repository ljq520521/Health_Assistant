# 饮食模块 API 清单（由当前 FastAPI OpenAPI 提取）

公共目录扩展新增的 9 个操作、身份键及权限规则见 [PUBLIC-CATALOG.md](PUBLIC-CATALOG.md#api)。下表保留原 60 个操作清单，不能作为本次新增 API 的完整描述；私人接口现要求有效登录和健康数据授权，写操作限管理员，公共目录 GET 与时区配置允许匿名。原 `openapi-diet.json` 是历史交付快照，当前接口以源码和运行中的 `/docs` 为准。

仅列真实已注册路由。请求模型完整字段/枚举见 [openapi-diet.json](openapi-diet.json) 的 components.schemas；参数约束以该文件及实际 /docs 为准。动态字典响应请结合服务函数与模块 README。

| 方法 | 路径 | Query / Path 参数 | 请求模型 | 响应状态 |
| --- | --- | --- | --- | --- |
| GET | `/api/diet-records` | date_from, date_to | — | 200, 422 |
| POST | `/api/diet-records` | — | DietInput/CatalogInput | 201, 422 |
| GET | `/api/diet-records/{id}` | id（必填） | — | 200, 422 |
| PUT | `/api/diet-records/{id}` | id（必填） | DietInput/CatalogInput | 200, 422 |
| DELETE | `/api/diet-records/{id}` | id（必填） | — | 204, 422 |
| GET | `/api/diet/config` | — | — | 200 |
| GET | `/api/diet/food-categories` | — | — | 200 |
| POST | `/api/diet/food-categories` | — | CategoryInput | 201, 422 |
| GET | `/api/diet/food-categories/{id}` | id（必填） | — | 200, 422 |
| PUT | `/api/diet/food-categories/{id}` | id（必填） | CategoryInput | 200, 422 |
| DELETE | `/api/diet/food-categories/{id}` | id（必填） | — | 204, 422 |
| GET | `/api/diet/foods` | q, category_id, uncategorized | — | 200, 422 |
| POST | `/api/diet/foods` | — | FoodInput | 201, 422 |
| GET | `/api/diet/foods/{id}` | id（必填） | — | 200, 422 |
| PUT | `/api/diet/foods/{id}` | id（必填） | FoodInput | 200, 422 |
| DELETE | `/api/diet/foods/{id}` | id（必填） | — | 204, 422 |
| GET | `/api/diet/goals` | date（必填） | — | 200, 422 |
| PUT | `/api/diet/goals` | — | GoalChanges | 200, 422 |
| GET | `/api/diet/goals/history` | — | — | 200 |
| GET | `/api/diet/nutrition-summary` | date_from（必填）, date_to（必填）, group_by | — | 200, 422 |
| GET | `/api/diet/record-summary` | date_from, date_to | — | 200, 422 |
| GET | `/api/diet/water-records` | date_from, date_to | — | 200, 422 |
| POST | `/api/diet/water-records` | — | WaterInput | 201, 422 |
| GET | `/api/diet/water-records/{id}` | id（必填） | — | 200, 422 |
| PUT | `/api/diet/water-records/{id}` | id（必填） | WaterInput | 200, 422 |
| DELETE | `/api/diet/water-records/{id}` | id（必填） | — | 204, 422 |
| GET | `/api/diet/water-summary` | date（必填） | — | 200, 422 |
| GET | `/api/diet/water-reminder-settings` | — | — | 200 |
| PUT | `/api/diet/water-reminder-settings` | — | ReminderInput | 200, 422 |
| GET | `/api/diet/recipe-categories` | — | — | 200 |
| POST | `/api/diet/recipe-categories` | — | CategoryInput | 201, 422 |
| GET | `/api/diet/recipe-categories/{id}` | id（必填） | — | 200, 422 |
| PUT | `/api/diet/recipe-categories/{id}` | id（必填） | CategoryInput | 200, 422 |
| DELETE | `/api/diet/recipe-categories/{id}` | id（必填） | — | 204, 422 |
| GET | `/api/diet/recipes` | q, category_id | — | 200, 422 |
| POST | `/api/diet/recipes` | — | RecipeInput | 201, 422 |
| GET | `/api/diet/recipes/{id}` | id（必填） | — | 200, 422 |
| PUT | `/api/diet/recipes/{id}` | id（必填） | RecipeInput | 200, 422 |
| DELETE | `/api/diet/recipes/{id}` | id（必填） | — | 204, 422 |
| POST | `/api/diet/recipes/{id}/refresh-nutrition` | id（必填） | Revision | 200, 422 |
| GET | `/api/diet/inventory-items` | — | — | 200 |
| POST | `/api/diet/inventory-items` | — | InventoryInput | 201, 422 |
| GET | `/api/diet/inventory-items/{id}` | id（必填） | — | 200, 422 |
| PUT | `/api/diet/inventory-items/{id}` | id（必填） | InventoryInput | 200, 422 |
| DELETE | `/api/diet/inventory-items/{id}` | id（必填） | — | 204, 422 |
| GET | `/api/diet/ingredient-terms/resolve` | name（必填） | — | 200, 422 |
| GET | `/api/diet/ingredient-terms` | q | — | 200, 422 |
| POST | `/api/diet/ingredient-terms` | — | TermInput | 201, 422 |
| GET | `/api/diet/ingredient-terms/{id}` | id（必填） | — | 200, 422 |
| PUT | `/api/diet/ingredient-terms/{id}` | id（必填） | TermInput | 200, 422 |
| DELETE | `/api/diet/ingredient-terms/{id}` | id（必填） | — | 204, 422 |
| GET | `/api/diet/foods/{id}/composition` | id（必填） | — | 200, 422 |
| PUT | `/api/diet/foods/{id}/composition` | id（必填） | CompositionInput | 200, 422 |
| GET | `/api/diet/food-preferences` | — | — | 200 |
| POST | `/api/diet/food-preferences` | — | PreferenceInput | 201, 422 |
| GET | `/api/diet/food-preferences/{id}` | id（必填） | — | 200, 422 |
| PUT | `/api/diet/food-preferences/{id}` | id（必填） | PreferenceInput | 200, 422 |
| DELETE | `/api/diet/food-preferences/{id}` | id（必填） | — | 204, 422 |
| POST | `/api/diet/recipe-recommendations/preview` | — | RecommendationInput | 200, 422 |
| GET | `/api/diet/reports` | date（必填）, period | — | 200, 422 |

通用业务状态：无档案409 PROFILE_REQUIRED；资源不存在404；校验422；模块未迁移503；冲突409。OpenAPI表仅自动列声明状态，不代表未列出的业务错误不会发生。
饮食旧路由部分HTTPException仅返回detail；LibraryError返回detail和code；422的detail为数组。config无需个人档案。
DELETE food/recipe为归档，不是物理删除；成分类、偏好、库存等删除语义见服务代码。GET不进行测试业务写入。
营养目标PUT按提交字段合并；饮食/食物/菜谱/饮水等PUT按各自完整模型处理，不能套用同一种合并策略。
