# 饮食营养模块：小组集成交付 README

2026-10-29 推荐策略调整：未填写、未核验或核对过期的成分信息不再单独排除食谱，保留未知提示和未核验状态。已记录的具体食物、同源食品、明确食材名称/人工别名，以及 contains/may_contain 成分命中的过敏/禁用规则仍先于评分排除。名称只做精确匹配（允许去掉末尾加工状态括注），不做子串猜测或交叉过敏推断。周计划上下文包含算法版本与术语别名，旧计划保留并提示确认刷新。

## 一周计划扩展（2026-10-28，依赖公共目录）

新增 7 天 21 餐次预览、明确确认后的计划保存、档案相关信息检测、五种执行反馈和不可变历史版本。仍使用团队本机单档案及真实账号/健康数据授权，不推断热量，不自动写实际摄入记录。005 依赖 006，均须显式部署，普通启动不自动迁移。完整接口、统计口径、数据归属和两阶段 PR 边界见 [周计划说明](docs/WEEKLY-PLANS.md)，最终验证见 [周计划验收记录](docs/WEEKLY-ACCEPTANCE.md)。

## 公共目录扩展（2026-10-28）

新增随项目分发的只读 `catalog_data/food_catalog.db`，支持无需档案浏览 134 种公共食物与 12 道菜谱；私人引用使用独立 006 扩展迁移。六项既有功能与原始 v2/v3 数据包保留。当前认证复用团队真实账号和健康数据授权，私人 API 不再允许匿名访问。

本次的架构、9 个新增 HTTP 操作、006、使用和回退流程见 [公共目录说明](docs/PUBLIC-CATALOG.md)，当前真实应用复核见 [全站复核记录](docs/PUBLIC-CATALOG-FULL-ACCEPTANCE.md)，前一轮独立结果保留于 [历史验收记录](docs/PUBLIC-CATALOG-ACCEPTANCE.md)。下文 60 接口、17 表、旧环境测试数量及生成清单属于原交付基线，不包含本次扩展。成员 C 的缺失文件已在最新 main dcb9c4b 补齐；真实五模块应用导入、启动和后端联调已复核。

更新时间：2026-10-15。当前六项功能已完成代码开发。团队集成第四步第一部分仅调整显式迁移策略测试与饮食内部文档，未执行运行测试、数据库迁移或演示库操作；下文旧开发环境验收记录不代表团队集成测试已通过。

## 交付入口

- [完整文件清单](docs/FILE-MANIFEST.md)、[源码SHA256](docs/SOURCE-MANIFEST.json)：89个当前业务/测试/准备资料文件。没有Git历史，不能将它当作相对团队基线的新增/修改差异。
- [全部API清单](docs/API-CATALOG.md)、[OpenAPI定义](docs/openapi-diet.json)：60个HTTP操作。
- [数据库字段、外键、DDL、索引](docs/DATABASE-CATALOG.md)、[结构JSON](docs/database-schema.json)：17张饮食相关表（含迁移登记）及共享profiles依赖。
- [前后端组件与依赖](docs/ARCHITECTURE.md)、[逐文件导入关系](docs/DEPENDENCIES.json)。
- [成员A与多用户接入、Git及跨模块联调](docs/TEAM-INTEGRATION.md)、[单档案定位清单](docs/SINGLE-PROFILE-LOCATIONS.json)。

共享docs中的早期“待开发”和旧批次描述并不代表当前实现状态。当前以此模块README、源码和实际Swagger为准；共享文档的合并更新需由团队确认。

## 功能与统计口径

1. 饮食记录：日期/餐次/克重/备注CRUD；手动或食物库模式；营养快照由后端计算，旧手动请求保持兼容。
2. 食物库：分类CRUD、中文名称搜索、归档、每100g四项营养、来源标记。NULL未知，0为真实零；公开来源不是过敏安全证明。
3. 营养分析：按生效日期保存目标；日/周/月、日期范围、趋势、比例。周一为周起点，月为自然月，范围最多366天。缺数据不推断为实际零摄入。
4. 饮水：UTC时间、ml及备注CRUD；复用目标water_ml；页面内固定/间隔提醒、去重和稍后提醒。离开/diet停止；不支持关浏览器后的后台推送。
5. 食谱推荐：食谱/分类/库存/术语别名/成分核对/偏好管理；禁忌先过滤后评分。无库存/喜好时对应维度NULL、不参与；有效权重归一化。评分不是医学健康分。
6. 报告：日/周/月实时只读汇总，复用营养和饮水统计；可追溯规则建议；原生Canvas生成图片型PDF、PNG，无PDF依赖，无005迁移。

