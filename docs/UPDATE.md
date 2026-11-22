# 更新与发布流程

## 客户端怎么检查更新

侧栏“检查更新”会读取：

- 配置项 `update_manifest_url`
- 默认值：`https://raw.githubusercontent.com/LocalImageWorkbench/local-image-workbench/main/update.json`

清单格式：

```json
{
  "version": "0.2.1-beta",
  "url": "https://github.com/LocalImageWorkbench/local-image-workbench/releases/tag/v0.2.1-beta",
  "notes": "修复内容",
  "assets": {
    "portable_zip": "PromptWorkbench-0.2.1-portable.zip",
    "sha256": "..."
  }
}
```

客户端只做三件事：

1. 比较版本号
2. 显示更新说明
3. 打开 GitHub Release

不会自动下载、自动替换 exe，也不会执行远程脚本。

## 以后发新版

1. 修改 `VERSION` 和 `CHANGELOG.md`
2. 重新构建便携版
3. 生成 zip 和 SHA256
4. 在 GitHub 创建新 tag 和 Release
5. 上传 zip、`SHA256SUMS.txt`
6. 修改仓库根目录的 `update.json`
7. 提交并推送 `update.json`

用户下次点“检查更新”即可看到新版本。

## 为什么用静态清单

- 不需要自建服务器
- GitHub 公开仓库可以直接放 `update.json`
- 清单可以随时改，客户端不用重新发版
- 出问题可以回退清单内容

以后如果要接入自己的 API，只改 `update_manifest_url`，客户端不用改代码。

## 便携版怎么升级

1. 下载新 zip
2. 关闭旧程序
3. 解压到新目录，或覆盖旧目录
4. 配置、历史、设置保存在 `%APPDATA%\PromptWorkbench`，不会丢

不要删除 `%APPDATA%\PromptWorkbench`，否则历史、设置和迁移数据会丢失。

## 更新失败时

如果检查更新失败、下载后打不开，或新版本环境不适配：

1. 在“更新失败”弹窗选择“生成 DSH 环境修复提示词”
2. 或到“环境设置 → 更新修复提示词”
3. 复制给 DSH

提示词会带上：

- 当前版本、目标版本、错误信息
- Windows、Python、ComfyUI、Ollama、模型路径
- 清单中的 `requires` 环境要求
- 不删模型/历史、不自动升级 Python/CUDA/ComfyUI 的限制

不包含 API Key。

## 安全要求

- `update_manifest_url` 必须是 HTTPS
- Release 必须附 SHA256
- 不自动执行下载文件
- 不在清单里放 token、API Key 或用户数据
- 发现清单被篡改时，先停用更新检查并发公告

## 夸克包怎么更新

运行包和模型包分开更新：

- 应用更新：替换运行包，保留模型包
- 模型更新：只替换对应模型包
- NSFW 包单独维护，不混进主运行包
- 更新发布页的版本号和 SHA256


