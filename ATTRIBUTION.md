# Attribution

## AI-Assisted Development

This project was primarily built and implemented by me, with AI tools used as a support resource for debugging, refinement, and improving development speed. I used Claude to help clarify implementation approaches, troubleshoot errors, improve UI polish, and iterate on prompts and documentation.

| Component                                                       | AI Tool Used       | How Used                                                                                                           |
| --------------------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------ |
| LangGraph pipeline architecture                                 | Claude (Anthropic) | Used for guidance while I implemented the graph structure, node flow, and state management                         |
| Claim extraction and arbitration prompts                        | Claude (Anthropic) | Used to brainstorm and refine prompt wording; final logic and integration were implemented by me                   |
| Frontend UI (`index.html`, `admin.html`, `app.js`, `style.css`) | Claude (Anthropic) | Used to enhance styling, improve layout, and debug UI behavior                                                     |
| Admin dashboard (`admin.html`)                                  | Claude (Anthropic) | Used for layout suggestions and debugging while I integrated the dashboard into the project                        |
| Safety classifier logic                                         | Claude (Anthropic) | Used to brainstorm guardrail approaches and debug implementation issues                                            |
| RAG pipeline (`rag.py`)                                         | Claude (Anthropic) | Used for guidance on chunking, embedding, and reranking structure; implementation was adapted and integrated by me |
| Evaluation framework (`eval_simulation.py`)                     | Claude (Anthropic) | Used to help structure test cases and debug evaluation logic                                                       |
| README.md and SETUP.md documentation                            | Claude (Anthropic) | Used to improve clarity, organization, and formatting                                                              |

Overall, AI was used as a development assistant rather than as the primary builder. I made the final technical decisions, integrated the components, tested functionality, and adapted the code to fit the goals of Spoon.

## Third-Party Libraries and Frameworks

| Library | License | Use |
|---|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | MIT | Backend API framework |
| [LangGraph](https://github.com/langchain-ai/langgraph) | MIT | Multi-step pipeline orchestration |
| [LangChain](https://github.com/langchain-ai/langchain) | MIT | LLM utility functions |
| [OpenAI Python SDK](https://github.com/openai/openai-python) | MIT | GPT-4o-mini API access |
| [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) | MIT | Claude API access |
| [Google GenAI Python SDK](https://github.com/google/generative-ai-python) | Apache 2.0 | Gemini API access |
| [pypdf](https://github.com/py-pdf/pypdf) | BSD-3-Clause | PDF text extraction |
| [pydantic](https://github.com/pydantic/pydantic) | MIT | Data validation and schemas |
| [uvicorn](https://github.com/encode/uvicorn) | BSD-3-Clause | ASGI server |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | BSD-3-Clause | Environment variable loading |
| [numpy](https://numpy.org/) | BSD-3-Clause | Embedding similarity computation |
| [Inter](https://rsms.me/inter/) (Google Fonts) | SIL OFL 1.1 | UI typography |
| [JetBrains Mono](https://www.jetbrains.com/lp/mono/) (Google Fonts) | SIL OFL 1.1 | Admin dashboard monospace font |

## APIs and External Services

| Service | Provider | Use |
|---|---|---|
| GPT-4o-mini | OpenAI | Model responses and safety classification |
| Claude Sonnet 4.6 / Haiku | Anthropic | Model responses, claim extraction, synthesis, arbitration |
| Gemini 2.5 Flash | Google | Model responses and convergence judgment |
| OpenAI Embeddings API | OpenAI | RAG document embeddings |
| Railway | Railway Corp | Cloud deployment |
