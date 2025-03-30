# GraphRAG Server

基于 GraphRAG 2.1.0 实现的知识图谱检索与问答服务，支持多索引配置，OpenAI API兼容。

## 特性

- ✅ 支持多索引配置：可以从多个外部索引目录加载数据
- ✅ OpenAI API兼容：实现兼容OpenAI的接口，可与各种客户端无缝集成
- ✅ 多种搜索引擎：支持本地、全局、漂移和基础搜索模式
- ✅ 流式响应：支持流式输出，实时展示生成结果
- ✅ 兼容性强：兼容新旧版本的GraphRAG数据文件
- ✅ 容错处理：对缺失的数据文件和配置进行优雅处理

## 环境要求

- Python 3.10+
- GraphRAG 2.1.0
- FastAPI
- uvicorn

## 安装

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/graphrag-server.git
cd graphrag-server
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

## 配置

### 环境变量

服务可以通过环境变量或`.env`文件进行配置：

```
# 服务器配置
GRAPHRAG_HOST=0.0.0.0
GRAPHRAG_PORT=8088

# 数据目录配置
GRAPHRAG_ROOT=./data
GRAPHRAG_DATA=./data
GRAPHRAG_CONFIG=./config.json

# 多索引配置
GRAPHRAG_MULTIPLE_INDICES=index1:data1,index2:data2
```

### 多索引配置

多索引配置格式为：`索引名:根目录:数据目录,索引名2:根目录2:数据目录2`

例如：
```
GRAPHRAG_MULTIPLE_INDICES=project1:/path/to/project1:/path/to/project1/data,project2:/path/to/project2:/path/to/project2/data
```

也可以省略根目录：
```
GRAPHRAG_MULTIPLE_INDICES=project1:/path/to/project1/data,project2:/path/to/project2/data
```

## 启动服务

```bash
python -m webserver.main
```

或使用uvicorn直接启动：

```bash
uvicorn webserver.main:app --host 0.0.0.0 --port 8088 --reload
```

## API接口

服务启动后，默认监听在`http://localhost:8088`：

### 首页
- `GET /` - 服务首页，包含API使用说明

### OpenAI兼容接口
- `GET /v1/models` - 获取所有可用模型
- `GET /v1/indices` - 获取所有可用索引
- `POST /v1/chat/completions` - 聊天补全API，与OpenAI兼容
- `GET /v1/references/{index_id}/{datatype}/{id}` - 获取参考信息详情

## 客户端示例

### Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8088/v1",  # 服务地址
    api_key="dummy-key"  # 任意值即可，服务不验证密钥
)

# 使用默认索引查询
response = client.chat.completions.create(
    model="global",  # 搜索模型：local, global, drift, basic
    messages=[
        {"role": "user", "content": "什么是GraphRAG?"}
    ],
    temperature=0.7
)

print(response.choices[0].message.content)

# 使用特定索引查询
response = client.chat.completions.create(
    model="global",
    messages=[
        {"role": "user", "content": "什么是GraphRAG?"}
    ],
    index_id="project1"  # 指定索引
)

print(response.choices[0].message.content)
```

### 流式响应示例

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8088/v1",
    api_key="dummy-key"
)

# 流式响应
response = client.chat.completions.create(
    model="global",
    messages=[
        {"role": "user", "content": "什么是GraphRAG?"}
    ],
    stream=True  # 启用流式响应
)

# 实时输出回答
for chunk in response:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="", flush=True)
print()
```

## 文件结构

```
graphrag-server/
├── webserver/
│   ├── configs/
│   │   └── settings.py          # 配置管理
│   ├── routes/
│   │   └── api.py               # API路由
│   ├── search/
│   │   ├── base.py              # 搜索引擎基础功能
│   │   └── indexdata.py         # 索引数据处理
│   ├── templates/
│   │   └── index.html           # 首页模板
│   ├── utils/
│   │   └── consts.py            # 常量定义
│   └── main.py                  # 主程序入口
├── .env                         # 环境变量(可选)
├── config.json                  # GraphRAG配置
└── requirements.txt             # 依赖列表
```

## GraphRAG 2.1.0 数据文件说明

GraphRAG 2.1.0 相比之前版本的数据文件命名有变化：

- `create_final_nodes.parquet` → `entities.parquet`
- `create_final_text_units.parquet` → `text_units.parquet`
- `create_final_relationships.parquet` → `relationships.parquet`
- 新增 `documents.parquet`

服务会自动检测文件是否存在，并支持新旧版本的文件名。

## 许可证

MIT
