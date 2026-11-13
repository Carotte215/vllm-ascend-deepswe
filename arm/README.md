# 本机 ARM DeepSWE 运行说明

所有步骤在 `/home/zhaozihan/vLLM` 内完成。模型推理与任务执行均可放在这台服务器上。本阶段验证的是任务执行和评分环境，还没有运行真实模型 Agent，也没有得到模型成功率。

## 环境与版本

- DeepSWE 源码：`../deep-swe`，commit `0b9fabbb63b9104d678fe965e1632f2dd9eaa2ea`。
- Pier 源码：`../pier`，commit `b26211ed2bbee6d145f6b8c5b80e39f18b296f08`，另有一处本地文件权限适配。
- 独立 Python：3.12.15；Pier 虚拟环境：`../pier/.venv`，依赖按上游 `uv.lock` 安装。
- 项目内 Docker CLI：27.5.1；Compose：2.32.4（已校验官方 SHA256）。
- 复用系统 Docker Engine 18.09，通过 API 自动协商降级。没有替换或重启系统服务。
- ARM 基础镜像固定为 `public.ecr.aws/x8v8d7g8/mars-base@sha256:8d4d973c993776850e6249f909431040f0f0e694162768b1ed1409ba64162cb2`。
- 镜像中工具版本：Python 3.12.12、Go 1.25.5、Node 24.12.0、Cargo 1.92.0。
- Docker 数据盘实际有约 12 TiB 空闲空间；工作目录所在盘是另一个磁盘，空闲约 691 GiB。

## ARM 配置覆盖范围

已生成全部 113 个任务的独立副本，位于 `tasks/`。这不代表全部 113 个任务都已经成功构建或通过实测。已准备的配置清单见 `manifests/all-tasks.json`，实际运行结果见 `validation.json`，完整原始运行记录见 `jobs/`。

每个任务只修改 `task.toml`、`environment/Dockerfile`、`tests/Dockerfile` 中的构建配置与镜像引用。原始提示词、参考解答、隐藏测试、评分器和评分配置逐文件校验 SHA256，保持与上游一致。

针对具体工具的适配：

1. Deno：`cliffy-config-file-parsing` 改用同版本 aarch64 下载地址；尚需该任务实测。
2. 五个 Rust 任务：cargo-nextest 下载入口由 `/linux` 改为 `/linux-arm`，版本保持 0.9.97。官方说明：https://nexte.st/docs/installation/pre-built-binaries/ 。
3. Pest：当前 crates.io 将引导工具解析为 2.9.6，它生成的代码调用任务内 2.8.6 运行库不存在的 API。构建配置将外部 pest_generator、pest_meta、pest 固定到 2.8.6，不修改被评测仓库的源码或测试；Cargo.lock 由构建产生，保存在镜像中。
4. 评分文件权限：本机 Docker 继承 umask 0027，导致容器生成的日志在退出前无法被宿主用户读取。在 Pier 的 Linux 命令包装层设置 umask 022。补丁保存在 `patches/pier-readable-artifacts.patch`。相关上游验证器生命周期测试 15 项通过。

## 验证标准

每个实测任务运行两种无模型检查：

- `oracle`：执行官方参考解答，要求 reward=1，新增功能测试（F2P）与已有回归测试（P2P）全部通过。
- `nop`：不修改代码，要求 reward=0，新增功能测试没有全部通过，已有回归测试全部通过。

两种检查都必须没有评测工具异常。`validation.json` 保留失败尝试，不会用后续成功记录覆盖早期错误。第一次 Go oracle 曾因评分日志权限失败，修复后已经重跑；原始错误仍保留。

### 当前实测结果

| 语言 | 任务 | 参考解答 F2P | 参考解答 P2P | 未修改代码 F2P | 未修改代码 P2P |
| --- | --- | --- | --- | --- | --- |
| Python | httpx-multipart-response-parsing | 122/122 | 1272/1272 | 0/122 | 1272/1272 |
| Go | tengo-callable-instance-isolation | 23/23 | 122/122 | 0/23 | 122/122 |
| JavaScript | yjs-map-conflict-detection | 9/9 | 231/231 | 0/9 | 231/231 |
| TypeScript | ts-pattern-match-each | 85/85 | 6/6 | 0/85 | 6/6 |
| Rust | pest-character-class-coalescing | 104/104 | 250/250 | 0/104 | 250/250 |

上述 5 个任务的 10 次最终对照全部满足预期。全部历史记录共 11 次，另有修复前 Go 的一次权限错误。其余 108 个任务尚未构建或实测。这里的参考解答成功率不是模型成功率。

## 运行方式

例如，重新构建并验证 HTTPX：

```bash
cd /home/zhaozihan/vLLM
scripts/build_arm_task.sh httpx-multipart-response-parsing
scripts/smoke_arm_task.sh httpx-multipart-response-parsing oracle
scripts/smoke_arm_task.sh httpx-multipart-response-parsing nop
python3 scripts/summarize_arm_checks.py
```

需要当前用户能够访问 Docker socket。构建阶段使用 host 网络并继承现有 HTTP(S) 代理，以访问依赖源；这不改变任务运行阶段的网络隔离。构建额度为 2 核 CPU、8 GiB 内存。构建日志位于 `build-logs/`。

包装器 `../scripts/with_arm_env.sh` 只对单个命令设置项目内工具路径，并禁用不适用于当前旧 Engine 的 BuildKit。例如：

```bash
/home/zhaozihan/vLLM/scripts/with_arm_env.sh docker compose version
/home/zhaozihan/vLLM/scripts/with_arm_env.sh pier --version
```

冒烟检查使用 `--no-delete`：任务结束后移除其容器，但保留本地重建镜像，避免重复构建。不要执行全局 Docker 清理命令，服务器还有其他项目的镜像。

## 后续工作

1. 根据 `validation.json` 扩展更多任务的构建与正负对照；浏览器、数据库、其他 Rust 项目依赖尚未验证。
2. 安装并验证模型 Agent；其安装阶段的代理及运行阶段的模型接口网络白名单仍需测试。
3. 选择模型、部署 vLLM-Ascend，固定提示词、采样、Agent 和预算后建立算法基线。

ARM 重建使用了不同于官方 amd64 镜像的执行环境，且部分上游依赖没有完整锁定。本地正负对照通过不能证明与官方运行环境完全等价，也不能替代模型算法效果评测。
