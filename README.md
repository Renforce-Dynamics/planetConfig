# planetConfig

共享配置与通信协议，供 Planet 服务和执行器独立使用。

## 安装与使用

需要 Python 3.10+、`uv`。

```bash
git clone git@github.com:Renforce-Dynamics/planetConfig.git
cd planetConfig
./scripts/bootstrap.sh

# 展开配置、覆盖参数，并保存本次配置快照
./scripts/run.sh -- resolve configs/entry/entry_example.yaml \
  --set service.rate_hz=100 --output runs/example
```

处理自己的配置：

```bash
.venv/bin/planet-config resolve ./site.yaml --output runs/site
.venv/bin/planet-config diff ./site.yaml ./other-site.yaml
```

## 在项目中使用

| 包 | 导入名 | 内容 |
| --- | --- | --- |
| `planet-config` | `planet_config` | YAML 继承、资源定位、参数覆盖和快照 |
| `planet-protocol` | `planet_protocol` | PLNJ、状态查询、关节目标和定位协议 |

```python
from planet_config import load_config

config = load_config("configs/entry/entry_example.yaml",
                     overrides=["service.rate_hz=100"])
config.freeze("runs/site")
```

配置支持有序 `extends` 和 `compose`；字典逐项合并，列表替换。
本仓库示例在根目录 `configs/`，安装包只包含代码。快照保存生效配置、来源、覆盖参数和摘要。
通用 `resolve_resource` API 保留显式 `pkg://` 兼容能力，仓库示例不依赖包内数据。
业务字段由各服务校验，配置库只依赖 PyYAML，协议包只依赖标准库。

## 文档与开发

- [协议、客户端与数据格式](packages/planet-protocol/README.md)
- [配置约定](docs/configuration.md)
- [配置 API](src/planet_config/__init__.py)

开发：`./scripts/test.sh` 运行测试，`./scripts/build.sh` 构建安装包。

本仓库无 submodule，不依赖 Cadence、模型或 SDK；消费者按需安装共享包。
工具支持 `--venv /path/to/env`；默认环境为 `.venv`。

由 **Renforce Dynamics** 开发维护，采用 [MIT License](LICENSE)。
