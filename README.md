<!-- trunk-ignore-all(markdownlint/MD033) -->
<!-- trunk-ignore(markdownlint/MD041) -->
<div align="center">
  <img src=".github/resources/isotipo.png" height="180px" width="auto" alt="RomM 标志">

  <h3 style="font-size: 25px;">
    一款可自行托管、支持游戏元数据简体中文翻译的 ROM 管理工具。
  </h3>
</div>

# 概述

romm-cn 基于 RomM（ROM 管理器），通过简洁的响应式界面扫描、整理和浏览游戏收藏，支持多个游戏平台、多种命名规则和自定义标签。本分支以游戏库管理和游戏元数据简体中文翻译为重点。

## 功能

- 扫描游戏库，并使用 [IGDB][igdb-api]、[Screenscraper][screenscraper-api] 和 [MobyGames][mobygames-api] 的元数据补全游戏资料
- 从 [SteamGridDB][steamgriddb-api] 获取自定义美术素材
- 展示你在 [Retroachievements][retroachievements-api] 上的游戏成就
- 提供 [400 多个游戏平台][docs-supported-platforms] 的元数据
- 扫描或自动更新游戏元数据时，将获取的游戏名称和简介翻译为简体中文，支持缓存，翻译失败时保留原文
- 与朋友共享游戏库，并限制其访问范围和操作权限
- 支持多碟游戏、可下载内容（DLC）、模组、改版游戏、补丁和说明书
- 解析文件名中的[标签][docs-tag-support]，并按标签筛选
- 通过任意现代网页浏览器查看、上传、更新和删除游戏

## 界面预览

以下截图沿用上游项目，仅供界面参考，不代表本分支的所有功能均可用。

|                                       🖥 桌面端                                        |                                                           📱 移动端                                                            |
| :------------------------------------------------------------------------------------: | :----------------------------------------------------------------------------------------------------------------------------: |
| <img src=".github/resources/screenshots/preview-desktop.webp" alt="桌面端界面预览" /> | <img style="width: 325px; aspect-ratio: auto;" src=".github/resources/screenshots/preview-mobile.webp" alt="移动端界面预览" /> |

## 安装

基础部署方式请参阅上游的[快速入门指南][docs-quick-start-guide]，扫描问题可参考[故障排查步骤][docs-troubleshooting]。使用本分支的修改需要基于当前分支源码构建；上游预构建镜像不包含本分支的定制改动。源码部署说明见 [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md)。

## 本分支的功能状态

| 功能 | 当前状态 |
| --- | --- |
| 游戏库管理 | 保留扫描、元数据获取、浏览、上传、更新、删除和共享等功能。 |
| 浏览器内模拟器 | 已移除，包括 EmulatorJS、Ruffle、js-dos、PICO-8 播放器、联机对战（Netplay）和流媒体（Streaming）。 |
| 存档数据 | 已移除存档、即时存档、固件、游玩记录和记忆卡，数据库中的相关表由迁移 `0129` 删除，且无法回滚。 |
| 设备存档同步 | 已移除。设备与客户端令牌仍可使用，但 Grout、Argosy 等客户端无法再与本服务同步存档。 |
| 游戏元数据翻译 | 扫描及 ROM 更新流程中自动获取的名称、简介会尝试翻译为简体中文；ROM 更新时显式提交的名称和简介保留原值。 |

元数据翻译通过 Google 的公开翻译接口进行，需要服务器能够访问 `translate.googleapis.com`。成功结果缓存在进程内存中，进程重启后缓存失效；请求失败时保留原文。此功能翻译游戏名称和简介，不会翻译 ROM 文件内容，也不会自动批量翻译数据库中已有的所有记录。

## 相对于分叉基线的改动

与分叉基线提交 `6c3b32582594eb6f94bc858a05db78f33e84b882` 相比：

- **游戏元数据：** 为扫描及自动更新时获取的游戏名称和简介新增简体中文翻译，支持缓存，翻译失败时保留原文。
- **模拟器与存档数据：** 移除前后端中所有与模拟器相关的代码，包括播放器、存档、即时存档、截图（ROM 截图保留）、固件、游玩记录、记忆卡和设备存档同步，并新增迁移 `0129` 删除相关数据表；`config.yml` 中的 `emulatorjs`、`streaming` 配置段和 `filesystem.structure.firmware` 会被忽略。
- **README：** 移除顶部徽章，以及「参与贡献」「官方应用」「社区项目」「支持本项目」「友好项目」「支持方」章节及其链接。
- **数据库解析：** 修复了布尔值、浮点数和整数转换辅助函数中的异常元组语法。

各文件的具体改动请参阅 [ChangeFromUpstream.md](ChangeFromUpstream.md)。

<!-- 文档链接 -->

[docs-quick-start-guide]: https://docs.romm.app/latest/Getting-Started/Quick-Start-Guide/
[docs-supported-platforms]: https://docs.romm.app/latest/Platforms-and-Players/Supported-Platforms/
[docs-troubleshooting]: https://docs.romm.app/latest/Troubleshooting/Scanning-Issues/
[docs-tag-support]: https://docs.romm.app/latest/Getting-Started/Folder-Structure/#tag-support

<!-- 外部链接 -->

[igdb-api]: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#igdb
[screenscraper-api]: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#screenscraper
[mobygames-api]: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#mobygames
[steamgriddb-api]: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#steamgriddb
[retroachievements-api]: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#retroachievements
