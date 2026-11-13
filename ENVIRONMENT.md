# 当前环境与复现入口

最近核对日期：2026-11-12（Asia/Shanghai）。工作目录：`/home/zhaozihan/vLLM`。

本文持续维护当前环境；环境变化时同步更新。历史实验使用的具体版本与参数保存在相应编号文档和实验目录，不能只引用本文代替实验快照。

- [研究文档索引](docs/README.md)
- [00：项目起步基线](docs/00-项目概览与环境基线.md)
- [助手协作约定](AGENTS.md)

## 1. 主机与部署方式

模型推理、Agent、DeepSWE 任务执行及独立评分均计划在本机完成，采用 ARM64 原生容器路线。CPU 承担构建、代码执行与测试；NPU 承担模型推理。

| 项目 | 已核对的配置 |
| --- | --- |
| 操作系统 | Huawei Cloud EulerOS 2.0 |
| CPU 架构 | aarch64 / ARM64 |
| CPU | Kunpeng 920，192 个逻辑 CPU，8 个 NUMA 节点 |
| 主机内存 | 约 1.5 TiB，无 Swap |
| NPU | 8 × Ascend 910B1，每卡 64 GiB HBM |
| npu-smi 工具报告 | 25.5.0；驱动与固件的完整版本组合待推理部署阶段核对 |
| 工作区存储 | `/home/zhaozihan/vLLM`，约 7 TiB 的磁盘 |
| Docker 存储 | `/var/lib/docker`，独立约 14 TiB 的磁盘，overlay2 |

2026-11-12 检查时，工作区剩余约 691 GiB，Docker 数据盘剩余约 12 TiB。空闲资源为时点数据，不代表专属资源配额；启动实验前重新检查。

## 2. 已可用的评测软件

| 组件 | 当前版本或位置 |
| --- | --- |
| 系统默认 Python | 3.9.9，保持原样 |
| 项目独立 Python | 3.12.15，`.runtime/python/` |
| Pier | 0.3.1，`pier/`；虚拟环境在 `pier/.venv/` |
| Pier 依赖 | 按 `pier/uv.lock` 安装 |
| 系统 Docker Engine | 18.09.0，API 1.39，沿用既有服务 |
| 项目 Docker CLI | 27.5.1，`.runtime/bin/docker` |
| 项目 Docker Compose | 2.32.4，`.runtime/docker-config/cli-plugins/docker-compose` |
| Docker 配置目录 | `.runtime/docker-config/` |
| 命令包装器 | `scripts/with_arm_env.sh` |

包装器设置项目工具路径和 Docker 配置，禁用 BuildKit，并使用本地 LiteLLM 费用表。新客户端已验证可协商到旧 Engine 的 API；不据此假定所有现代 Docker 功能都可用。需要当前用户能够访问 Docker 服务。

### 源码与 ARM 基础镜像

| 对象 | 已固定的版本 |
| --- | --- |
| DeepSWE | `0b9fabbb63b9104d678fe965e1632f2dd9eaa2ea` |
| Pier | `b26211ed2bbee6d145f6b8c5b80e39f18b296f08`，另有本地权限补丁 |
| 基础镜像 | `public.ecr.aws/x8v8d7g8/mars-base@sha256:8d4d973c993776850e6249f909431040f0f0e694162768b1ed1409ba64162cb2` |

基础镜像内为 Python 3.12.12、Go 1.25.5、Node 24.12.0、Cargo 1.92.0。宿主和容器内版本分别记录。

本地权限补丁：[pier-readable-artifacts.patch](arm/patches/pier-readable-artifacts.patch)。它在 Linux 命令包装层设置 `umask 022`，让宿主用户能及时读取容器写入的评分文件。

## 3. 镜像构建、网络与资源设置

- 官方 113 个任务镜像均只有 amd64 版本，本项目重建 ARM64 任务及评分镜像。
- 构建入口为 `scripts/build_arm_task.sh`；使用经典构建器、host 网络，以及调用环境中已有的 HTTP(S) 代理变量。不要将构建代理设置误当作任务运行阶段的网络配置。
- 构建额度为 2 核 CPU、8 GiB 内存。
- 每个任务的 Agent 环境与独立评分环境分别配置为 2 核 CPU、8 GiB 内存、20 GiB 存储额度；存储额度不等于镜像实际大小或已验证的本机硬配额。
- 评分环境保留无网络配置；真实模型 Agent 的 API 网络白名单仍待联调。
- 冒烟检查使用 `--no-delete`，结束后移除相应容器、保留本地镜像。服务器存在其他项目的镜像，不做全局清理。

