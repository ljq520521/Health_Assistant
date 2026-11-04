# 小组集成、个人档案与Git交付

## 成员A必须提供的最小接口

当前`backend/app/modules/profile/router.py`只有APIRouter声明，没有GET/PUT处理函数，不能声称已完成真实建档联调。

| 接口 | 协议与协作点 |
| --- | --- |
| GET /api/profile | 返回当前唯一Profile；未建档按既有docs约定404；含id、display_name、可空height_cm/weight_kg、文本健康字段、审计时间 |
| PUT /api/profile | 创建或更新唯一id=1，返回200；display_name必填；身高/体重可NULL，medical_history/allergies/medications/preferences默认空串；不能迫使测试人员填写虚构健康指标 |
| /profile前端页 | 可正常建档、显示校验错误，并允许返回/diet；饮食页409提供此入口 |

饮食服务目前直接查询共享SQLite的profiles，不通过HTTP调用A的接口。A和B必须连接同一团队集成数据库；不能各自指向不同文件还期待建档后自动可用。

profiles的id有CHECK(id=1)。更新必须保持主键：请使用UPDATE或安全upsert更新列，不要INSERT OR REPLACE，因为SQLite的替换可能先删除父行，触发ON DELETE CASCADE并丢失饮食等子表数据。

A的health_goals是通用目标，B的diet_daily_goals是版本化营养与饮水目标。不能未经协议同步覆盖。profiles.allergies/preferences是文本，B的结构化food_preferences用于硬过滤；文本不能自动当成已核验术语映射。正式接入时需共同决定导入或提示方式，本轮不猜测映射。

成员A规划中的GET/POST /api/profile/goals及GET/PUT/DELETE /api/profile/goals/{id}属于A自己的通用目标接口，目前不是B六项功能运行的前置条件；不能因为A尚未实现这些接口而替B创建或清空diet_daily_goals。

## 单档案核查结论与未来多用户位置

结论：业务确实固定使用profile_id=1，不存在真实账号登录鉴权或用户数据隔离。不能只将前端加一个profile_id输入框就称为多用户支持。

| 位置 | 当前实现 | 后续需要的改动（本轮不实施） |
| --- | --- | --- |
| backend/sql/init.sql profiles | 主键CHECK(id=1) | 团队批准新的账号/档案迁移、保留历史档案；不能改已发布001～004校验和 |
| router.py、library_router.py及子路由依赖 | 只有database_path依赖，无当前用户 | 统一鉴权依赖解析current_profile_id，拒绝未授权访问；不要信任请求体归属ID |
| service.py require_profile/find/list/save/delete | WHERE profile_id=1、VALUES(1,...) | 每个读写、更新、删除显式绑定认证档案；资源不存在/他人资源采用一致策略 |
| library_service.py | 食品/分类固定档案 | 归属校验与分类关联隔离；明确公共库和个人库模型，不能用NULL绕过约束 |
| nutrition_service.py、water_service.py | 目标、统计、提醒配置固定档案 | 日期统计与目标版本全部按认证档案过滤 |
| recipe_service.py、recipe_preference_service.py、recipe_recommendation.py | 食谱、库存、术语、组成、规则固定档案 | 逐层校验关联资源；补必要复合外键/租户索引及交叉用户拒绝测试 |
| report_service.py | 三张来源表WHERE profile_id=1 | 同一读取事务内绑定同一个认证档案，防止报表泄露 |
| import_service.py、开发演示工具 | 固定档案1、marker身份与去重在当前数据集 | 正式导入目标必须来源于获授权的档案，来源去重也按归属；测试工具保持隔离 |
| waterReminder.js / WaterReminderHost.vue | 固定localStorage键health-diet-water-reminder-v1、锁名diet-water-reminder | 按账号/档案命名、登出清理监听及身份状态，避免账户间串用已提醒槽位 |
| 前端6个API封装和公共CORS | 当前无账号凭据协议 | 团队统一token/cookie、CSRF/CORS策略及错误处理；不要每模块各做登录 |
| 测试 | 基于单档案模型 | 增加A/B两档案读写隔离、跨租户关联攻击、导入/报告/缓存隔离及旧库升级测试 |

精确文件和命中行见SINGLE-PROFILE-LOCATIONS.json。该清单包含测试/演示工具中的合理固定值，应区分业务改造与测试样本，不做机械全局替换。

## 现有公共集成点：手工核对而不是覆盖

本机历史上为饮食集成保留的公共点：main.py保存settings并调用饮食初始化检查；requirements.txt的tzdata；test_smoke.py未建档饮食返回409；.gitignore的SQLite/缓存规则；共享docs中第一批饮食说明。它们需要与团队当前版本逐块比对，不能凭没有Git历史的工作目录断言整文件均由B新增。

