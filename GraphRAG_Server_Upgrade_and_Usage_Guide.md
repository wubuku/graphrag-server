# GraphRAG Server Upgrade and Usage Guide

## Upgrade

GraphRAG has been upgraded to version 2.1.0, and other dependency packages have also been updated to newer stable versions.

The new version has adjusted the output files. We first modified the file `webserver/utils/consts.py` to change some output file names to the new version format.

Major changes in GraphRAG 2.1.0:

1. **File naming convention changes**:
   - Original `create_final_nodes.parquet` → Now `entities.parquet`
   - Original `create_final_text_units.parquet` → Now `text_units.parquet`
   - Original `create_final_relationships.parquet` → Now `relationships.parquet`
   - Original `create_final_communities.parquet` → Now `communities.parquet`
   - Original `create_final_community_reports.parquet` → Now `community_reports.parquet`
   - New addition: `documents.parquet`

2. **Configuration structure changes**:
   - The `storage` attribute is replaced by the `output` attribute
   - Some functionality of the `embeddings` attribute has been moved to `vector_store`
   - Entity and embedding information are now merged into a single file

3. **Removed functionality**:
   - The `covariates` (claims) functionality has been removed in GraphRAG 2.1.0


## Using Externally Built Index Results

Modify the configuration file: `webserver/configs/settings.py` to ensure the paths point to the correct data directory.

Run the following command to install dependencies:

```shell
pip install -r requirements.txt
```

Check if the installation is complete:

```shell
python -c "import graphrag; print(graphrag.__path__[0])" | xargs ls -la
```

This should display the files in the package directory, confirming if there is actual content.

To completely uninstall and reinstall:

```shell
pip uninstall -y graphrag
pip cache purge
pip install graphrag==2.1.0
```

After executing `pip install -r requirements.txt`, you can directly start the server:

```shell
python -m webserver.main
```

## Service Endpoints

GraphRAG Server provides the following main endpoints:

### 1. Homepage
- **URL**: `http://localhost:20213/`
- **Method**: GET
- **Description**: Displays the homepage and basic information of the GraphRAG Web Server
- **Usage**: Visit this URL in a browser

### 2. Search API
- **URL**: `http://localhost:20213/v1/chat/completions`
- **Method**: POST
- **Description**: OpenAI-compatible chat completion API for document search and question answering
- **Parameters**:
  - `model`: Specify the search model, possible values are:
    - `local` - Local search
    - `global` - Global search
    - `drift` - Drift search
    - `basic` - Basic search
  - `messages`: Array of messages containing the user's query
  - `stream`: Boolean, whether to use streaming response
- **Example Request**:
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

### 3. View Reference Details
- **URL**: `http://localhost:20213/v1/references/{index_id}/{datatype}/{id}`
- **Method**: GET
- **Description**: Displays detailed information of reference items
- **Parameters**:
  - `index_id`: **This parameter is not actually used in the code, any value can be used**
  - `datatype`: Data type, possible values are:
    - `entities` - Entities
    - `sources` - Source text units
    - `reports` - Community reports
    - `relationships` - Relationships
  - `id`: The numeric ID of the data item
- **Examples**:
  - `http://localhost:20213/v1/references/local/entities/42`
  - `http://localhost:20213/v1/references/local/sources/7`

### 4. Available Models List
- **URL**: `http://localhost:20213/v1/models`
- **Method**: GET
- **Description**: Returns a list of available search models


Query example:
```shell
curl -X POST "http://localhost:20213/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local",
    "messages": [
      {"role": "user", "content": "What are the treatment options for rosacea? (answer with reference only to data sources, but not to entities, relationships, or communities)"}
    ],             
    "stream": false
  }'
```

Return result:
```json
{"id":"chatcmpl-750577b87d0e4444910d513fdf64cb31","choices":[{"finish_reason":"stop","index":0,"logprobs":null,"message":{"content":"Rosacea treatment options include various methods, such as:\n\n*   **Tranexamic Acid**: Research shows that topical 3% tranexamic acid solution can improve erythema, reduce the number of inflammatory skin lesions, increase stratum corneum hydration, decrease TEWL values and pH values, and improve stratum corneum integrity and reduce patient response to lactic acid stimulation test [^Data:Sources(30)].\n*   **Doxycycline**: Doxycycline is a systemic treatment drug for rosacea with anti-inflammatory properties [^Data:Sources(35)].\n*   **Sunscreen**: Sunscreen can help protect the skin from sub-erythema doses of ultraviolet radiation [^Data:Sources(35)].\n\nThese treatments can help improve rosacea symptoms and promote the recovery of the skin barrier function.\n[^Data:Sources(35)]: [Sources: 35](http://127.0.0.1:20213/v1/references/local/sources/35)\n[^Data:Sources(30)]: [Sources: 30](http://127.0.0.1:20213/v1/references/local/sources/30)","refusal":null,"role":"assistant","annotations":null,"audio":null,"function_call":null,"tool_calls":null}}],"created":1743326931,"model":"local","object":"chat.completion","service_tier":null,"system_fingerprint":null,"usage":{"completion_tokens":-1,"prompt_tokens":0,"total_tokens":-1,"completion_tokens_details":null,"prompt_tokens_details":null}}
```


