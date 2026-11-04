# 用户与基础模块：账号、档案与目标

本文件记录成员 A 在 v0.2 中实现的“用户与基础”模块。它不替换 `docs/04-database.md`、`docs/05-api.md` 的既有约定，只补充本轮新增的本地账号能力。

## 1. 模块范围

| 职责 | 实现 |
| --- | --- |
| 用户注册与账号体系 | `POST /api/auth/register`；首个账号自动成为管理员，之后只能由管理员创建只读账号 |
| 密码安全存储 | PBKDF2-HMAC-SHA256，210000 次迭代，16 字节随机盐，格式 `pbkdf2_sha256$迭代次数$盐$摘要` |
| 账号状态管理 | `active` / `disabled`；管理员可在“账户与隐私”中停用或启用其他账号 |
| 登录与会话 | `POST /api/auth/login` 签发 HS256 JWT，有效期 8 小时；`GET /api/auth/me` 校验会话 |
| 多角色权限 | `admin`（管理员）与 `viewer`（只读）；写档案、写目标、管理账号仅管理员可用 |
| 个人健康档案 | 昵称、身高体重、既往病史、过敏史、用药记录、生活偏好；单档案 `profiles.id=1` |
| 健康目标 | 增删改查、手动累计当前值、进度 = `min(当前值/目标值, 1) × 100`，保留 1 位小数 |
| 账号安全与隐私 | 修改密码（旧令牌立即失效）、数据授权开关、敏感字段隐藏、匿名统计偏好 |

## 2. 权限矩阵

| 操作 | 未登录 | viewer | admin |
| --- | --- | --- | --- |
| 查看档案 / 目标 | 401 | 200（可隐藏敏感字段） | 200（完整） |
| 建立或修改档案 | 401 | 403 | 200 |
| 增删改目标 | 401 | 403 | 200 |
| 查看账号列表 | 401 | 403 | 200 |
| 停用 / 启用账号 | 401 | 403 | 200（不能停用自己） |
| 修改本人密码 / 隐私 | 401 | 200 | 200 |

## 3. 认证实现

- **无新增依赖**：密码哈希、Base64URL、HMAC-SHA256 与 JWT 编解码全部使用 Python 标准库，`requirements.txt` 不变，其他模块拉取代码后无需重新安装依赖即可启动。
- **签名密钥**：首次使用时生成并写入 `auth_secrets` 表，重启后令牌仍然有效；不依赖 `.env`。
- **令牌失效**：`users.token_version` 参与签名载荷。修改密码、停用或启用账号时自增，旧令牌立即失效。服务端每次请求还会重新读取账号状态，停用即时生效。
- **令牌存储**：前端保存在 `localStorage` 的 `health_profile_token`，请求头为 `Authorization: Bearer <token>`。
- **生产提示**：标准库实现适合本地课程项目；正式部署应改用 Argon2/bcrypt 与 PyJWT，并把密钥放入环境变量或密钥管理服务。

## 4. 接口

所有路径都在 `/api` 下，响应为 JSON；错误统一为 `{"detail": "说明"}`。

| 方法 | 路径 | 说明 | 成功状态 |
| --- | --- | --- | --- |
| GET | `/api/auth/setup` | 是否已有账号（决定显示“创建管理员”还是“登录”） | 200 |
| POST | `/api/auth/register` | 注册；首个账号为 admin，之后需管理员令牌 | 201 |
| POST | `/api/auth/login` | 登录，返回令牌与账号信息 | 200 |
| GET | `/api/auth/me` | 当前账号 | 200 |
| PUT | `/api/auth/password` | 修改密码，返回新令牌 | 200 |
| PUT | `/api/auth/privacy` | 保存三个隐私开关 | 200 |
| GET | `/api/auth/users` | 账号列表（仅管理员） | 200 |
| PUT | `/api/auth/users/{id}/status` | 停用 / 启用（仅管理员） | 200 |
| GET | `/api/profile` | 读取档案；未建档 404 | 200 |
| PUT | `/api/profile` | 建立或整体替换档案 | 200 |
| GET | `/api/profile/goals` | 目标列表 `{items: []}` | 200 |
| POST | `/api/profile/goals` | 新建目标 | 201 |
| GET | `/api/profile/goals/{id}` | 单个目标 | 200 |
| PUT | `/api/profile/goals/{id}` | 整体替换目标 | 200 |
| DELETE | `/api/profile/goals/{id}` | 删除目标 | 204 |