目标PUT按字段合并：未提交字段保留，显式null清空；其他PUT遵守各自输入模型，不能统一当PATCH。营养按Decimal换算并保留4位小数；改食物库不改变历史快照。报告两种热量平均分别除以有记录天数和区间天数，都只是已知记录的摊分。

## 安装（其他组员的新工作副本）

Python 3.12，Node >=22.12.0。现有依赖锁定于backend/requirements.txt及frontend/package-lock.json：FastAPI 0.141.1、Vue 3.5.43、Vite 7.3.6；Windows时区依赖tzdata 2026.5。不要复制当前机器的.venv或node_modules。

在新工作副本根目录用PowerShell：

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location frontend
npm ci
Set-Location ..
```

安装命令是交付说明，本轮未安装或升级依赖。团队项目使用全新Python 3.12虚拟环境；先确认`py -3.12 --version`成功，若`.venv`已存在则停止并核对，不覆盖。旧项目复制的.venv曾失效，历史验收使用过单独的diet-venv，不能将其视为团队当前可用环境。每条安装命令失败后应停止，不自动更换锁定版本或改用其他Python版本运行测试。

## 初始化与001～004迁移

部署时需要显式准备目标数据库，顺序：`app.database.init_database` → `migrations`（001）→ `migration_002` → `migration_003` → `migration_004`。不能只运行init.sql就期待完整饮食功能；迁移与普通FastAPI启动分开执行。

| 版本 | 入口模块（app.modules.diet下） | 增量内容 |
| --- | --- | --- |
| 001_food_library | migrations | food_categories、food_items、diet_schema_migrations；diet_records追加关联/营养/快照字段及索引 |
| 002_daily_goals | migration_002 | diet_daily_goals，含water_ml预留字段 |
| 003_water | migration_003 | water_records、water_reminder_settings及时间索引 |
| 004_recipes | migration_004 | 食谱/库存/术语/成分/偏好10表及索引 |

001～004各自显式BEGIN IMMEDIATE，使用现有connect提交/回滚，不重建diet_records。每一步单独事务，并非四步共用一个事务；若004失败，先前成功的001～003保留，004整体回滚。重复运行返回未变更；校验和冲突、未登记扩展表或已知结构异常停止，不能手动删除迁移记录硬重跑。基础初始化沿用团队init.sql事务，不额外重复添加初始化入口。

团队普通FastAPI启动只保留原有基础表初始化，不自动执行饮食001～004；即使`DIET_APPLY_MIGRATIONS=1`也不会触发饮食迁移。main.py注入`application.state.settings`供路由读取数据库路径，但不导入或调用`initialize_diet_schema`。

旧辅助函数`initialize_diet_schema`仍保留在migrations.py中，直接调用它且环境变量为1仍可能执行001；团队启动流程不使用该函数，也不将其作为部署入口。环境变量不再是应用启动迁移开关，示例设置0仅用于避免旧工具误触发。使用下述显式命令，或在独立临时库测试中直接调用对应迁移函数。

普通启动不再进行饮食迁移的统一校验；显式迁移和相关业务请求会检查迁移状态。已有合法档案但尚未执行001时，食物库返回503和`DIET_MIGRATION_REQUIRED`；未建档则优先返回409和`PROFILE_REQUIRED`。002～004缺失时相应功能返回迁移提示。结构或校验和异常应停止相关操作并核对版本，不能用空表或删库掩盖错误。

### 推荐新成员使用全新临时验收库

```powershell
# 已在项目根目录，且Python 3.12虚拟环境与固定依赖已准备好。
Set-Location backend
$env:DIET_APPLY_MIGRATIONS = '0'
$testInfoJson = & ..\.venv\Scripts\python.exe -B -m app.modules.diet.dev_database
if ($LASTEXITCODE -ne 0) { throw '临时库创建失败，停止' }
$testInfo = $testInfoJson | ConvertFrom-Json -ErrorAction Stop
if ($testInfo.temporary -ne $true -or -not $testInfo.database_path) { throw '临时库信息无效，停止' }
$env:HEALTH_DB_PATH = $testInfo.database_path
$env:HEALTH_DB_PATH
& ..\.venv\Scripts\python.exe -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

以上命令仅供获得临时库准备和测试授权后执行，本轮未执行。dev_database是显式准备工具：每次创建新系统临时库，依次调用全部001～004迁移函数，创建明确标记的测试档案；不接受现有目标路径。这些写入发生在运行工具时，不由后续FastAPI启动触发。`--without-profile`用于409验收。不要加`--demo`来冒充真实食物，那个选项仅产生明确标记的虚构测试数据。134/12待审数据包不是本工具默认内置食物。

