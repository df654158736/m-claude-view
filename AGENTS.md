# 项目规范

## 项目结构

```
backend/src/
├── domain/agent/            # 核心引擎、模型、Prompt、日志
├── application/             # 任务服务、用例编排
├── infrastructure/
│   ├── llm/                 # LLM 客户端（OpenAI 兼容）
│   ├── tools/               # 工具体系
│   │   ├── base.py          #   Tool 基类（Pydantic + __init_subclass__ 自动注册）
│   │   ├── registry.py      #   注册表（执行、MCP 延迟加载目录）
│   │   ├── factory.py       #   工具装配（自动发现 + MCP 子工具创建）
│   │   ├── mcp_server.py    #   MCP 协议适配（stdio / HTTP）
│   │   ├── mcp_sub_tool.py  #   MCP 子工具代理
│   │   └── builtin/         #   内置工具（bash, read_file, load_mcp_tools）
│   ├── config/              # 配置加载（YAML + 环境变量覆盖）
│   └── storage/             # 事件日志读写（JSONL）
├── interfaces/
│   ├── http/                # FastAPI 路由（REST API + 文件上传）
│   └── cli/                 # 交互式 REPL
└── bootstrap/               # 依赖装配 + 启动自报

frontend/                    # 纯静态前端（HTML + CSS + JS，无构建步骤）
backend/tests/               # pytest 测试套件
backend/config.yaml          # 运行时配置
```

依赖方向：`interfaces → application → domain ← infrastructure`，domain 层不依赖外部。

## 常用命令

```bash
# 安装依赖
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# 运行测试
PYTHONPATH=backend pytest backend/tests/ -v

# 运行单个测试文件
PYTHONPATH=backend pytest backend/tests/test_react_engine.py -v

# 启动 Web 服务
./start.sh

# CLI 模式
PYTHONPATH=backend python -m src.interfaces.cli.main
```

## 代码风格

- 4 空格缩进，使用 type hints
- `snake_case` 函数/变量，`PascalCase` 类名，`UPPER_SNAKE_CASE` 常量
- 不写注释，除非解释"为什么"而非"做了什么"
- 不写多行 docstring，一行足够
- 不为假设性的未来需求做设计，不加不需要的抽象

## 工具开发规范

新建工具：在 `backend/src/infrastructure/tools/builtin/` 下创建文件，定义 `Tool` 子类即可。

```python
class MyTool(Tool):
    name = "my_tool"                    # 非空则自动注册
    description = "工具描述"

    class Input(BaseModel):             # Pydantic 声明参数，自动生成 JSON Schema
        param: str = Field(description="参数说明")

    def execute(self, args: Input) -> str:
        return "结果"
```

- `name` 非空即自动注册，无需手动修改 factory 或 registry
- 参数用 Pydantic `Input` 内部类声明，`execute` 接收解析后的 `Input` 实例
- MCP 工具不需要手写工具类，在 `config.yaml` 的 `mcp.servers` 配置即可
- 在 `config.yaml` 的 `tools` 列表中添加 `name + enabled: true` 启用

## 测试规范

- 框架：`pytest` + `unittest.mock`
- 文件命名：`backend/tests/test_<模块>.py`
- 测试命名：按行为描述，如 `test_tool_registry_execute`
- 覆盖成功和失败路径
- Mock 外部依赖（LLM、MCP 服务），不 mock 内部逻辑
- `tool.execute()` 接收 `parse_args()` 返回的对象，不接收 kwargs

## 提交规范

- 使用 Conventional Commits：`feat:` / `fix:` / `refactor:` / `chore:`
- 消息用祈使句，聚焦"为什么改"而非"改了什么"
- 不提交 `.env`、API Key、大文件
- PR 包含：问题/方案摘要、测试命令及结果、配置变更说明

## 安全要求

- API Key 通过环境变量注入，不写入代码或配置文件
- `.env` 已被 `.gitignore` 忽略
- `bash` 工具有任意命令执行能力，生产环境需加白名单
- 文件上传保存在 `uploads/` 目录，注意文件名安全（已做 `Path.name` 过滤）
