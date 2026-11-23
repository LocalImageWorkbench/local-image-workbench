# 版本与便携版发布规则

## 两条线

- 源码线：`D:\prompt-workbench-release\app.pyw`，桌面“源码调试”快捷方式
- 便携线：`dist6\PromptWorkbench\PromptWorkbench.exe`，桌面“便携运行”快捷方式

源码修改不会自动进入便携版；便携版是某个时间点的冻结构建。

## 普通小更新

- 只改源码、文档、配置默认值
- 不重建便携版，不覆盖 GitHub/夸克便携包
- 便携版保留为稳定回滚点
- 回滚基线：`rollback\local-image-workbench-0.2.0-beta-portable-rollback.zip`

## 大版本更新

满足以下任一条件才重建便携版：

- 新功能成组上线
- 依赖/打包方式变化
- 需要用户更新客户端
- 版本号升级（如 0.2.0 → 0.3.0）

大版本流程：

1. 更新 VERSION 和 update.json
2. 重建便携包
3. 更新 Release 资产和 SHA
4. 更新 Quark 整合包
5. 保留上一版便携包作为回滚点

## 当前基线

- 0.2.0-beta 便携包：`rollback\local-image-workbench-0.2.0-beta-portable-rollback.zip`
- 当前源码可能比便携包新，这是预期行为。
