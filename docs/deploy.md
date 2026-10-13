# 思辨工坊部署说明

> 当前用于本地开发和技术演示；不是生产部署手册。项目持续开发中，执行前请使用对应分支的最新代码。

## 环境要求

| 组件 | 要求 | 说明 |
|---|---|---|
| 操作系统 | macOS 15+ 或 Windows 10/11 | 两端开发流程均有说明；数据库备份恢复共用 Python helper。 |
| Python | 3.11+ | 创建虚拟环境并安装 `backend/requirements.txt`。 |
| MySQL | 8+ | 本机开发/演示使用 `sfb_dev`、`sfb_test`、`sfb_demo` 三个 schema。 |
| Node.js / pnpm | 项目锁定版本 | 用于前端开发和构建。 |
| 模型网关 | OpenAI-compatible API | 配置地址、模型名和密钥见本机 `backend/.env`。 |

## 配置

复制 `backend/.env.example` 为 `backend/.env`，按模板填写 `DATABASE_URL`、`MODEL_BASE_URL`、`MODEL_API_KEY`、`MODEL_DEFAULT` 和 `JWT_SECRET`。数据库密码中的特殊字符需按 URL 规则 percent-encode。`.env` 含本机凭据，不能提交到 Git 或粘贴到聊天中。

## MySQL 初始化

确认本机 MySQL 已启动，并使用有建库权限的账号执行 `backend/scripts/create_schemas.sql`。该脚本幂等创建 `sfb_dev`、`sfb_test`、`sfb_demo`，使用 `utf8mb4_0900_ai_ci`，并输出 schema 字符集和排序规则供核对。项目连接串应指向 `sfb_dev`。

Windows 可通过 `backend/scripts/mysql-root.ps1` 调用本机 MySQL 客户端；macOS 可使用安装目录中的 `mysql` 客户端或数据库 GUI 执行 SQL。

应用数据库结构需要在 `backend` 目录执行 Alembic 迁移：

```sh
python -m alembic upgrade head
```

## 启动后端

macOS：

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Windows PowerShell：

```powershell
Set-Location backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

健康检查地址：`http://127.0.0.1:8000/api/health`，预期返回 `{"status":"ok"}`。

## 启动前端

在另一个终端窗口运行：

```sh
cd frontend
pnpm install
pnpm dev
```

使用 Vite 输出的本地地址访问。生产构建命令为 `pnpm build`。

## 演示前备份与恢复

演示数据使用 `sfb_demo`，不要用 `sfb_dev` 做破坏性恢复演练。macOS/Linux 备份示例：

```sh
backend/scripts/backup.sh --database sfb_demo
```

恢复到已确认可覆盖的目标 schema：

```sh
backend/scripts/restore.sh backend/scripts/backups/<备份文件名>.sql --target-database sfb_demo
```

Windows PowerShell 对应命令为 `backend/scripts/backup.ps1 -Database sfb_demo` 和 `backend/scripts/restore.ps1 -DumpFile <备份文件路径> -TargetDatabase sfb_demo`。恢复脚本要求显式指定目标库并交互确认；恢复前必须确认目标库内容可覆盖。完整演练记录见 `docs/backup_drill.md`。

## 开发注意

- MySQL 类型同义词在 ORM 与反射结果中可能不同：`NUMERIC`/`DECIMAL`、`BOOL`/`BOOLEAN`/`TINYINT(1)`、`INT`/`INTEGER`。结构一致性比较前需要归一化；实现见 `backend/tests/models/_type_utils.py` 的 `canon_type()`。
- ORM 与数据库反射对比时要考虑 InnoDB 自动为外键创建的索引。
- 每次新增迁移后，同步更新 `backend/tests/models/test_migration_consistency.py` 中的预期 revision 和业务表数量，再运行迁移一致性测试。
- 默认 `pytest -q` 的 CRUD 冒烟使用内存 SQLite。`backend/tests/models/` 下的 MySQL 集成测试会先清空 `sfb_test` 再迁移建表；只有确认 `sfb_test` 是可丢弃的专用测试库后，才设置 `SFB_ALLOW_DESTRUCTIVE_TEST_SCHEMA=1` 运行，切勿指向 `sfb_dev` 或含需保留数据的库。
- SQLAlchemy 2.x 的 `make_url` 不应先渲染为字符串再重新解析后传入 `create_engine`；密码转义可能因此被错误处理。按项目现有 `backend/app/core/config.py` 将 URL 对象直接传给 engine。
- `.ps1` 文件包含中文时应保存为 UTF-8 BOM，以兼容 Windows PowerShell 5.1 的脚本解码。
- `backend/scripts/backups/`、虚拟环境、`.env` 等本地文件已加入 `.gitignore`。
