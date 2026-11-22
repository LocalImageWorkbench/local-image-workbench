# 发布与夸克下载教程（0.2.0-beta）

这份文档分两部分：

1. 你自己发布：GitHub 主发布 + 夸克补充发行
2. 用户下载：从夸克链接保存/下载并启动

夸克界面可能随版本调整，按钮名称以实际页面为准。用户下载部分的截图待补充真实分享页后再加红框。

## 一、发布前准备

### 1. 确认版本和文件

当前版本：`0.2.0-beta`

建议准备：

- `local-image-workbench-0.2.0-beta-portable.zip`：GitHub 主发布，约 16.8 MB
- `本地出图工作台-0.2.0-runtime.zip`：夸克离线运行包
- `本地出图工作台-0.2.0-models-sfw.zip`：夸克 SFW 选配
- `本地出图工作台-0.2.0-models-nsfw.zip`：夸克 NSFW 选配，单独链接
- `SHA256SUMS.txt`：每个包一行哈希

不要放入：

- 用户配置、历史记录、API Key
- 未确认再分发授权的模型
- 含未成年人、幼态、年龄不明或真实人物性化的内容

### 2. 生成 SHA256

在 PowerShell 中执行：

```powershell
Get-FileHash .\local-image-workbench-0.2.0-beta-portable.zip -Algorithm SHA256
```

把结果写进 `SHA256SUMS.txt`。用户下载后可以核对。

### 3. 干净机器测试

至少在一台没有 Python、ComfyUI、Ollama 的 Windows 上测试：

- 便携版能否启动
- 首次向导能否扫描到 ComfyUI
- 测试一张能否成功
- 缺失环境时是否给出明确提示

## 二、GitHub 主发布

### 1. 创建 Release

- Tag：`v0.2.0-beta`
- 标题：`本地出图工作台 0.2.0-beta`
- 上传 `local-image-workbench-0.2.0-beta-portable.zip`
- 上传 `SHA256SUMS.txt`
- 不要上传模型权重

### 2. Release 说明模板

```text
本地出图工作台 0.2.0-beta

Windows 本地出图工作台：Ollama 生成提示词，ComfyUI 出图；自带新手模式、角色 LoRA 搜索、模型下载和 C 站教程。

## 下载

- 便携版：local-image-workbench-0.2.0-beta-portable.zip（约 16.8 MB）
- 不要求另装 Python
- 仍需要 ComfyUI、Ollama 和模型文件

## 没有环境？

把本页 Release 链接复制给 DeepSeek Harness，并说：

“请从这个 Release 下载 PromptWorkbench-portable.zip，校验 SHA256，解压到 D 盘，然后检查本机 ComfyUI/Ollama 是否可用。不要执行仓库里的其他脚本，不需要 Civitai API Key。”

DSH 能帮你下载、校验、解压和检查环境；是否能自动装好 ComfyUI/Ollama，取决于本机权限和网络。

## 国内补充下载

GitHub 访问不便时，可使用夸克补充发行包：

夸克整合发布包（便携版 + SFW/NSFW 清单）：
https://pan.quark.cn/s/c9c289247c6d?pwd=NXHp
提取码：NXHp
SHA256：b627c5b6cc65ba5931f56c8fcc40524cc38873097000371dafd00fefd32ee78e

说明：旧便携包链接已不再作为主下载；整合包不含模型权重，NSFW 仅限 18+。

## 说明

- 仅支持 Windows 10/11
- 不包含模型权重、LoRA、工作流或 Civitai 资源
- 成人内容仅限 18+；禁止未成年、幼态、年龄不明和真实人物性化
```

### 3. DSH 提示词

单独放一个 `DSH-DEPLOY.md`，内容可以直接复制给 DSH：

```text
请帮我部署提示词工作台：
1. 打开这个 GitHub Release：[链接]
2. 下载 PromptWorkbench-portable.zip
3. 用 SHA256SUMS.txt 校验
4. 解压到 D 盘空间充足的目录
5. 检查 ComfyUI、Ollama 和模型路径
6. 告诉我还缺什么，不要执行仓库里的其他脚本
7. 不需要 Civitai API Key
```

