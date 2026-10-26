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

基础部署方式请参阅上游的[快速入门指南][docs-quick-start-guide]，扫描问题可参考[故障排查步骤][docs-troubleshooting]。上游的预构建镜像 `rommapp/romm` 不包含本分支的改动，需要用本分支源码自行构建。

[`examples/docker-compose.romm-cn.yml`](examples/docker-compose.romm-cn.yml) 会从 `docker/Dockerfile` 构建镜像（标签 `romm-cn:local`）并启动 MariaDB。填好其中的数据库密码、`ROMM_AUTH_SECRET_KEY` 和游戏库路径后，在仓库根目录运行：

```bash
docker compose -f examples/docker-compose.romm-cn.yml up -d --build
```

部署前请注意：

- **使用全新数据库。** 被上游 RomM 镜像迁移过的数据库无法再迁移到本分支，启动时会报 `Can't locate revision`。
- **ScreenScraper 需要开发者凭据。** 自行构建的镜像不含官方 CI 注入的 ScreenScraper 开发者凭据，所有请求都会被拒绝。如有自己的凭据，构建前在环境变量中设置 `SCREENSCRAPER_DEV_ID`、`SCREENSCRAPER_DEV_PASSWORD`；否则请改用 IGDB 等其他元数据源。
- **翻译需要访问 Google。** 服务器无法访问 `translate.googleapis.com` 时，每个 ROM 扫描都会等待超时并保留原文；可以在 compose 中设置 `HTTPS_PROXY`（会作用于所有对外请求）。

开发环境的搭建见 [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md)。

## 本分支的功能状态

| 功能 | 当前状态 |
| --- | --- |
| 游戏库管理 | 保留扫描、元数据获取、浏览、上传、更新、删除和共享等功能。 |
| 浏览器内模拟器 | 已移除，包括 EmulatorJS、Ruffle、js-dos、PICO-8、EasyRPG 播放器、联机对战（Netplay）和流媒体（Streaming）。 |
| 存档数据 | 已移除存档、即时存档、固件、游玩记录和记忆卡，数据库中的相关表由迁移 `0129` 删除，且无法回滚。 |
| 设备 | 保留设备注册和客户端令牌；已移除设备存档同步和向设备推送安装。 |
| 年龄限制 | 不引入上游的年龄限制功能；隐藏平台和隐藏 ROM 仍可用。 |
| 游戏元数据翻译 | 游戏名不再机器翻译：优先用 `backend/utils/official_names_zh.json` 里手动列出的官方中文名，其次用 Wikidata 上该游戏的中文名（按 IGDB slug 自动查询，优先采用标注为简体中文的名称，其次是通用中文标签，不采用繁体和港台译名），都没有就保留数据源给的原名；简介翻译为简体中文，其中的游戏名与标题保持一致。网页手动“匹配 ROM”与扫描走同一流程，编辑表单里手动填写的名称和简介保留原值。 |
| 中文文件名搜索 | 文件名含中文时，按名称搜索 IGDB、MobyGames、ScreenScraper 前先译成英文（去掉“英文版”“汉化版”等标签、`DiscA`/`DiscB` 光盘标记和标题末尾表示第一作的“1”）；`backend/utils/search_titles_en.json` 里已列出的标题直接使用对应英文名（如“斑鸠”→ *Ikaruga*）。 |

元数据翻译通过 Google 的公开翻译接口进行，需要服务器能够访问 `translate.googleapis.com`；自动查官方中文名需要能访问 `query.wikidata.org`，访问不了时游戏名保留原名。成功结果缓存在进程内存中，进程重启后缓存失效；请求失败时保留原文。此功能翻译游戏名称和简介，不会翻译 ROM 文件内容，也不会自动批量翻译数据库中已有的所有记录。中文文件名是机器翻译成英文后再搜索的，官方英文名与直译差别较大的游戏，可以往 `search_titles_en.json` 里添加“中文标题 → 英文标题”；没有添加的仍可能匹配不到，这类文件请改用英文名。

## 相对于分叉基线的改动

与分叉基线提交 `6c3b32582594eb6f94bc858a05db78f33e84b882` 相比：

- **游戏元数据：** 为扫描及自动更新时获取的游戏名称和简介新增简体中文翻译，支持缓存，翻译失败时保留原文；中文文件名在按名称搜索前先译成英文。
- **模拟器与存档数据：** 移除前后端中所有与模拟器相关的代码，包括播放器、存档、即时存档、截图（ROM 截图保留）、固件、游玩记录、记忆卡和设备存档同步，并新增迁移 `0129` 删除相关数据表；`config.yml` 中的 `emulatorjs`、`streaming` 配置段和 `filesystem.structure.firmware` 会被忽略。
- **上游后端同步：** 后端、数据库迁移、Docker 与 nginx 配置、`pyproject.toml` 和 `uv.lock` 已同步到上游 `master` 的 `7eae2b8ff`（2026-10-23），并再次移除了流媒体、联机对战、存档同步、设备推送安装、浏览器内播放器相关的后端代码；前端也同步到该版本（上游已移除 v1 界面和 Console 手柄模式，原 v2 界面成为唯一界面），并再次移除了播放器、存档、固件、流媒体、设备同步和年龄限制相关界面；CI 配置保持分叉自身状态。年龄限制功能不引入；迁移链为 `0129` → `0152` → 上游 `0130` 至 `0150`（跳过只涉及已删除功能的 `0135`、`0136`、`0138`、`0140`、`0141`、`0142`、`0148`），这样旧版分支已标记到 `0152` 的数据库也能补齐后续迁移。
- **同步后的修复：** 修复只有 libretro 封面匹配的 ROM 在扫描时因缺少名称而报错（上游同样存在）；恢复上游权限变更时清理图库缓存、通知默认组成员的逻辑；修复首页统计小组件扩展模式的报错，移除只服务已删功能的前端代码、依赖和无效设置。
- **CI：** 工作流在 `sync/upstream-all` 推送时运行；只适用于上游仓库的镜像发布和 HLTB 更新仅在 `rommapp/romm` 上运行。
- **部署示例：** 新增 `examples/docker-compose.romm-cn.yml`，从本分支源码构建镜像，而不是拉取上游的 `rommapp/romm`。
- **文档与 Agent 规则：** `AGENTS.md` 成为唯一的指令文件（`CLAUDE.md` 只导入它），新增 `project.md`、`test_method.md`、`test_troubleshooting.md`，架构文档和 skills 去掉已删功能。
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
