# GraphRAG Server
## Features
- 添加了Web服务器，以支持真即时流式输出。
- 添加了建议问题API。
- 添加了实体或者关系等链接到输出中，你可以直接点击访问参考实体、关系、数据源或者报告。
- 支持任意兼容OpenAI大模型桌面应用或者Web应用UI接入。
- 增加Docker构建
- 最新版本Graphrag 1.1.2

![image](https://github.com/user-attachments/assets/c251d434-4925-4012-88e7-f3b2ff40471f)


![image](https://github.com/user-attachments/assets/ab7a8d2e-aeec-4a0c-afb9-97086b9c7b2a)

# 如何安装How to install
你可以使用Docker安装，也可以拉取本项目使用。You can install by docker or pull this repo.
## 拉取源码 Pull the source code
- 克隆本项目 Clone the repo
```
git clone https://github.com/KylinMountain/graphrag-server.git
cd graphrag-server
```
- 建立虚拟环境 Create virtual env
```
conda create -n graphrag python=3.10
conda activate graphrag
```

- 安装依赖 Install dependencies
```
pip install -r requirements.txt
```

- 初始化GraphRAG Initialize GraphRAG
```
graphrag init --root .
```
- 创建input文件夹 Create Input Foler

```
mkdir input
```

- 配置settings.yaml Config settings.yaml

按照GraphRAG官方配置文档配置 [GraphRAG Configuration](https://microsoft.github.io/graphrag/posts/config/json_yaml/)

- 索引

在配置好settings.yaml后，运行以下命令进行索引。After config the settings.yaml, run the following command to index.
```
graphrag index --root .
```
- 配置webserver Config webserver

你可能需要修改`webserver/configs/settings.py`配置以下设置，但默认即可支持本地运行。 You may need config the following item, but you can use the default param.
```yaml
    server_port: int = 20213
    cors_allowed_origins: list = ["*"]  # Edit the list to restrict access.
    data: str = ("./output")
    community_level: int = 2
    dynamic_community_selection: bool = False
    response_type: str = "Multiple Paragraphs"
```
- 启动web server
```bash
python -m webserver.main
```
更多的参考配置，可以访问[公众号文章](https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzI0OTAzNTEwMw==&action=getalbum&album_id=3429606151455670272&uin=&key=&devicetype=iMac+MacBookPro17%2C1+OSX+OSX+14.4+build(23E214)&version=13080710&lang=zh_CN&nettype=WIFI&ascene=0&fontScale=100)和[B站视频](https://www.bilibili.com/video/BV113v8e6EZn)

## 使用Docker安装 Install by docker
- 拉取镜像 pull the docker image
```
docker pull kylinmountain/graphrag-server:0.3.1
```
启动 Start
在启动前 你可以创建output、input、prompts和settings.yaml等目录或者文件
Before start, you can create output、input、prompts and settings.yaml etc.
```
docker run -v ./output:/app/output \
           -v ./input:/app/input \
           -v ./prompts:/app/prompts \
           -v ./settings.yaml:/app/settings.yaml \
           -v ./lancedb:/app/lancedb -p 20213:20213 kylinmountain/graphrag-server:0.3.1

```
- 索引 Index
```
docker run kylinmountain/graphrag-server:0.3.1 python -m graphrag.index --root .
```
