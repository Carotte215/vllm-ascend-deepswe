# DeepSWE ARM 兼容性检查

检查日期：2026-11-12（Asia/Shanghai）。

后续已在本机开始 ARM 适配并进行任务实测。最新运行方式与验证记录见 [ARM 运行说明](arm/README.md) 和 [实际验证结果](arm/validation.json)。下文保留最初检查时的环境快照；其中“尚未构建/安装”的描述仅对应初始检查阶段。

## 结论

Datacurve DeepSWE 当前公开的 113 个任务镜像均为 linux/amd64，不能作为本机 linux/arm64 原生镜像直接运行。共用基础镜像支持 linux/amd64 和 linux/arm64，因此存在从源码重建 ARM 任务环境的路线，但还未实际验证构建和评分。

本次完成的是主机只读检查、源码静态检查以及镜像仓库 manifest/config 元数据检查。没有安装依赖、下载镜像层、构建镜像、运行任务或改动系统服务。工作区新增了官方源码副本和检查记录。

## 固定的源码版本

- DeepSWE：https://github.com/datacurve-ai/deep-swe
  - commit：`0b9fabbb63b9104d678fe965e1632f2dd9eaa2ea`
- Pier：https://github.com/datacurve-ai/pier
  - commit：`b26211ed2bbee6d145f6b8c5b80e39f18b296f08`
  - pyproject 版本：0.3.1。

## 镜像检查

完整结果：`deepswe-image-platforms.json`。共查询 114 个镜像，最终没有未解决的查询错误。首次遇到限流的 6 个镜像已低速重试成功。

| 对象 | 数量 | 镜像清单中的平台 |
| --- | ---: | --- |
| 官方任务镜像 | 113 | 全部仅 linux/amd64 |
| 共用 mars-base 基础镜像 | 1 | linux/amd64、linux/arm64 |

所有 `tasks/*/environment/Dockerfile` 都使用 `public.ecr.aws/x8v8d7g8/mars-base:latest`。全部任务的 `task.toml` 都引用 `public.ecr.aws/d3j8x8q7/swe-bench-202605:*` 预构建任务镜像。

全部 113 个任务使用独立 verifier 环境，且 `tests/Dockerfile` 的 FROM 仍引用对应官方 amd64 任务镜像。ARM 适配必须同步修改任务镜像引用和 verifier 的基础镜像引用，并保留测试隔离机制。仅修改 environment/Dockerfile 或设置 force_build 不足以完成适配：Pier 安装 Agent 时也可能从 task.toml 中的预构建镜像继续构建。

## 主机条件

| 项目 | 检测结果 | 判断 |
| --- | --- | --- |
| CPU 架构 | aarch64，192 核 Kunpeng 920 | ARM64 主机 |
| 主机内存 | 约 1.5 TiB | 具备运行多个任务环境的资源基础 |
| 工作区磁盘剩余 | 约 694 GiB | 全量构建前需规划空间 |
| 默认 Python | 3.9.9 | 不满足当前 Pier 的 Python >=3.12 要求；可另建独立环境 |
| Docker 客户端/服务端 | 18.09.0，API 1.39，linux/arm64 | 服务实际可访问；仍需验证现代工具链与旧服务端兼容性 |
| Docker Compose | docker compose 与 docker-compose 均未安装 | 当前 Pier 本地后端无法按现状直接使用 |
| 已有推理镜像 | 存在多个 vLLM-Ascend 镜像，包括 v0.30.0 | 不代表已有 DeepSWE 环境 |

首次受限执行环境无法访问 Docker socket；经允许的只读检查后成功读取服务端版本。因此不能据首次失败判断用户本身没有 Docker 权限。

Pier 源码使用 `docker compose`，并调用 `up --detach --wait`、构建配置中的 `pull_policy: build` 等功能。需要准备支持这些功能的 Compose，并核实它与现有 Engine 的兼容性；本次没有升级或重启 Docker。

## 任务源码中的架构风险

任务语言分布：Python 34、Go 34、TypeScript 35、Rust 5、JavaScript 5。

对任务 Dockerfile、task.toml、test.sh 扫描后发现：

- `cliffy-config-file-parsing/environment/Dockerfile:19` 写死下载 Deno 2.0.0 的 `deno-x86_64-unknown-linux-gnu.zip`，ARM 原生构建需要适配。
- `quill-shared-toolbar-focus` 安装 Playwright Chromium，需实际验证相应版本的 ARM 浏览器与系统依赖。
- Rust 任务涉及 cargo-nextest 的预编译工具下载，需要确认安装器实际选中的架构。
- Python 原生扩展、Node 原生依赖、Go/Rust 编译和测试均未实跑；未发现写死 x86 地址不能视为兼容性通过。

## 可选路线

1. **正式对照优先：x86 执行 DeepSWE，当前 ARM/NPU 服务器提供模型 API。** 任务容器不需要 NPU；推理计算仍在 910B1 上。可以复用官方任务镜像，减少与公开评测环境之间的差异。需要另有 x86 Linux 执行资源及两端 API 网络连通性。
2. **单机学习优先：本机重建 ARM 任务镜像。** 先选一个 Python 和一个 Go 任务，分别验证未修复状态及官方参考解答的评分，再逐步覆盖其他语言。保留上游版本和测试规则，单独保存 ARM 构建配置。全量跑完前不能宣称与官方环境等价。
3. **x86 模拟执行：仅作为可能的诊断方案。** 尚未验证；性能和超时行为可能变化，不建议作为首次正式基线的默认路线。

若走本机 ARM 路线，下一阶段的通过条件应是：独立 Python 环境中 Pier 可运行、容器工具链可用、至少一个 ARM 任务及其独立评分容器构建成功、无模型参与的评分检查成功，随后才接入 vLLM。
