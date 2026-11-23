# 版本归档与 GitHub 上传规则

## 目录

- 版本库：`D:\prompt-workbench-release\versions\<版本号>\`
- 每个版本目录包含：便携 zip、`SHA256SUMS.txt`、该版本的启动快捷方式
- 旧桌面快捷方式备份：`versions\desktop-shortcuts\`
- 桌面只保留：
  - `本地出图工作台 - 最新版.lnk`
  - `本地出图工作台 - 次新版.lnk`

## 每次改版本号

1. 修改 `VERSION` 和 `app.pyw` 的 `APP_VERSION`
2. 更新 `CHANGELOG.md`、`README.md`、`使用说明.md`
3. 跑 `python -m unittest discover -s tests`
4. 用 PyInstaller 构建便携版
5. 运行 `tools\archive_version.ps1` 归档
6. 提交源码和文档到 GitHub
7. 创建对应 `v<版本号>` tag / GitHub Release，上传 zip 和 SHA256SUMS
8. 更新 `update.json` 到新版本（正式发布时）

## 归档示例

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\archive_version.ps1 `
  -Version "0.5.2-beta" `
  -Zip ".\dist-v52\local-image-workbench-0.5.2-beta-portable.zip" `
  -Exe ".\dist-v52\PromptWorkbench\PromptWorkbench.exe" -Latest
```

## GitHub 上传

源码/文档可以提交到 `main`；便携包用 Release 附件，不直接塞进 git。

```powershell
gh release create v0.5.2-beta `
  ".\dist-v52\local-image-workbench-0.5.2-beta-portable.zip" `
  ".\dist-v52\SHA256SUMS.txt" `
  --repo LocalImageWorkbench/local-image-workbench `
  --title "本地出图工作台 0.5.2-beta" `
  --notes-file ".\docs\RELEASE-NOTES-0.5.2-beta.md"
```

发布前确认：包能启动、版本号正确、SHA256 已记录、用户已明确同意。
