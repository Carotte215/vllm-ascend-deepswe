# vllm-ascend-deepswe

vLLM-Ascend 推理学习与 DeepSWE ARM 评测。

在 Ascend 910B1 八卡 ARM64 服务器上，学习推理框架、适配 Datacurve DeepSWE，并研究推理优化对任务成功率、延迟、吞吐和内存占用的影响。

这是个人学习与实验项目，不是 vLLM、vLLM-Ascend、DeepSWE 或 Pier 的官方发行版。

## 当前进展

- 已生成 113 个 DeepSWE ARM 配置副本。
- 已实际构建并验证 5 个代表任务，覆盖 Python、Go、JavaScript、TypeScript 和 Rust。
- 10 次最终 oracle/nop 对照符合预期；保留 1 次修复前的权限异常记录。
- **尚未运行真实模型 Agent，也没有模型在 DeepSWE 上的成功率。** 其余 108 个任务尚未完成构建与实测。
- 正式实验主模型选型为 Qwen3.8-27B BF16；另讨论过以标准 Attention 小模型学习 KV Cache，尚未开始部署。

[公开环境验证摘要](results/arm-smoke-2026-11-12.json)仅报告参考解答与未修改代码的检查结果，不是模型能力榜单。

## 阅读入口

| 文件 | 内容 |
| --- | --- |
| [docs/README.md](docs/README.md) | 研究文档索引与顺序记录规则 |
| [00：项目概览与环境基线](docs/00-项目概览与环境基线.md) | 项目目标、起步环境、已完成准备和验收标准 |
| [ENVIRONMENT.md](ENVIRONMENT.md) | 原实验服务器的当前环境与复现入口 |
| [AGENTS.md](AGENTS.md) | 工作区助手协作约定 |
| [ARM 操作说明](arm/README.md) | 构建与评分流程、适配原因及结果 |
| [config/versions.json](config/versions.json) | 上游提交、ARM 基础镜像、工具版本与下载校验值 |
| [第三方来源说明](THIRD_PARTY.md) | 上游项目与补丁来源 |

文档中的 `/home/zhaozihan/vLLM` 是原实验路径。新机器在自己的仓库目录执行命令；项目脚本按自身位置定位工作目录。

## 仓库包含什么

```text
config/          固定版本和基础镜像信息
docs/            按编号保存的研究记录
scripts/         环境恢复、ARM 配置生成、构建与验证入口
arm/manifests/   任务来源与文件校验清单
arm/patches/     上游工具的本地适配补丁
results/         主动导出的精简结果摘要
licenses/        第三方许可与通知文件
```

`deep-swe/`、`pier/` 是按固定提交恢复的独立上游仓库，不复制进本仓库。`arm/tasks/`、`.runtime/`、原始日志、模型权重和镜像归档均保留在本地并由 `.gitignore` 排除。现有文件不会因忽略规则而删除。

## 在新机器上恢复

完整运行路线面向 Linux ARM64。需要 Git、Python 3.9+、[uv](https://docs.astral.sh/uv/getting-started/installation/)、可访问的 Docker 服务，以及下载公开依赖的网络条件。NPU 只在后续模型推理阶段需要。

克隆本仓库并进入目录后：

```bash
# 下载固定上游源码，应用补丁，安装项目内 Python 与容器客户端。
python3 scripts/bootstrap.py

# 从上游重新生成全部 ARM 配置副本（不会覆盖已存在的任务副本）。
python3 scripts/prepare_arm_tasks.py --all \
  --base-image "$(cat .runtime/base-image.txt)"

# 检查本地依赖与工具；不启动模型，不构建任务镜像。
python3 scripts/bootstrap.py --check

# 重建并验证一个已实测的任务；这一步会下载依赖并运行 CPU 测试。
scripts/build_arm_task.sh httpx-multipart-response-parsing
scripts/smoke_arm_task.sh httpx-multipart-response-parsing oracle
scripts/smoke_arm_task.sh httpx-multipart-response-parsing nop
python3 scripts/summarize_arm_checks.py
```

只查看上游代码或在非 ARM 主机准备源码时：

```bash
python3 scripts/bootstrap.py --upstreams-only
```

恢复脚本不会替换系统 Python、安装 Docker 服务、升级驱动或重启服务。已有上游 checkout 的 HEAD 不符时会停止，不会重置本地工作。Pier 的已知改动保存在补丁中，恢复时检查后应用；重复执行不会再次叠加同一补丁。

本项目已验证的 Docker 组合是项目客户端 27.5.1、Compose 2.32.4 与既有 Engine 18.09。其他机器的 Docker、网络、资源和 NPU 软件栈需要自行验证；版本清单是复现起点，不是通用兼容性保证。

## 结果与实验归档

原始轨迹、异常和评分保存在被忽略的 `arm/jobs/`，本地汇总为 `arm/validation.json`。导出精简摘要后再提交：

```bash
python3 scripts/export_public_results.py \
  --record-date YYYY-MM-DD \
  --output results/arm-smoke-YYYY-MM-DD.json
```

`--record-date` 填原始实验日期。导出保留每次检查的指标、是否符合预期及异常类型，移除本机路径、异常堆栈和完整轨迹；上游版本、补丁和原始汇总的 SHA256 用于追溯。公开摘要不包含完整原始日志，复现实验应重新运行。

已有文档中指向被忽略目录的链接仅在原实验工作区或重新运行后可用。公开阅读从 `results/` 下的摘要开始。

## 日常版本管理

```bash
git status
git diff
git add <本次修改的文件>
git diff --cached
git commit -m "描述本次变更"
```

修改上游工具时，先保存补丁到 `arm/patches/`，再更新版本清单、恢复步骤和相关研究记录。直接修改被忽略的上游目录不会自动进入本项目的版本历史。

公开仓库：[Carotte215/vllm-ascend-deepswe](https://github.com/Carotte215/vllm-ascend-deepswe)。本地 `origin` 指向 `https://github.com/Carotte215/vllm-ascend-deepswe.git`。

首次文件发布通过已授权的 GitHub 连接完成，发布后将本地 `main` 对齐到 `origin/main`。发布前的本地提交保留在 `local-bootstrap-history` 分支，不删除原历史。

GitHub 连接的授权不等于服务器终端已经登录。后续在服务器直接推送，需要先配置 GitHub CLI/HTTPS 凭据或 SSH 认证；本次没有向服务器保存访问令牌。终端认证可用后：

```bash
git push -u origin main
```

原创代码的对外授权方式尚未选定，未擅自添加根目录 LICENSE；第三方材料的原许可见 [THIRD_PARTY.md](THIRD_PARTY.md)。