## Debugging Issues

If you encounter problems with server startup or search, you can use the provided `debug_server.py` script for debugging:

1. First, ensure the correct paths are set:
   ```python
   root = Path("/path/to/your/graphrag/project")
   data_dir = Path("/path/to/your/graphrag/project/output")
   ```

2. Run the debug script:
   ```shell
   python debug_server.py
   ```

3. The script will check:
   - If the configuration file is correctly loaded
   - If the required parquet files exist in the data directory
   - If the context and search engines can be successfully loaded

## GraphRAG Server Reference System Implementation Analysis

The reference system of the GraphRAG server works through the following key components:

### 1. LLM System Prompts

In the files under the `prompts` directory (such as `basic_search_system_prompt.txt` and `local_search_system_prompt.txt`), there are clear reference format guidelines for the large language model:

```
Points supported by data should list their data references as follows:
"This is an example sentence supported by multiple data references [^Data:<dataset name>(record id)] [^Data:<dataset name>(record id)]."
```

Here, `<dataset name>` can be one of the following types:
- Entities
- Relationships
- Sources
- Reports

The system prompts explicitly guide the LLM to use specific reference markers when generating answers, such as `[^Data:Entities(0)]`, where "Entities" is the data source type and "0" is the record ID.

### 2. Reference Pattern Detection

In the `webserver/utils/refer.py` file, a regular expression pattern is defined to identify references:

```python
pattern = re.compile(r'\[\^Data:(\w+?)\((\d+(?:,\d+)*)\)\]')
```

The `get_reference()` function uses this pattern to identify all references in the text and group them by data source type:

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

### 3. Converting References to Clickable Links

After the LLM generates an answer with reference markers, the `generate_ref_links()` function converts these markers into clickable footnote-style links:

```python
def generate_ref_links(data: Dict[str, Set[int]], index_id: str) -> str:
    base_url = f"{settings.website_address}/v1/references"
    lines = []
    for key, values in data.items():
        for value in values:
            lines.append(f'[^Data:{key.capitalize()}({value})]: [{key.capitalize()}: {value}]({base_url}/{index_id}/{key}/{value})')
    return "\n".join(lines)
```

These links point to specific API endpoints on the server for displaying detailed information about the references.

### 4. Response Processing

In `main.py`, both synchronous and streaming response handlers call the above functions to process references:

```python
reference = utils.get_reference(response)
if reference:
    response += f"\n{utils.generate_ref_links(reference, request.model)}"
```

This code adds the definitions of all footnote links at the bottom of the answer.

### 5. Reference Endpoint

The server has a dedicated endpoint for displaying reference data:

```python
@app.get("/v1/references/{index_id}/{datatype}/{id}", response_class=HTMLResponse)
```

This endpoint renders HTML templates (such as `entities_template.html`) to display detailed information for each reference when the user clicks on it.

## Actual Workflow

1. The user asks a question
2. The system sends the question to the LLM, along with system prompts instructing it to use special reference formats
3. The LLM generates an answer with reference markers (such as `[^Data:Entities(8)]`)
4. The server processes the answer, extracts all references, and adds clickable footnote links at the bottom
5. When the user clicks a reference link, they see a detailed view of that specific entity, relationship, source, or report

Example output:

```
# Leonardo da Vinci
    Leonardo da Vinci, born in 1452 in the town of Vinci near Florence, is widely celebrated as one of the most versatile geniuses of the Italian Renaissance. His full name was Leonardo di Ser Piero d'Antonio di Ser Piero di Ser Guido da Vinci, and he was the natural and first-born son of Ser Piero, a country notary [Data: Entities (0)]. Leonardo's contributions spanned various fields, including art, science, engineering, and philosophy, earning him the title of the most Universal Genius of Christian times [Data: Entities (8)].
``` 