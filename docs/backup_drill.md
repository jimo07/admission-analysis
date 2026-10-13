# S0-10 备份与恢复演练

## macOS 演练（2026-10-12，MySQL 9.5.0）

通过 `backend/.env` 连接本机 TCP 3306，在随机命名的临时源库创建 InnoDB 测试表和一条记录，使用 `mysqldump` 导出并恢复到临时目标库。恢复后 `COUNT(*)` 为 1，标记值一致。临时库和 dump 已清理，`sfb_dev`、`sfb_test`、`sfb_demo` 未被演练触碰。

MySQL 9.5 同机恢复时使用 `--set-gtid-purged=OFF`，避免 `GTID_PURGED` 与服务器已执行状态重叠。实际演练通过。

## Windows 演练（2026-10-12）

在 `sfb_test` 中创建 `drill_marker` 并插入 5 行。备份前计数为 5；执行备份后删除这 5 行，再恢复备份；恢复后计数为 5，判据通过。期间发现 PowerShell 5.1 对无 BOM 的 UTF-8 中文脚本可能按系统 ANSI 解码，主分支已将相关脚本转为 UTF-8 BOM。还新增 `mysql-root.ps1` 以显式 `root` 用户运行 MySQL 客户端。

## 跨平台脚本

macOS/Linux 使用 `backend/scripts/backup.sh`、`restore.sh`；Windows 使用 `backup.ps1`、`restore.ps1`。入口共同调用标准库实现的 `db_backup.py`。它从 `backend/.env` 读取 `DATABASE_URL`，通过临时 MySQL 客户端配置文件传递凭据，不把密码放在进程参数中。

备份示例：

```sh
backend/scripts/backup.sh --database sfb_test
```

Windows PowerShell：`backend/scripts/backup.ps1 -Database sfb_test`。备份默认目标为 `sfb_test`，也可显式指定其他 schema；备份文件位于 `backend/scripts/backups/`，使用 `.sql` 扩展名。

恢复示例：

```sh
backend/scripts/restore.sh backend/scripts/backups/<备份文件名>.sql --target-database sfb_test
```

Windows PowerShell：`backend/scripts/restore.ps1 -DumpFile <备份文件路径> -TargetDatabase sfb_test`。恢复要求显式指定目标 schema，并要求交互确认；请恢复到空的临时 schema，避免与已有表冲突。正式演示前先备份演示数据。