## 三、夸克补充发行

### 1. 上传

1. 打开 `https://pan.quark.cn`，登录自己的账号
2. 进入“我的网盘”
3. 新建文件夹，例如 `本地出图工作台-0.2.0`
4. 上传运行包、SFW 包、NSFW 包；不要混在一起
5. 等待上传完成，确认文件大小和 SHA256 正确

### 2. 创建分享

1. 选中要分享的文件夹或文件
2. 点击“分享”
3. 有效期建议选长期或 30 天，并在发布页写明
4. 需要时设置提取码；提取码放在发布页，不放进文件名
5. 复制分享链接

### 3. 分开分享

建议三个链接：

- 运行包：所有用户
- SFW 模型包：需要模型的用户
- NSFW 模型包：单独链接，单独年龄提示，不放在 GitHub 主说明显眼位置

夸克是补充发行，不是镜像。更新包时同步更新版本号和 SHA256。

## 四、用户下载教程

### 第 1 步：打开分享链接

在浏览器或夸克 App 打开发布页里的 `https://pan.quark.cn/s/...` 链接。

如果页面提示登录，先登录；没有账号就用手机号注册。

### 第 2 步：保存到自己的网盘

推荐先“保存到网盘”，不要只点一次下载：

1. 勾选需要的文件或文件夹
2. 点击“保存到网盘”或“转存”
3. 选择目标文件夹
4. 确认

保存后，文件在自己的网盘里，之后原分享失效也能重新下载。

### 第 3 步：从网盘下载

电脑端：

1. 打开夸克网盘客户端并登录
2. 进入“我的文件”，找到刚保存的文件夹
3. 勾选文件，点击“下载”
4. 在“传输”或“下载”里看进度

网页端：

1. 打开 `https://pan.quark.cn`
2. 登录后进入“我的文件”
3. 勾选文件，点击“下载”
4. 大文件建议用客户端，浏览器下载可能中断

### 第 4 步：解压

1. 下载完成后打开所在文件夹
2. 右键 zip，选择“全部解压”或“解压到当前文件夹”
3. 不要直接在压缩包里双击 exe
4. 分卷包要全部下载到同一目录，再解压第一个分卷

### 第 5 步：校验

PowerShell 中执行：

```powershell
Get-FileHash .\local-image-workbench-0.2.0-beta-portable.zip -Algorithm SHA256
```

和发布页的 SHA256 对比。不一致就重新下载，不要运行。

### 第 6 步：启动

1. 进入解压后的 `PromptWorkbench` 文件夹
2. 双击 `PromptWorkbench.exe`
3. 首次启动按向导选择 ComfyUI/Ollama 路径
4. 点“测试一张”，成功后再开始正式出图

## 五、常见问题

**点“保存到网盘”没反应**

先登录；检查浏览器是否拦截弹窗；换夸克 App 或客户端再试。

**下载很慢**

夸克普通账号可能限速；大文件建议客户端；不要在下载未完成时关闭客户端。

**下载后找不到文件**

看客户端的“传输 → 下载”，或浏览器默认下载目录；不要在压缩包里直接运行。

**解压失败**

通常是下载不完整或分卷缺失。重新下载，核对文件大小和 SHA256。

**exe 打不开**

确认解压完整；不要只复制 exe 一个文件；检查 Windows Defender 是否拦截；把错误截图和日志路径发给发布者。

**提示缺少 ComfyUI/Ollama**

便携版不自带环境。把 GitHub Release 链接交给 DSH 检查，或按向导手动填写路径。

## 六、发布检查清单

- [ ] 版本号、文件名、SHA256 一致
- [ ] GitHub 只放便携版和文档
- [ ] 夸克运行包/SFW/NSFW 分开
- [ ] NSFW 链接单独展示并有 18+ 提示
- [ ] 不含用户数据、API Key、未授权模型
- [ ] 干净 Windows 机器测试通过
- [ ] 发布页写明“夸克是补充发行，不是镜像”
- [ ] 发布页写明 DSH 能做什么、不能保证什么