其他四人的业务目录、页面、公共导航和数据库配置不是本次可覆盖的交付范围。本轮只更新本模块README及docs附录，没有改这些共享文件。

## 当前Git状态与安全接入方案

项目根目录及外层Health_Assistant-main均无.git；工作区与Documents/Codex也未发现.git。未执行git init、commit、push、merge。没有团队仓库地址和基线，因此无法出具真实git diff或“已跟踪敏感文件”的检查结果。

后续由你获得正式仓库地址后，在一个新的独立目录克隆，不能克隆覆盖当前项目：

```powershell
# 以下是未来人工执行模板，先替换地址和确认分支名；本轮未执行。
git clone <团队仓库地址> <新的空目录>
Set-Location <新的空目录>
git switch -c codex/diet-integration
```

1. 确认团队最新基线、README/AGENTS及分支流程。先看当前status，不能覆盖未提交改动。
2. 参照FILE-MANIFEST逐文件对比，优先合并diet目录、饮食组件/6个API、DietView和饮食测试；团队已有同名代码时先diff再人工合并。
3. 公共main.py、requirements、test_smoke、路由和公共文档仅合并经团队批准的最小差异；不要复制整套项目和node_modules/.venv。
4. 不搬入backend/data、demo.db、任何SQLite备份、.env、课堂PDF/PNG、classroom-state.json、导入审计及个人健康数据；待审批数据不是团队已正式批准素材。
5. 在克隆仓库确认忽略规则后，使用明确路径暂存，避免git add .。不自动推送或发起合并。

提交前人工核验命令：

```powershell
git status --short --untracked-files=all
git check-ignore -v --no-index backend/data/health.db backend/data/demo.db demo.db .venv/pyvenv.cfg frontend/node_modules/example.js
git ls-files -- '*.db' '*.db-*' '*.sqlite' '*.sqlite-*' '*.sqlite3' '*.sqlite3-*' '.env'
git diff --cached --name-status
git diff --cached --check
```

`.gitignore`不保护已跟踪文件，也挡不住git add -f。若git ls-files发现数据文件，应停止提交，先与负责人确认从索引移除及敏感历史处理；不要擅自改写仓库历史。PDF/PNG/JSON也可能含健康信息，不能只检查.db扩展名。

当前项目.gitignore已覆盖backend/data/*（保留.gitkeep）、*.db及日志、*.sqlite*、.env、.venv、node_modules、.pnpm-store、dist和Python缓存。本轮备份与课堂材料放在项目之外的独立交付目录，那里新增局部.gitignore排除private-demo/classroom-materials/private-audit；没有改公共.gitignore。

## 五人联调清单

- [ ] 全组在独立集成测试库执行init→001→002→003→004；校验和一致，重复迁移无改动，禁止各自重建共享表。
- [ ] A：未建档时GET profile为404，B业务为409；创建id=1后B接口可用；修改档案不删除已有饮食/食物/目标/饮水/食谱数据。
- [ ] A：决定档案删除、备份与级联语义；核对文本过敏信息与B结构化禁忌的边界；确认通用目标与营养目标互不覆盖。
- [ ] C运动：共享同一档案；饮食操作前后exercise_records一致；不得把运动消耗自动抵扣饮食目标，除非另有协议。
- [ ] D睡眠：UTC时间存储、业务时区日期含义明确；饮水筛选与睡眠跨午夜展示互不干扰；B操作不改sleep_records。
- [ ] E生理期：资料只在本模块展示；B报告不读写cycle_records，不将经期数据混入饮食建议。
- [ ] 公共后端：main保留五路由、settings注入、CORS；/health通过；不得因某模块默认路径指向另一文件而产生“已建档仍409”。
- [ ] 公共前端：/diet与其他4页导航正常；离开/diet后提醒停止；样式隔离，无全局CSS覆盖其他成员页面。
- [ ] 在同一临时库执行五模块顺序写入及刷新测试，捕获锁等待和错误响应；保留测试前后各表计数/关键记录对比。
- [ ] 回归B全部180项后端测试及17项前端逻辑测试，再执行全组新增测试与生产构建；本轮没有声称其他成员未实现功能已通过。
- [ ] 多浏览器/移动端人工复核、通知权限拒绝、PDF中文和导出，明确预览服务与生产部署的区别。
- [ ] 提交前核对显式暂存名单，不含任何正式/演示数据库、个人资料、审批材料或依赖缓存。

目前能交付单档案饮食模块供集成测试；真实建档流程、其他成员业务联调、正式数据审批和多用户体系仍待团队处理。