## 4. 模型与 NPU 推理环境：尚未部署验证

| 项目 | 当前决定或待确认项 |
| --- | --- |
| 主模型 | 已选定 `Qwen/Qwen3.8-27B` BF16 原始权重 |
| 备用模型 | Qwen3.6-27B BF16，出现明确兼容问题时再评估切换 |
| 模型权重 | 尚未下载并固定 revision、文件校验与最终存储位置 |
| 推理框架 | 计划使用 vLLM + vLLM-Ascend |
| 既有镜像 | 主机已有多个 vLLM-Ascend 镜像，包括 v0.30.0；不等于本项目已完成模型推理验证 |
| CANN | 存在多个安装目录，包括 8.5.0、9.2.0-beta.1；实际使用版本待固定 |
| PyTorch / torch-npu / vLLM 版本 | 随最终选定推理容器核对并固定 |
| 模型 Agent | 计划优先 mini-swe-agent；尚未完成安装与本地服务联调 |
| 并行、上下文、并发、采样 | 待实测确定，暂无已验证的正式参数 |
| 服务地址与端口 | 待部署确定 |

推理部署成功后，将上述待确认项替换为实测值，记录容器镜像摘要、权重 revision、组件版本和启动配置，并在对应编号文档中保留当次快照。

## 5. 任务环境的实际验证状态

- 已生成 113 个 ARM 配置副本，并通过任务格式解析。
- 已构建和完成正负对照的任务有 5 个：HTTPX（Python）、Tengo（Go）、Yjs（JavaScript）、ts-pattern（TypeScript）、Pest（Rust）。
- 10 次最终对照均符合预期，完整历史另有 1 次修复前的权限异常。其余 108 个任务未完成构建与实测。
- 目前没有真实模型 Agent 的任务分数。参考解答验证与模型成功率分别报告。

证据：[验证汇总](arm/validation.json)、[原始记录](arm/jobs/)、[ARM 配置清单](arm/manifests/all-tasks.json)、[操作说明](arm/README.md)。实际状态变化后同步更新本节。

## 6. 常用入口

本地环境、上游 checkout 和生成的任务不纳入主仓库。新机器按 [根 README](README.md) 使用 `scripts/bootstrap.py` 与 [固定版本清单](config/versions.json) 恢复；当前环境可用 `python3 scripts/bootstrap.py --check` 核对。公开检查摘要见 [results/README.md](results/README.md)，完整实验数据仍保留在原工作区。

公开仓库为 [Carotte215/vllm-ascend-deepswe](https://github.com/Carotte215/vllm-ascend-deepswe)，本地远程名为 `origin`。已授权 GitHub 连接可用于仓库读写；服务器终端的 HTTPS/SSH 推送认证尚未配置，两者分别管理。

```bash
cd /home/zhaozihan/vLLM

# 查看工具版本。
scripts/with_arm_env.sh pier --version
scripts/with_arm_env.sh docker compose version

# 复现一个已适配任务的构建与正负对照。
scripts/build_arm_task.sh httpx-multipart-response-parsing
scripts/smoke_arm_task.sh httpx-multipart-response-parsing oracle
scripts/smoke_arm_task.sh httpx-multipart-response-parsing nop

# 汇总已有记录。
python3 scripts/summarize_arm_checks.py
```

重建会覆盖该任务在 `arm/build-logs/` 下的构建日志，需要保留时先归档；每次冒烟运行在 `arm/jobs/` 中生成新记录。

## 7. 更新记录

| 日期 | 变化 |
| --- | --- |
| 2026-11-12 | 建立当前环境说明，区分已实测评测工具与尚待部署的模型推理环境。 |
| 2026-11-13 | 增加主 Git 仓库、版本清单和恢复入口；上游源码与运行环境继续保留在本地，未改变既有推理或容器服务。 |