未建档时访问目标接口返回 409；未授权健康数据处理时档案与目标接口返回 403。

## 5. 数据表

两张新增表已追加到 `backend/sql/init.sql`，使用 `CREATE TABLE IF NOT EXISTS`，启动时自动补齐，**不修改既有六张表**，已有数据不受影响。

- `users`：`id`、`username`（唯一、小写）、`password_hash`、`role`、`status`、`consent_health_data`、`mask_sensitive`、`analytics_consent`、`token_version`、`last_login_at`、`created_at`、`updated_at`。
- `auth_secrets`：单行签名密钥。

档案与目标的字段、校验与索引沿用 `docs/04-database.md`。

## 6. 隐私开关语义

- **授权处理健康数据**：关闭后，当前账号访问 `/api/profile*` 一律 403；该接口本身在 `/api/auth/privacy`，所以可以随时重新开启，不会把自己锁死。
- **隐藏敏感字段**：只对 viewer 生效。viewer 读取档案时，既往病史、过敏史、用药记录返回空串并带 `sensitive_masked: true`；管理员始终读取完整值，避免“隐藏后再保存”把真实病史覆盖为空。
- **匿名使用统计**：仅保存偏好，当前版本没有任何上传或统计逻辑。

## 7. 前端

| 文件 | 作用 |
| --- | --- |
| `src/api/profile.js` | 令牌读写、统一错误处理、全部档案/目标/账号请求 |
| `src/components/profile/AuthPanel.vue` | 首次创建管理员或登录 |
| `src/components/profile/ProfileForm.vue` | 档案表单；只读账号自动禁用 |
| `src/components/profile/GoalsPanel.vue` | 目标列表、进度条、新增/编辑/删除弹窗 |
| `src/components/profile/AccountPanel.vue` | 账号信息、修改密码、隐私开关、账号管理、退出 |
| `src/views/ProfileView.vue` | 页面编排、登录态检查、三个页签 |

沿用现有视觉：`module-overview`、`page-heading`、`button`、原生 `<dialog>` 与各组件 scoped CSS；未改动 `styles.css`。

## 8. 接入点

1. 后端**不需要**在 `app/main.py` 注册新路由：该文件已经 `include_router(profile_router, prefix="/api")`，而模块内的聚合路由同时挂载了 `/auth` 与 `/profile`。
2. 唯一改动的公共文件是 `app/main.py` 的 CORS `allow_headers`：加入 `Authorization`，否则浏览器预检会拦截带令牌的请求。
3. 数据库无需迁移脚本：新增表是幂等的 `CREATE TABLE IF NOT EXISTS`，后端启动时自动执行；已有 `health.db` 会在下次启动后出现 `users` 表。
4. 前端路由 `/profile` 已存在，无需改动 `router/index.js`；其他模块页面无需改动。

## 9. 验证

```powershell
# 项目根目录已按 README 建好 .venv 并安装依赖后
cd backend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

新增测试 `backend/tests/test_profile.py`（16 项）覆盖：首个账号成为管理员、重复注册与弱密码、登录失败、伪造或畸形令牌、档案权限与校验、目标增删改查与进度、未建档 409、数据授权 403、敏感字段隐藏、修改密码使旧令牌失效、账号停用与启用、管理员不能停用自己。后端完整套件（196 项）通过。

## 10. 已知边界

- 仍是**单档案**应用：所有账号共享 `profiles.id=1`，账号是访问控制层，不做多用户数据隔离。若后续要多用户，需要把 `profiles` 改为按账号归属，并同步调整其他四个模块。
- 没有“退出登录”服务端接口：JWT 无状态，前端删除本地令牌即可；如需服务端吊销，可复用 `token_version` 强制下线。
- 令牌放在 `localStorage`，存在 XSS 风险；本地单机工具可接受，公网部署应改用 HttpOnly Cookie。
- 未实现找回密码、邮箱验证、登录限流；本地离线场景暂不需要。
