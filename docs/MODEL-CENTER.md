# 模型中心与下载网络

## 直连能不能下载

可以先直接试。2026-11-22 在本机实测：

- Civitai API：HTTP 200
- Hugging Face API：HTTP 200

所以“没有 VPN 就一定下载不了”不成立。实际文件 CDN 可能比 API 更容易受到地区、运营商和时段影响，可能慢或失败。

## 推荐顺序

1. 直连 Civitai CDN / Hugging Face
2. Hugging Face 镜像 `hf-mirror.com`
3. GitHub 镜像
4. 直连失败时，才测试 Ikuuu 等网络工具

Ikuuu 是 VPN/梯子类网络工具，只作为可选测试写进说明；也可以自行使用同类产品。它不是模型来源，不随软件分发或配置。

## 模型中心

左侧“☁ 模型中心”支持：

- 搜索 Civitai 的 LoRA / Checkpoint
- 按底模过滤
- 查看版本、文件、大小、作者、训练词
- 显示下载大小并二次确认
- 下载后计算 SHA256；API 提供哈希时进行比对
- LoRA 下载后自动刷新本地 LoRA 列表
- 底模下载到 `checkpoint_dir`，没有配置时按 LoRA 根目录推导 `models/checkpoints`

不会做的事：

- 不自动静默下载
- 不自动购买 Civitai Buzz
- 不绕过登录、付费或授权
- 不自动安装缺失的 ComfyUI 节点

## 配置

```json
{
  "lora_roots": ["D:\\ComfyUI\\models\\loras"],
  "checkpoint_dir": "D:\\ComfyUI\\models\\checkpoints",
  "civitai_api_key": ""
}
```

Civitai API Key 可选，某些 NSFW/受限资源可能需要。Key 只保存在 `%APPDATA%\PromptWorkbench\config.json`，不要提交仓库。

## 大小与流量

下载前会显示文件大小。超过 1GB 的模型和 LoRA 不应该在未确认流量、磁盘空间和授权的情况下直接下载。

当前下载器不支持断点续传；网络不稳时建议用浏览器或专用下载器。

## 内容边界

模型中心可以搜索成人向资源，但软件仍只允许：

- 18+ 虚构角色
- 禁止未成年、幼态、儿童化、年龄不明
- 禁止真实人物性化