### 在全新临时库逐步显式初始化和迁移

以下是上节一体化工具的替代流程，在backend目录执行，仍须单独获得临时库迁移授权。路径由tempfile生成，不使用正式health.db、现有集成库或演示库路径：

```powershell
$env:DIET_APPLY_MIGRATIONS = '0'
$targetDb = & ..\.venv\Scripts\python.exe -B -c 'from pathlib import Path; import tempfile; print(Path(tempfile.mkdtemp(prefix="health-diet-integration-")) / "health.db")'
if ($LASTEXITCODE -ne 0 -or -not $targetDb) { throw '临时路径生成失败，停止' }
if (-not [System.IO.Path]::IsPathRooted($targetDb) -or (Test-Path -LiteralPath $targetDb)) { throw '必须使用全新临时数据库路径' }
$env:HEALTH_DB_PATH = $targetDb
& ..\.venv\Scripts\python.exe -B -c 'import sys; from pathlib import Path; from app.database import init_database; init_database(Path(sys.argv[1]))' $targetDb
if ($LASTEXITCODE -ne 0) { throw '基础初始化失败，停止' }
foreach ($module in @('migrations','migration_002','migration_003','migration_004')) {
    & ..\.venv\Scripts\python.exe -B -m "app.modules.diet.$module" --database $targetDb --apply
    if ($LASTEXITCODE -ne 0) { throw "迁移失败：$module；停止，禁止自动恢复覆盖" }
}
```

此流程不插入档案，直接请求需要档案的接口仍会返回409；自动测试由各自夹具在独立临时库创建合法测试档案，交互功能验收可使用上一节工具创建的明确标记测试档案。去掉`--apply`为迁移状态检查；再次显式执行应幂等。

已有库或正式部署必须单独确认目标绝对路径、停止写入、完成备份及恢复验证，并在备份副本演练后再批准001～004显式迁移；不能把上述临时库命令改成正式路径后直接执行。不得改变已发布迁移SQL以“修复”现有库，未来新结构应单独设计新版本并经批准。

dev_database和上述mkdtemp流程创建的临时目录不会随命令结束自动删除；记录打印路径，验收后先停止服务、关闭连接，再核对目录身份后清理。不要删除或覆盖其他临时目录。

## 前后端启动与连接检查

后端使用上节明确指定的HEALTH_DB_PATH。配置相对路径以项目根目录解析，不以终端目录解析；在backend目录可只读打印：

```powershell
& ..\.venv\Scripts\python.exe -c 'from app.config import get_settings; print(get_settings().database_path.resolve())'
```

前端另开终端，在frontend目录：

```powershell
$env:API_PROXY_TARGET = 'http://127.0.0.1:8000'
$env:FRONTEND_PORT = '5173'
$env:VITE_API_BASE_URL = ''
npm run dev -- --configLoader native
```

若依赖预构建受目录权限限制，用已验证的预览方式，不扩大目录权限：

```powershell
npm run build -- --configLoader native
if ($LASTEXITCODE -eq 0) { npm run preview -- --configLoader native --port 5173 --strictPort }
```

访问 `/diet`，后端 `/health`、`/docs`；空VITE_API_BASE_URL走Vite代理。若直接连接跨域API，需要团队批准的ALLOWED_ORIGINS匹配前端地址；CORS不是身份认证。

## 档案依赖

成员A至少提供GET /api/profile与PUT /api/profile并创建合法profiles.id=1；未建档时饮食业务返回409 PROFILE_REQUIRED，config例外。当前A的router.py仍为空，尚未真正完成跨模块建档联调。不能在正式库插入假档案来绕过。

显示名必填，身高/体重可NULL，病史等默认空串即可；饮食模块不要求填写真实健康指标，也不据此推算目标。成员A更新档案必须保留主键并UPDATE，不要INSERT OR REPLACE触发级联删除。A的health_goals与B的diet_daily_goals不是同一张表。

当前没有账号认证，服务层固定profile_id=1；只适用已约定的本地单档案模型，不可当作已隔离的多用户服务。多用户改动清单见TEAM-INTEGRATION.md，本次不实施。

## 测试

以下为后续获授权的运行测试步骤，本轮仅做静态检查。先确认虚拟环境确实为Python 3.12且依赖完整，不能因缺少依赖改用错误解释器强行执行。backend目录：

