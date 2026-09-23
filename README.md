# 个人健康管理系统 · v0.1.0

一个面向个人的健康记录工具，集中管理健康档案、饮食、运动、睡眠与生理期信息。

**当前交付：初始可运行骨架。** 已有前后端启动入口、首页、五个模块占位页、真实健康检查、模块目录接口、六张空表与配套文档。业务录入、统计、注册登录等尚未实现。原始需求依据为《软工需求分析.doc》，其扩展功能归入后续规划。

## 技术栈定版

后端 **Python 3.12 + FastAPI + SQLite**，前端 **Vue 3 + Vite 7 + Vue Router 4**，使用 **JavaScript、原生 CSS**；v0.1 **仅本地运行**。

Python 依赖固定在 `backend/requirements.txt`，前端依赖固定在 `frontend/package.json` 和 `frontend/package-lock.json`。前端使用 Node.js 22.12+（建议 22 LTS 或 24 LTS）与 npm。

## 文档入口

| 文档 | 内容 |
| --- | --- |
| [01 极简需求](docs/01-requirements.md) | 项目目标、5 条核心功能、边界、关键规则 |
| [02 技术栈](docs/02-tech-stack.md) | 技术定版、环境变量、运行约定 |
| [03 页面与交互](docs/03-pages.md) | 页面、按钮、弹窗、跳转关系 |
| [04 数据库设计](docs/04-database.md) | 六张表的字段、类型、主键与索引 |
| [05 接口清单](docs/05-api.md) | 已实现接口与待开发接口的入参、出参 |
| [06 五人分工](docs/06-team.md) | 一人一模块、文件归属、协作方式、验收项 |
| [07 后续规划](docs/07-roadmap.md) | 原文 30 项需求与可选扩展的阶段安排 |

## 功能规划（极简需求）

- **目标：** 一个个人健康记录工具，支持五类健康信息的录入、查看与维护。
- **核心功能：** ①健康档案与目标；②饮食记录与每日热量汇总；③运动记录与每日时长汇总；④睡眠记录与时长计算；⑤经期、症状与情绪记录。
- **不做：** 首轮不做注册登录、多角色权限、多人数据、AI 推荐、拍照/扫码识别、穿戴设备接入、主动推送、经期/排卵预测、医疗诊断、报告导出。
- **关键规则：** ①仅维护一个本地档案，业务记录均归属该档案，先建档再录入；②记录必须通过日期与数值校验，例如醒来晚于入睡、经期结束不早于开始、运动时长大于 0。

上述业务功能计划在 v0.2 开发，v0.1 只完成基础设施与文档。

## 五人分工

| 负责人（替换为真实姓名） | 模块 | 前端入口 | 后端目录 |
| --- | --- | --- | --- |
| 成员 A | 用户与基础 | `ProfileView.vue` | `app/modules/profile/` |
| 成员 B | 饮食营养 | `DietView.vue` | `app/modules/diet/` |
| 成员 C | 运动健身 | `ExerciseView.vue` | `app/modules/exercise/` |
| 成员 D | 睡眠监测 | `SleepView.vue` | `app/modules/sleep/` |
| 成员 E | 生理期管理 | `CycleView.vue` | `app/modules/cycle/` |

每人负责本模块的前端、后端、数据校验和联调。成员 A 兼任公共骨架维护人，其他人通过 PR 协调公共文件修改。

## 本地启动

### 1. 获取项目并配置环境

已有本地项目可直接进入目录，跳过克隆。

```bash
git clone https://github.com/ljq520521/Health_Assistant.git health-management
cd health-management
cp .env.example .env
```

Windows PowerShell 将复制命令换为 `Copy-Item .env.example .env`。示例值可直接用于本地开发；`.env` 不进入 Git。配置文件只放仓库根目录。

### 2. 启动后端（终端一）

macOS / Linux，在项目根目录执行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
cd backend
python scripts/init_db.py
python run.py
```

Windows PowerShell，在项目根目录执行（可不激活虚拟环境）：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe scripts\init_db.py
..\.venv\Scripts\python.exe run.py
```

建表脚本可重复运行；后端启动时也会自动建表。不会插入个人档案或示例健康数据，不会清空已有记录。

- 健康检查：<http://127.0.0.1:8000/health>
- Swagger 接口文档：<http://127.0.0.1:8000/docs>
- 模块目录：<http://127.0.0.1:8000/api/modules>

健康检查正常返回：

```json
{"status":"ok","database":"ok","version":"0.1.0"}
```

