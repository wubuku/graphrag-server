# GraphRAG Server 升级与使用说明

[![DeepWiki](https://img.shields.io/badge/DeepWiki-Docs-blue?logo=read-the-docs)](https://deepwiki.com/wubuku/graphrag-server)

## 升级

已经将GraphRAG升级到2.1.0版本，其他依赖包也更新到更新的稳定版本。

新版本对输出文件进行了调整。我们先修改了文件 `webserver/utils/consts.py`，将部分输出文件名修改为新版本的形式。

GraphRAG 2.1.0版本的主要更改：

1. **文件命名约定变更**：
   - 原 `create_final_nodes.parquet` → 现 `entities.parquet`
   - 原 `create_final_text_units.parquet` → 现 `text_units.parquet`
   - 原 `create_final_relationships.parquet` → 现 `relationships.parquet`
   - 原 `create_final_communities.parquet` → 现 `communities.parquet`
   - 原 `create_final_community_reports.parquet` → 现 `community_reports.parquet`
   - 新增 `documents.parquet`

2. **配置结构变化**：
   - `storage`属性被`output`属性替代
   - `embeddings`属性的某些功能被移到`vector_store`中
   - 实体和嵌入信息现在合并在一个文件中

3. **已移除的功能**：
   - `covariates` (声明/claims)功能在GraphRAG 2.1.0中已移除


## 使用外部建立的索引结果

修改配置文件：`webserver/configs/settings.py`，确保路径指向正确的数据目录。

执行下面的命令安装依赖：

```shell
pip install -r requirements.txt
```

检查安装是否完整：

```shell
python -c "import graphrag; print(graphrag.__path__[0])" | xargs ls -la
```

这应该显示包目录中的文件，确认是否有实际内容。

如需完全卸载并重新安装：

```shell
pip uninstall -y graphrag
pip cache purge
pip install graphrag==2.1.0
```

在执行 `pip install -r requirements.txt` 之后，直接可以启动服务器：

```shell
# conda activate graphrag
# source .env
python -m webserver.main
```

## 服务端点

GraphRAG Server提供以下主要端点：

### 1. 主页
- **URL**: `http://localhost:20213/`
- **方法**: GET
- **描述**: 显示GraphRAG Web Server的主页和基本信息
- **使用**: 在浏览器中访问此URL

### 2. 搜索API
- **URL**: `http://localhost:20213/v1/chat/completions`
- **方法**: POST
- **描述**: 兼容OpenAI格式的聊天完成API，用于执行文档搜索和问答
- **参数**:
  - `model`: 指定搜索模型，可选值有：
    - `local` - 本地搜索
    - `global` - 全局搜索
    - `drift` - 漂移搜索
    - `basic` - 基础搜索
  - `messages`: 消息数组，包含用户的查询
  - `stream`: 布尔值，是否使用流式响应
- **示例请求**:
  ```shell
  curl -X POST "http://localhost:20213/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local",
    "messages": [
      {"role": "user", "content": "Who is Leonardo da Vinci?"}
    ],
    "stream": false
  }'
  ```

### 3. 查看引用详情
- **URL**: `http://localhost:20213/v1/references/{index_id}/{datatype}/{id}`
- **方法**: GET
- **描述**: 显示引用项的详细信息
- **参数**:
  - `index_id`: **此参数实际未在代码中使用，可使用任意值**
  - `datatype`: 数据类型，可选值为:
    - `entities` - 实体
    - `sources` - 源文本单元(text units)
    - `reports` - 社区报告
    - `relationships` - 关系
  - `id`: 数据项的数字ID
- **示例**:
  - `http://localhost:20213/v1/references/local/entities/42`
  - `http://localhost:20213/v1/references/local/sources/7`

### 4. 可用模型列表
- **URL**: `http://localhost:20213/v1/models`
- **方法**: GET
- **描述**: 返回可用的搜索模型列表


查询示例：
```shell
curl -X POST "http://localhost:20213/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local",
    "messages": [
      {"role": "user", "content": "玫瑰痤疮有什么治疗方案？(answer with reference only to data sources, but not to entities, relationships, or communities)"}
    ],             
    "stream": false
  }'
```

返回结果：
```json
{"id":"chatcmpl-750577b87d0e4444910d513fdf64cb31","choices":[{"finish_reason":"stop","index":0,"logprobs":null,"message":{"content":"玫瑰痤疮的治疗方案包括多种方法，例如：\n\n*   **氨甲环酸**：研究表明，外用3%氨甲环酸溶液可以改善红斑、减少炎症性皮损数目，升高角质层含水量，降低TEWL值和pH值，此外还改善了角质层的完整性，减弱了患者对于乳酸刺激试验的反应 [^Data:Sources(30)]。\n*   **多西环素**：多西环素是一种用于治疗玫瑰痤疮的系统治疗药物，具有抗炎特性 [^Data:Sources(35)]。\n*   **防晒霜**：防晒霜可以帮助保护皮肤免受亚红斑剂量的紫外线辐射 [^Data:Sources(35)]。\n\n这些治疗方案可以帮助改善玫瑰痤疮的症状并促进皮肤屏障功能的恢复。\n[^Data:Sources(35)]: [Sources: 35](http://127.0.0.1:20213/v1/references/local/sources/35)\n[^Data:Sources(30)]: [Sources: 30](http://127.0.0.1:20213/v1/references/local/sources/30)","refusal":null,"role":"assistant","annotations":null,"audio":null,"function_call":null,"tool_calls":null}}],"created":1743326931,"model":"local","object":"chat.completion","service_tier":null,"system_fingerprint":null,"usage":{"completion_tokens":-1,"prompt_tokens":0,"total_tokens":-1,"completion_tokens_details":null,"prompt_tokens_details":null}}
```


## 调试问题

如果服务器启动或搜索遇到问题，可以使用提供的`debug_server.py`脚本进行调试：

1. 首先确保设置正确的路径：
   ```python
   root = Path("/path/to/your/graphrag/project")
   data_dir = Path("/path/to/your/graphrag/project/output")
   ```

2. 运行调试脚本：
   ```shell
   python debug_server.py
   ```

3. 脚本会检查：
   - 配置文件是否正确加载
   - 数据目录中是否存在所需的parquet文件
   - 是否可以成功加载上下文和搜索引擎

## GraphRAG Server 引用系统实现解析

GraphRAG服务器的引用系统由以下几个关键组件共同工作：

### 1. LLM系统提示（System Prompts）

在`prompts`目录下的文件（如`basic_search_system_prompt.txt`和`local_search_system_prompt.txt`）中，包含了对大语言模型的明确引用格式指导：

```
Points supported by data should list their data references as follows:
"This is an example sentence supported by multiple data references [^Data:<dataset name>(record id)] [^Data:<dataset name>(record id)]."
```

其中，`<dataset name>`可以是以下类型之一：
- Entities（实体）
- Relationships（关系）
- Sources（来源）
- Reports（报告）

系统提示明确指导LLM在生成回答时，使用特定格式的引用标记，比如`[^Data:Entities(0)]`，其中"Entities"是数据源类型，"0"是记录ID。

### 2. 引用模式检测

在`webserver/utils/refer.py`文件中，定义了用于识别引用的正则表达式模式：

```python
pattern = re.compile(r'\[\^Data:(\w+?)\((\d+(?:,\d+)*)\)\]')
```

`get_reference()`函数使用此模式识别文本中的所有引用，并按数据源类型对它们进行分组：

```python
def get_reference(text: str) -> dict:
    data_dict = defaultdict(set)
    for match in pattern.finditer(text):
        key = match.group(1).lower()
        value = match.group(2)

        ids = value.replace(" ", "").split(',')
        data_dict[key].update(ids)

    return dict(data_dict)
```

### 3. 将引用转换为可点击链接

LLM生成带有引用标记的回答后，`generate_ref_links()`函数将这些标记转换为可点击的脚注式链接：

```python
def generate_ref_links(data: Dict[str, Set[int]], index_id: str) -> str:
    base_url = f"{settings.website_address}/v1/references"
    lines = []
    for key, values in data.items():
        for value in values:
            lines.append(f'[^Data:{key.capitalize()}({value})]: [{key.capitalize()}: {value}]({base_url}/{index_id}/{key}/{value})')
    return "\n".join(lines)
```

这些链接指向服务器特定的API端点，用于展示引用的详细信息。

### 4. 响应处理

在`main.py`中，同步和流式响应处理器都会调用上述函数处理引用：

```python
reference = utils.get_reference(response)
if reference:
    response += f"\n{utils.generate_ref_links(reference, request.model)}"
```

这段代码会在回答的底部添加所有脚注链接的定义。

### 5. 引用端点

服务器有专门用于显示引用数据的端点：

```python
@app.get("/v1/references/{index_id}/{datatype}/{id}", response_class=HTMLResponse)
```

此端点渲染HTML模板（如`entities_template.html`），以在用户点击时显示每个引用的详细信息。

### 实际工作流程

1. 用户提出问题
2. 系统将问题发送给LLM，并附带指导其使用特殊引用格式的系统提示
3. LLM生成带有引用标记（如`[^Data:Entities(8)]`）的回答
4. 服务器处理回答，提取所有引用，并在底部添加可点击的脚注链接
5. 当用户点击引用链接时，会看到该特定实体、关系、来源或报告的详细视图

示例输出如下:

```
# Leonardo da Vinci
    Leonardo da Vinci, born in 1452 in the town of Vinci near Florence, is widely celebrated as one of the most versatile geniuses of the Italian Renaissance. His full name was Leonardo di Ser Piero d'Antonio di Ser Piero di Ser Guido da Vinci, and he was the natural and first-born son of Ser Piero, a country notary [Data: Entities (0)]. Leonardo's contributions spanned various fields, including art, science, engineering, and philosophy, earning him the title of the most Universal Genius of Christian times [Data: Entities (8)].
    ## Early Life and Training
    Leonardo's early promise was recognized by his father, who took some of his drawings to Andrea del Verrocchio, a renowned artist and sculptor. Impressed by Leonardo's talent, Verrocchio accepted him into his workshop around 1469-1470. Here, Leonardo met other notable artists, including Botticelli and Lorenzo di Credi [Data: Sources (6, 7)]. By 1472, Leonardo was admitted into the Guild of Florentine Painters, marking the beginning of his professional career [Data: Sources (7)].
```

### 注意事项

1. **index_id参数**: 在引用URL中的`index_id`参数（如`http://localhost:20213/v1/references/local/entities/123`中的"local"）实际上在当前实现中未被使用。服务器总是使用配置文件中指定的单一数据源，无论URL中提供的`index_id`值是什么。

2. **GraphRAG 2.1.0中的变化**: 请注意，GraphRAG 2.1.0移除了`claims`数据类型，现在只支持`entities`、`sources`、`reports`和`relationships`四种数据类型。

3. **资源文件**: 服务器使用`webserver/templates`目录中的HTML模板来渲染引用视图。这些模板包括：
   - `entities_template.html`
   - `relationships_template.html`
   - `reports_template.html`
   - `sources_template.html`
   - `index.html` (主页) 

## 使用 Docker 运行

如果需要使用 Docker 运行，可以参考下面的命令：

```shell
docker run -d \
  -p 20213:20213 \
  -e GRAPHRAG_API_KEY=YOUR_OPENAI_API_KEY \
  -e DEEPSEEK_API_KEY=YOUR_DEEPSEEK_API_KEY \
  -e GRAPHRAG_ROOT_DIR=/app/data \
  -e GRAPHRAG_REFERENCE_BASE_URL=YOUR_REFERENCE_BASE_URL \
  -e GRAPHRAG_SERVER_PORT=20213 \
  -v /PATH/TO/YOUR/DATA/DIR:/app/data \
  --name graphrag-server \
  {IMAGE_NAME}
```

你需要将占位符 YOUR_OPENAI_API_KEY、YOUR_DEEPSEEK_API_KEY、YOUR_REFERENCE_BASE_URL 替换为实际值。
