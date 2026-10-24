<!-- trunk-ignore-all(markdownlint/MD033) -->
<!-- trunk-ignore(markdownlint/MD041) -->
<div align="center">
  <img src=".github/resources/isotipo.png" height="180px" width="auto" alt="RomM 标志">

  <h3 style="font-size: 25px;">
    一款美观、强大、可自行托管的 ROM 管理与游玩工具。
  </h3>
</div>

<div align="center">
  <div dir="auto">
    <a href="https://trendshift.io/repositories/14133?utm_source=repository-badge&amp;utm_medium=badge&amp;utm_campaign=badge-repository-14133" target="_blank" rel="noopener noreferrer"><img src=".github/resources/trendshift-badge.svg" alt="Trendshift" width="250" height="58"/></a>
    <a href="https://news.ycombinator.com/item?id=44247964" target="_blank" rel="noopener noreferrer"><img src=".github/resources/hackernews-badge.svg" width="250px" alt="Hacker News 徽章"></a>
    <br />
    <a href="https://selfh.st/survey/2025-results/" target="_blank" rel="noopener noreferrer"><img src=".github/resources/selfhst-badge.svg" width="250px" alt="selfh.st 徽章"></a>
    <a href="https://discord.gg/invite/romm" target="_blank" rel="noopener noreferrer"><img src=".github/resources/discord-badge.svg" alt="Discord" width="250" height="58"/></a>
  </div>
</div>

# 概述

RomM（ROM 管理器）提供简洁的响应式界面，让你能够扫描游戏收藏、补全游戏资料、浏览和游玩游戏。RomM 支持多个游戏平台、多种命名规则和自定义标签，是模拟器玩家的必备工具。

## 功能

- 扫描游戏库，并使用 [IGDB][igdb-api]、[Screenscraper][screenscraper-api] 和 [MobyGames][mobygames-api] 的元数据补全游戏资料
- 从 [SteamGridDB][steamgriddb-api] 获取自定义美术素材
- 展示你在 [Retroachievements][retroachievements-api] 上的游戏成就
- 提供 [400 多个游戏平台][docs-supported-platforms] 的元数据
- 使用 [EmulatorJS][docs-emulatorjs] 和 [RuffleRS][docs-rufflers] 直接在浏览器中游玩游戏
- 与朋友共享游戏库，并限制其访问范围和操作权限
- 提供适用于 [Playnite][playnite-app]、[Android][argosy-launcher] 和[自定义固件（CFW）][grout]的官方应用
- 支持多碟游戏、可下载内容（DLC）、模组、改版游戏、补丁和说明书
- 解析文件名中的[标签][docs-tag-support]，并按标签筛选
- 通过任意现代网页浏览器查看、上传、更新和删除游戏

## 界面预览

|                                       🖥 桌面端                                        |                                                           📱 移动端                                                            |
| :------------------------------------------------------------------------------------: | :----------------------------------------------------------------------------------------------------------------------------: |
| <img src=".github/resources/screenshots/preview-desktop.webp" alt="桌面端界面预览" /> | <img style="width: 325px; aspect-ratio: auto;" src=".github/resources/screenshots/preview-mobile.webp" alt="移动端界面预览" /> |

## 安装

开始使用 RomM，请参阅文档中的[快速入门指南][docs-quick-start-guide]。如果使用过程中遇到问题，请参阅[故障排查步骤][docs-troubleshooting]。

## 相对于分叉基线的改动

与分叉基线提交 `6c3b32582594eb6f94bc858a05db78f33e84b882` 相比：

- **串流与联机：** 移除了相关后端 API、套接字处理程序、配套模块，以及串流接口测试。
- **游戏元数据：** 为扫描及自动更新时获取的游戏名称和简介新增简体中文翻译，支持缓存，翻译失败时保留原文。
- **模拟器配置：** 未设置相应环境变量时，默认禁用 EmulatorJS、RuffleRS、JSDos 和 PICO-8。
- **数据库解析：** 修复了布尔值、浮点数和整数转换辅助函数中的异常元组语法。

各文件的具体改动请参阅 [ChangeFromUpstream.md](ChangeFromUpstream.md)。

## 参与贡献

如需为 RomM 做出贡献，请参阅[贡献指南](./CONTRIBUTING.md)。

## 官方应用

由 RomM 团队开发和维护的应用与集成。

