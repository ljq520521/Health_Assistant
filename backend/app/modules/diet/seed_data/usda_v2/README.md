# 饮食 v2 种子包：仅限本地演示，待团队最终审核

本包包含 134 种 USDA FoodData Central 来源食物、12 道项目团队自编、AI 辅助中文菜谱草案。
所有菜谱未经实际试做；营养由食材投料估算，不是成品实测。中文名称、匹配关系、成分与过敏原仍需人工核对。
数据包保持 `temporary_review` / `pending_final_confirmation`，提交 GitHub 不代表数据获得正式批准。

不包含用户档案数据文件、45 条饮食记录、18 条饮水记录、病史、账号、凭证或 SQLite 数据库。
运行时只通过已有 `demo_environment.initialize_empty` 创建明确标记的临时演示档案 `profile_id=1`。
首版只支持本地单档案；不能当作正式多用户导入工具。

## 来源、体积与校验

- `foods.json` 与原 v2 完全相同：身份、中文名、英文原名、营养数值、来源和待审核状态全部保留。
- `recipes.json` 只在 `source_note` 补充“未经实际试做。”，其他字段不变。
- 数据包仍为版本 2，精简分发格式为 1；新包 ID 为 `common-food-cn-preview-compact`，原 ID、版本和哈希保存在 `PROVENANCE.json`。
- `sources/*.zip` 是选定食物的**原始记录子集，不是完整 USDA 压缩包**。保留原文件名只为兼容原 `foods.json` 的 `source_archive` 引用。
- 原始记录不删字段、不改数值；逐记录哈希保存在 `provenance/source-record-sha256.json`，导入时再次校验。
- `provenance/original-manifest.json` 是原清单的留档，不是本包的导入入口；其中完整源包、原审核材料和 PDF 不随本包分发。
- 原来源版本：SR Legacy 2018-04、Foundation 2026-04-30。完整源包 SHA256 与官方 URL 见 `PROVENANCE.json`。
- 许可和署名见 `LICENSE-SOURCES.md`；USDA CC0 不自动覆盖团队菜谱或代码。

原 v2 manifest SHA256：
`bdc647117fe396ee04d7bac93bd0ef5b1d1cf22e7b8fd02047565470bb2321a6`

本种子包 manifest SHA256（固定在演示命令中）：
`2391951c2738a0b5ca181c441a216d872731f9eed8fc8290b2e6001610f4e29b`

`SHA256SUMS.txt` 列出本目录其他所有交付文件的哈希。更改数据、审核状态或来源文件后，旧哈希会拒绝导入，不能只改字段冒充审批。

## 克隆后准备环境

使用 Python 3.12 和项目锁定的后端依赖；已有 `.venv` 时不要覆盖。
前端使用项目原有 Node 要求和 `package-lock.json`（`npm ci`），不升级版本。
下面命令在项目的 `backend` 目录执行，例如：

```powershell
Set-Location C:\Users\Administrator\Documents\Health_Assistant-Team\backend
& ..\.venv\Scripts\python.exe --version
```

其他组员只需把目录改为自己的克隆路径，后续命令保持相同。无需联网下载 USDA 原包，无需 API key。

## 默认预览：不导入食物或菜谱

```powershell
& ..\.venv\Scripts\python.exe -B -m app.modules.diet.seed_data.usda_v2.demo_seed
```

命令先校验固定 manifest、所有关联文件及 USDA 身份/营养值。然后只在全新的 `TemporaryDirectory` 中，
通过现有流程基础初始化 → 显式 001 → 002 → 003 → 004 → 创建演示档案，运行现有 `import_service.dry_run`。
预期 `add=146, skip=0, conflict=0`。默认预览不导入业务行、不保存审计文件，退出时清理整个临时目录。
它不会读取 `HEALTH_DB_PATH` 来选择目标，也不会连接项目默认 `backend/data/health.db`。

## 一条命令建立可用的课堂演示库

在确认允许创建独立演示数据后执行：

```powershell
& ..\.venv\Scripts\python.exe -B -m app.modules.diet.seed_data.usda_v2.demo_seed --create-demo --apply
```

