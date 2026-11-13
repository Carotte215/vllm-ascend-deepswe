# 第三方来源与许可

本项目维护自己的实验脚本、文档、版本清单和适配补丁。上游完整源码通过固定版本恢复，不复制进主仓库；生成的任务副本也不纳入主仓库。

| 来源 | 固定版本 | 本项目如何使用 |
| --- | --- | --- |
| [Datacurve DeepSWE](https://github.com/datacurve-ai/deep-swe) | `0b9fabbb63b9104d678fe965e1632f2dd9eaa2ea` | 恢复原始任务；由脚本生成 ARM 构建配置；保留文件哈希清单 |
| [Datacurve Pier](https://github.com/datacurve-ai/pier) | `b26211ed2bbee6d145f6b8c5b80e39f18b296f08` | 运行评测；补丁修改 Linux 命令包装中的默认文件权限 |
| Docker CLI / Compose | 见 `config/versions.json` | 从官方发布地址下载到本地，不提交二进制 |

DeepSWE 与 Pier 的上述版本采用 Apache-2.0。许可文本保存在 [licenses/Apache-2.0.txt](licenses/Apache-2.0.txt)，Pier 的通知保存在 [licenses/pier-NOTICE.txt](licenses/pier-NOTICE.txt)。DeepSWE 内各被评测上游项目保留自己的许可，可查其上游 `PROVENANCE.md`；不因本项目适配而改变。

[pier-readable-artifacts.patch](arm/patches/pier-readable-artifacts.patch)包含 Pier 上下文及本地修改，随原 Apache-2.0 许可和通知保留；具体改动为在 Linux 容器命令执行前设置 `umask 022`。

本文件不替本项目原创部分选择对外授权方式。尚未设置根目录 LICENSE，公开发布前可由项目所有者决定。