- [Argosy][argosy-launcher]，作者 [@tmgast](https://github.com/tmgast)：用于安装和启动游戏的原生 Android 客户端。
- [Grout][grout]，作者 [@BrandonKowalski](https://github.com/BrandonKowalski)：直接在基于 Linux 的复古掌机上，从你的 RomM 实例下载和管理游戏。支持：Allium、Batocera、Knulli、MinUI、muOS、NextUI、Onion、ROCKNIX、Spruce、TrimUI。
- [Playnite 插件][playnite-app]，作者 [@gantoine](https://github.com/gantoine)：适用于 Playnite 的游戏库插件。

## 社区项目

以下项目由社区成员维护。请注意，RomM 团队不会定期审查这些项目的源代码。

### 移动端

- [romm-ios-app][romm-ios-app]：由 [@ilyas-hallak](https://github.com/ilyas-hallak) 开发的原生 iOS 应用。

### 桌面端

- [RetroArch Sync][romm-retroarch-sync]：由 [@Covin90](https://github.com/Covin90) 开发，用于在 RetroArch 与 RomM 之间同步游戏库。
- [RomMate][rommate]：由 [@brenoprata10](https://github.com/brenoprata10) 开发，用于浏览游戏收藏的桌面应用。
- [romm-client][romm-client]：由 [@chaun14](https://github.com/chaun14) 开发的桌面客户端。
- [Freegosy][freegosy]：由 [@abduznik](https://github.com/abduznik) 开发的一体化游戏管理工具。

### 掌机

- [DeckyRommSync][decky-romm-sync]：由 [@danielcopper](https://github.com/danielcopper) 开发，适用于 SteamOS 的下载与同步工具。
- [SwitchRomM][switch-romm]：由 [@Shalasere](https://github.com/Shalasere) 开发，适用于 Switch 的 NRO 格式自制程序。

### 其他

- [romm-comm][romm-comm-discord-bot]：由 [@idio-sync](https://github.com/idio-sync) 开发的 Discord 机器人。
- [GGRequestz][ggrequestz]：由 [@XTREEMMAK](https://github.com/XTREEMMAK) 开发，用于发现游戏和提交游戏请求的工具。
- [Syncthing sync][syncthing-sync]：由 [@amn-96](https://github.com/amn-96) 开发，用于将 Syncthing 库推送到 RomM 的小工具。

## 支持本项目

欢迎通过 Open Collective 支持本项目的开发。所有资金都将用于支付 RomM 的托管、开发和维护费用。

<div align="center">
  <div dir="auto">
    <a href="https://opencollective.com/romm" target="_blank" rel="noopener noreferrer"><img src=".github/resources/opencollective-badge.svg" alt="Open Collective" width="250" height="58"/></a>
  </div>
</div>

## 友好项目

以下是一些你可能感兴趣的项目：

- [EmulatorJS](https://emulatorjs.org/)： 可嵌入网页的浏览器模拟器
- [RetroDECK](https://retrodeck.net/)： 在 SteamOS 和 Linux 上畅玩复古游戏
- [ES-DE Frontend](https://es-de.org/)： 适用于 Linux、macOS 和 Windows 的模拟器前端
- [Gaseous](https://github.com/gaseous-project/gaseous-server)： 另一款内置网页模拟器的 ROM 管理工具
- [Retrom](https://github.com/JMBeresford/retrom)： 集中式游戏库与游戏收藏管理服务
- [Drop](https://droposs.org/)： 为无数字版权管理（DRM）限制的游戏提供类似 Steam 的体验
- [LanCommander](https://lancommander.app/)： 面向 PC 游戏的数字游戏平台
- [Steam ROM Manager](https://steamgriddb.github.io/steam-rom-manager/)： 用于在 Steam 中管理 ROM 的应用

## 支持方

以下公司通过免费提供工具来支持我们：

<div align="center">
  <div dir="auto">
    <a href="https://www.greptile.com/?utm_source=oss_badge&amp;utm_medium=readme&amp;utm_campaign=greptile_for_open_source" target="_blank" rel="noopener noreferrer"><img src=".github/resources/greptile-badge.svg" alt="Greptile" width="250" height="58"/></a>
    <a href="https://www.aikido.dev/" target="_blank" rel="noopener noreferrer"><img src=".github/resources/aikido-badge.svg" alt="Aikido" width="250" height="58"/></a>
  </div>
</div>

<!-- 文档链接 -->

[docs-quick-start-guide]: https://docs.romm.app/latest/Getting-Started/Quick-Start-Guide/
[docs-supported-platforms]: https://docs.romm.app/latest/Platforms-and-Players/Supported-Platforms/
[docs-emulatorjs]: https://docs.romm.app/latest/Platforms-and-Players/EmulatorJS-Player/
[docs-rufflers]: https://docs.romm.app/latest/Platforms-and-Players/RuffleRS-Player/
[docs-troubleshooting]: https://docs.romm.app/latest/Troubleshooting/Scanning-Issues/
[docs-tag-support]: https://docs.romm.app/latest/Getting-Started/Folder-Structure/#tag-support

<!-- 外部链接 -->

[igdb-api]: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#igdb
[screenscraper-api]: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#screenscraper
[mobygames-api]: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#mobygames
[steamgriddb-api]: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#steamgriddb
[retroachievements-api]: https://docs.romm.app/latest/Getting-Started/Metadata-Providers/#retroachievements
[romm-comm-discord-bot]: https://github.com/idio-sync/romm-comm
[decky-romm-sync]: https://github.com/danielcopper/decky-romm-sync
[switch-romm]: https://github.com/Shalasere/SwitchRomM
[playnite-app]: https://github.com/rommapp/playnite-plugin
[ggrequestz]: https://github.com/XTREEMMAK/ggrequestz
[syncthing-sync]: https://github.com/amn-96/romm_syncthing_sync
[romm-client]: https://github.com/chaun14/romm-client
[romm-retroarch-sync]: https://github.com/Covin90/romm-retroarch-sync
[rommate]: https://github.com/brenoprata10/rommate
[freegosy]: https://github.com/abduznik/freegosy
[grout]: https://github.com/rommapp/grout
[romm-ios-app]: https://github.com/ilyas-hallak/romm-ios-app
[argosy-launcher]: https://github.com/rommapp/argosy-launcher