只创建新的系统临时目录 `health-diet-seed-*/demo.db`；不接受现有路径作为新库目标，不覆盖文件。
新库显式完成 001～004 和合法演示建档后，先 dry-run，再调用原 `import_service.apply_package` 原子导入。
结果应为 `status=committed`，134 食物和 12 菜谱可用；打印 `database_path`、计划哈希和审计目录。
`--create-demo` 不加 `--apply` 时只保留结构、演示档案及预览结果，尚未导入食物/菜谱。
每次 `--create-demo` 都建立不同的新库。若操作已有演示库，使用下一节而不是反复新建。
失败时停止；新建库及已有审计保留以供核查，不自动回滚到其他备份或连接正式库。

## 已有演示库：先预览，再明确确认

仅接受本工具创建、具有匹配 `SEED_DEMO_ONLY.json` 标识的临时 `demo.db`。
不会补跑迁移、补建档案或把普通数据库改标成演示库。

```powershell
$demoDb = '把上一步输出的 database_path 完整粘贴到这里'
$previewJson = & ..\.venv\Scripts\python.exe -B -m app.modules.diet.seed_data.usda_v2.demo_seed --database $demoDb
if ($LASTEXITCODE -ne 0) { throw '预览失败，停止；不得覆盖或篡改审核字段' }
$preview = $previewJson | ConvertFrom-Json -ErrorAction Stop
$preview | Format-List
```

重复预览应为 `add=0, skip=146, conflict=0`。确认计划后，才执行：

```powershell
& ..\.venv\Scripts\python.exe -B -m app.modules.diet.seed_data.usda_v2.demo_seed --database $demoDb --apply --confirm-database $demoDb --expected-plan-sha256 $preview.plan_sha256
```

同一来源内容不变则跳过；来源冲突、归档、用户改动、计划过期、缺少档案、迁移不全或外键异常都会停止。
审计保存在该演示目录的 `audit` 中，不放到仓库。不要删除审计或来源标记来强行重复导入。
普通 `app.modules.diet.import_data` 会拒绝本待审核包，这是预期保护行为；不能以修改审核字段解除保护。

## 在团队网站查看演示数据

在 backend 终端使用上一步真实输出的路径，不使用示例字符串直接启动：

```powershell
$env:HEALTH_DIET_SEED_DB = '把已导入成功的 database_path 完整粘贴到这里'
$env:HEALTH_DB_PATH = $env:HEALTH_DIET_SEED_DB
$env:DIET_APPLY_MIGRATIONS = '0'
& ..\.venv\Scripts\python.exe -B -m uvicorn app.modules.diet.seed_data.usda_v2.demo_seed:create_demo_app --factory --host 127.0.0.1 --port 8002
```

演示工厂校验标识和档案，并让 `Settings` 与 `HEALTH_DB_PATH` 使用同一库，包含生理期直接调用 `get_settings()` 的路径。
不会在启动时运行饮食迁移；原 `main.py` 未修改。`/api/diet/config` 返回 `approved=false` 及待审核说明。

在另一个终端进入克隆项目的 frontend 目录：

```powershell
$env:API_PROXY_TARGET = 'http://127.0.0.1:8002'
$env:FRONTEND_PORT = '5175'
$env:VITE_API_BASE_URL = ''
npm run dev
```

打开 http://127.0.0.1:5175/diet 。两个终端均需保持运行；退出各按 Ctrl+C。
选择“食谱推荐 → 获取食谱推荐”。未设置目标、库存、偏好时缺失维度显示空评分，仍可展示菜谱及缺料说明；
在演示库中设置目标和库存后复用现有推荐评分。成分未核对时禁忌规则可能保守排除菜谱，不应放松过滤来追求数量。
原有课堂记录未随本包导入，因此饮食记录、饮水和报告初始为空是正常的。
临时目录可能被系统清理；如需备份演示成果，应另行确认备份范围，不覆盖正式数据。

## 种子验收

```powershell
& ..\.venv\Scripts\python.exe -B -m unittest app.modules.diet.seed_data.usda_v2.test_seed -v
```

测试全部使用新建临时 SQLite，显式迁移和演示建档；验证 dry-run、134/12 数据、幂等跳过、冲突阻断、
普通入口拒绝待审包、失效计划、缺迁移/档案、事务回滚、真实食物搜索、营养计算、推荐和生理期联调。
测试结束清理临时库。原有完整后端回归须继续遵守统一的临时数据库隔离要求。