数据库默认位于 `backend/data/health.db`，已排除 Git 跟踪。数据库不可用时健康检查返回 HTTP 503。

### 3. 启动前端（终端二）

在项目根目录另开终端：

```bash
cd frontend
npm ci
npm run dev
```

访问 **<http://127.0.0.1:5173>**。首页应显示“服务连接正常”，五个模块入口均可跳转。后端未启动时会提示连接失败，并提供“重新检查”按钮。

本地开发由 Vite 将 `/health`、`/api` 请求转发到后端，无需手动修改前端 API 地址。若修改端口，请同步查看 [环境变量约定](docs/02-tech-stack.md)。

### 4. 验证与构建

在已激活 Python 虚拟环境的终端、`backend/` 目录执行：

```bash
python -m unittest discover -s tests -v
```

Windows 未激活环境时改用 `..\.venv\Scripts\python.exe -m unittest discover -s tests -v`。

在 `frontend/` 目录执行：

```bash
npm run build
```

构建结果为 `frontend/dist/`。`npm run preview` 仅预览构建产物，不代表部署完成，也不带开发服务器的 API 代理；要联调请使用 `npm run dev`。GitHub Actions 已配置后端冒烟检查和前端构建。

## 目录结构

```text
health-management/
├── README.md
├── .env.example               # 唯一配置示例
├── .gitignore
├── .editorconfig
├── .github/workflows/ci.yml
├── docs/                      # 需求、技术、页面、数据库、接口、分工、规划
├── backend/
│   ├── requirements.txt       # 固定 Python 依赖版本，含冒烟检查所需 httpx
│   ├── run.py                 # 本地启动入口
│   ├── app/
│   │   ├── main.py            # 应用、健康检查、路由注册
│   │   ├── config.py
│   │   ├── database.py
│   │   └── modules/           # profile / diet / exercise / sleep / cycle
│   ├── sql/init.sql           # 六张核心表与索引
│   ├── scripts/init_db.py
│   ├── tests/test_smoke.py
│   └── data/.gitkeep
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js
    ├── index.html
    ├── public/favicon.svg
    └── src/
        ├── main.js
        ├── App.vue
        ├── styles.css
        ├── api/client.js
        ├── router/index.js
        ├── data/modules.js
        ├── components/
        └── views/             # 总览、五个模块、404
```

## v0.1 提交验收

- [x] README、极简需求、技术栈、页面、数据库、接口与分工文档齐全。
- [x] `.gitignore` 排除依赖、虚拟环境、配置、健康数据、日志与临时文件。
- [x] `.env.example` 仅包含本地示例配置，没有账号、密钥或真实健康信息。
- [x] 后端可启动，健康检查和模块目录接口可用。
- [x] 前端可启动，首页与五个模块占位页可访问。
- [x] 建表脚本可重复执行，并保留已有数据。
- [x] 后端冒烟检查和前端生产构建通过。

## 第一次提交到 GitHub

项目仓库：[ljq520521/Health_Assistant](https://github.com/ljq520521/Health_Assistant)。需要从新的本地目录首次上传时，在项目根目录检查实际改动后执行：

```bash
git status
git add .
git commit -m "chore: initialize health management v0.1.0"
git branch -M main
git remote add origin https://github.com/ljq520521/Health_Assistant.git
git push -u origin main
```

若已有 `origin`，跳过 `git remote add`。从此仓库克隆后继续开发，只需提交改动并推送相应分支。

## 常见问题

- **`python3.12` 不存在：** 安装 Python 3.12；不要直接使用 macOS 系统自带的 Python 3.9。
- **Vite 报 Node 版本不满足：** 切换到 Node.js 22.12+；使用 nvm 时可在 `frontend/` 执行 `nvm install && nvm use`。
- **首页未连接后端：** 检查后端终端是否报错、8000 端口是否可访问，修改 `.env` 后重启前后端。
- **8000 端口已占用：** 修改根目录 `.env` 的 `BACKEND_PORT`（如 8001）并重启两端；Vite 默认代理会跟随该端口，后端文档地址也需使用新端口。
- **5173 端口已占用：** 先停止占用服务，或修改 `FRONTEND_PORT` 并同步 `ALLOWED_ORIGINS`；前端不会静默改用另一个端口。
- **修改 SQL 后旧库没有新字段：** `CREATE TABLE IF NOT EXISTS` 只负责初始化，不做结构迁移。后续表结构变更需新增迁移脚本，不直接删除已有数据库。