```powershell
& ..\.venv\Scripts\python.exe -B -c 'import sys; assert sys.version_info[:2] == (3, 12), sys.version'
if ($LASTEXITCODE -ne 0) { throw '需要Python 3.12，停止' }
& ..\.venv\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw '依赖检查失败，停止' }
$env:DIET_APPLY_MIGRATIONS = '0'
# 为直接读取get_settings()的模块设置独立临时库，避免回退默认路径。
$testInfoJson = & ..\.venv\Scripts\python.exe -B -m app.modules.diet.dev_database --without-profile
if ($LASTEXITCODE -ne 0) { throw '测试隔离库准备失败，停止' }
$testInfo = $testInfoJson | ConvertFrom-Json -ErrorAction Stop
if ($testInfo.temporary -ne $true -or -not $testInfo.database_path) { throw '临时库信息无效，停止' }
$env:HEALTH_DB_PATH = $testInfo.database_path
& ..\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw '测试失败，保留结果并停止' }
```

各饮食测试和冒烟测试仍使用自身TemporaryDirectory及SQLite夹具；进程HEALTH_DB_PATH是额外隔离措施，生理期服务等直接读取get_settings()的代码不能只依靠create_app(Settings(...))隔离。上面的无档案进程隔离库不替代具体测试夹具。

`test_startup_never_migrates_and_explicit_migration_enables_library`先在独立临时库创建合法profiles.id=1，再验证环境变量为0和1时启动前后结构不变、食物库返回503及DIET_MIGRATION_REQUIRED；显式执行001后验证200，重启也不隐式执行002～004。迁移失败回滚、并发幂等性和历史数据保护测试继续保留。

frontend目录：

```powershell
node --test src/components/diet/waterReminder.test.js src/components/diet/report.test.js
npm run build -- --configLoader native
```

旧饮食开发环境的2026-10-15历史验收记录：后端180项全部通过（28.453秒），前端17项全部通过（12项提醒+5项报告），Vite构建通过（1.08秒）。该记录来自团队集成前，不能作为当前显式迁移策略调整后的通过证明；当前团队运行结果须在新Python 3.12环境中重新验证。历史测试使用独立临时SQLite数据库，未向正式库写入测试记录，并记录过TestClient/httpx弃用提示；不因此自动升级依赖。

旧开发环境还记录了独立临时库001～004逐步首次执行成功、重复执行无更改、快照相同、完整性ok、外键无异常及临时文件清理。本轮没有重新执行这些数据库操作；历史升级/失败回滚/无档案/缺迁移等覆盖见现有测试。

## 演示与数据审批

本机专用demo_server要求HEALTH_DIET_DEMO_DB指向带正确标识的系统临时目录demo.db，拒绝回退正式库。当前环境134种食品、12道候选菜谱、45条课堂饮食、18条饮水；所有记录仅作演示。数据来源技术核验不等于团队正式批准；未经试做不标已试做。

当前课堂演示与备份材料在工作区outputs/diet-final-delivery-20261015的私有目录，不能提交到团队Git。该备份是归档副本，不是可直接替换HEALTH_DIET_DEMO_DB的启动目录；原临时库保留运行。实际启动、重置和讲解步骤见课堂材料。其他成员迁移机器时，应审核备份和演示元数据后再建立自己的独立演示路径，不能复制覆盖正式库。

正式导入工具默认dry-run，完整命令用 `python -m app.modules.diet.import_data --help` 查询。temporary_review包不能伪装成approved；正式导入仍需合法档案、明确审批、manifest/plan哈希、备份及再次授权。导入来源标识保存在source_note中，不新增公共库表；当前食物库也归档案1所有。

## 常见问题与边界

- 409：未建档，先与A联调；测试只在临时库创建测试档案。
- 503迁移提示：核对实际DB路径及版本，使用显式迁移流程，不删库重建。
- 500/代理失败：先确认后端启动与端口，再查错误日志；前端可访问不代表后端已连接。
- 搜索为空：营养库不自动下载USDA，不自动装入数据包；检查档案、数据库及筛选。
- 推荐为空：查看禁忌硬过滤、成分未知/过期、分类和制作时间筛选；不能为扩大数量放宽过滤。
- 提醒不出现：只有/diet可见页面、有效槽位、已开启设置且未被目标暂停时触发；权限拒绝不妨碍页面提醒。
- 多页签：Web Locks可用时串行认领；无Web Locks不保证多页签同时提醒的互斥；清除localStorage会重置去重。
- PDF是图片型、文字不可选中；中文依赖导出设备字体渲染。本次已有课堂导出备用文件。原始导出不自动带页面演示横幅，课堂文件已额外标记非真实记录。
- 手机布局、实际烹饪、浏览器通知与成员A/C/D/E真实联调仍需人工验收。

正式health.db本轮未改，未执行正式导入、Git初始化、提交、推送或合并。此README和附录仅在饮食模块目录更新；公共文件保持原状。
