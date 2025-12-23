# 📚 Knowledge Assistant

一个企业级个人知识助手Web应用，基于Python FastAPI构建，集成RAG（检索增强生成）、语义搜索、智能标签等AI功能。

## ✨ 核心特性

- **📄 文档管理** - 支持Markdown、PDF、DOCX等多种格式，类Obsidian双向链接
- **🔍 语义搜索** - 基于向量嵌入的智能搜索，比关键词更懂你的意图
- **💬 RAG对话** - 基于知识库的智能问答，流式响应，引用来源
- **🏷️ 智能标签** - AI自动生成文档标签和摘要
- **🕸️ 知识图谱** - 可视化文档间的关联关系
- **🔄 混合LLM** - 支持云端API（OpenAI/Claude/通义千问）和本地模型（Ollama/Llama）

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vanilla JS)                      │
├─────────────────────────────────────────────────────────────┤
│                    FastAPI Application                        │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Document   │     Chat     │    Search    │     System     │
│   Routes     │    Routes    │    Routes    │    Routes      │
├──────────────┴──────────────┴──────────────┴────────────────┤
│                   Application Layer                          │
│            (Use Cases / Business Logic)                      │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   LLM        │  Embedding   │   Vector     │   Document     │
│   Service    │   Service    │   Store      │   Processor    │
│  (LiteLLM)   │  (BGE-M3)    │  (Chroma)    │   (Chunking)   │
├──────────────┴──────────────┴──────────────┴────────────────┤
│                    Infrastructure Layer                       │
│              SQLAlchemy + SQLite/PostgreSQL                  │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| **框架** | FastAPI 0.109+, Pydantic 2.x |
| **LLM** | LiteLLM (统一接口), Ollama, OpenAI, Anthropic |
| **嵌入** | BGE-M3 (多语言), Sentence Transformers |
| **向量库** | ChromaDB (持久化) |
| **数据库** | SQLAlchemy 2.0 + SQLite/PostgreSQL |
| **前端** | Vanilla JS, Marked.js, Highlight.js |

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 克隆项目
git clone https://github.com/yourusername/knowledge-assistant.git
cd knowledge-assistant

# 复制环境变量
cp .env.example .env

# 启动服务
docker-compose up -d

# 拉取Ollama模型（首次运行）
docker exec -it knowledge-ollama ollama pull llama3.2
docker exec -it knowledge-ollama ollama pull bge-m3

# 访问应用
open http://localhost:8000/app
```

### 方式二：本地开发

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制环境变量
cp .env.example .env

# 启动Ollama（需要预先安装）
ollama serve &
ollama pull llama3.2

# 启动应用
python main.py
```

### 方式三：使用云端API

编辑 `.env` 文件：

```env
# ===== OpenAI =====
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-key

# ===== Anthropic Claude =====
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your-key

# ===== 阿里通义千问 =====
DEFAULT_LLM_PROVIDER=qwen
DEFAULT_LLM_MODEL=qwen-turbo
QWEN_API_KEY=sk-your-qwen-key

# ===== DeepSeek =====
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-your-deepseek-key
```

> 💡 **提示**：可以同时配置多个API Key，系统会根据 `DEFAULT_LLM_PROVIDER` 选择默认使用哪个，并支持自动降级到其他可用模型。

## 📖 API文档

启动应用后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 核心API端点

| 方法 | 端点 | 描述 |
|------|------|------|
| `POST` | `/api/documents` | 创建文档 |
| `GET` | `/api/documents` | 获取文档列表 |
| `POST` | `/api/documents/upload` | 上传文件 |
| `POST` | `/api/chat/conversations` | 创建对话 |
| `POST` | `/api/chat/conversations/{id}/messages` | 发送消息 |
| `POST` | `/api/chat/conversations/{id}/messages/stream` | 流式对话 |
| `POST` | `/api/chat/search` | 语义搜索 |

## 📁 项目结构

```
knowledge-assistant/
├── config/                 # 配置管理
│   └── settings.py
├── src/
│   ├── domain/             # 领域层（实体、接口）
│   │   ├── entities/
│   │   └── repositories/
│   ├── application/        # 应用层（用例）
│   │   └── use_cases/
│   ├── infrastructure/     # 基础设施层
│   │   ├── database/       # SQLAlchemy
│   │   ├── llm/            # LiteLLM服务
│   │   ├── embedding/      # 嵌入服务
│   │   ├── vector_store/   # Chroma
│   │   └── document_processing/
│   └── presentation/       # 展示层（API）
│       ├── api/
│       └── schemas/
├── static/                 # 前端静态文件
├── tests/                  # 测试
├── main.py                 # 应用入口
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## ⚙️ 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_LLM_PROVIDER` | ollama | LLM提供商 (ollama/openai/anthropic/qwen) |
| `DEFAULT_LLM_MODEL` | llama3.2 | 默认模型 |
| `EMBEDDING_PROVIDER` | local | 嵌入提供商 (local/openai/ollama) |
| `EMBEDDING_MODEL` | BAAI/bge-m3 | 嵌入模型 |
| `CHUNK_SIZE` | 500 | 文档分块大小 |
| `ENABLE_AUTO_TAGGING` | true | 启用AI自动标签 |
| `ENABLE_SUMMARIZATION` | true | 启用AI自动摘要 |

### 支持的LLM模型

**云端API：**
- OpenAI: gpt-4o, gpt-4o-mini, gpt-3.5-turbo
- Anthropic: claude-3-5-sonnet, claude-3-haiku
- 通义千问: qwen-turbo, qwen-plus
- DeepSeek: deepseek-chat

**本地模型（Ollama）：**
- llama3.2, llama3.1
- qwen2.5, qwen2
- deepseek-v2
- mistral, mixtral

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行带覆盖率
pytest --cov=src --cov-report=html

# 仅运行单元测试
pytest tests/unit/
```

## 🔒 安全注意事项

- 生产环境请修改 `SECRET_KEY`
- 配置适当的CORS策略
- 建议使用PostgreSQL替代SQLite
- API密钥不要提交到版本控制

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [LiteLLM](https://github.com/BerriAI/litellm)
- [ChromaDB](https://www.trychroma.com/)
- [Ollama](https://ollama.ai/)
- [BGE-M3](https://huggingface.co/BAAI/bge-m3)