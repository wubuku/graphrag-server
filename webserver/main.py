import logging
import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from graphrag.query.context_builder.conversation_history import ConversationHistory
from graphrag.query.question_gen.local_gen import LocalQuestionGen
from graphrag.query.structured_search.basic_search.search import BasicSearch
from graphrag.query.structured_search.drift_search.search import DRIFTSearch
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.local_search.search import LocalSearch
from jinja2 import Template
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta

from webserver import gtypes
from webserver import search
from webserver import utils
from webserver.configs import settings
from webserver.utils import consts

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GraphRAG Server",
    description="A server for GraphRAG search engines with OpenAI API compatibility"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="webserver/static"), name="static")

basic_search = None
local_search = None
global_search = None
drift_search = None
question_gen = None


async def startup():
    """Initialization function when the application starts"""
    global local_search, global_search, question_gen, drift_search, basic_search
    
    try:
        root = Path(settings.root).resolve()
        data_dir = Path(settings.data).resolve()
        
        # Check if paths exist
        if not root.exists():
            logger.error(f"Root directory does not exist: {root}")
            return
            
        if not data_dir.exists():
            logger.error(f"Data directory does not exist: {data_dir}")
            return
        
        # Ensure settings.yaml file exists in the external directory
        config_path = root / "settings.yaml"
        if not config_path.exists():
            logger.error(f"settings.yaml file not found in root directory: {config_path}")
            logger.error(f"Please ensure there is a valid settings.yaml file in {root}")
            return
        
        try:
            config, data = await search.load_context(root, data_dir)
        except FileNotFoundError as e:
            logger.error(f"Failed to load settings: {str(e)}")
            return
        except Exception as e:
            logger.error(f"Error loading context: {str(e)}", exc_info=True)
            return
        
        # Check if necessary data files exist and have data
        required_data = ["entities", "text_units", "community_reports"]
        missing_files = []
        
        for file_name in required_data:
            if file_name not in data or data[file_name].empty:
                missing_files.append(file_name)
        
        if missing_files:
            logger.error(f"Missing required data files: {', '.join(missing_files)}. Check your data directory: {data_dir}")
            return
        
        # Initialize search engines
        local_search = await search.load_local_search_engine(config, data)
        global_search = await search.load_global_search_engine(config, data)
        drift_search = await search.load_drift_search_engine(config, data)
        basic_search = await search.load_basic_search_engine(config, data)
        
        logger.info("All search engines initialized successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)


# Using the old on_event instead of lifespan
@app.on_event("startup")
async def startup_event():
    await startup()


@app.get("/")
async def index():
    html_file_path = os.path.join("webserver", "templates", "index.html")
    with open(html_file_path, "r", encoding="utf-8") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)


@app.middleware("http")
async def check_search_engines(request: Request, call_next):
    """Check if search engines are initialized, if not, try to initialize them again"""
    if request.url.path.startswith("/v1/chat/completions") and not all([local_search, global_search, drift_search, basic_search]):
        await startup()
        if not all([local_search, global_search, drift_search, basic_search]):
            return JSONResponse(
                status_code=503,
                content={"error": "Search engines are not initialized. Check server logs for details."}
            )
    
    response = await call_next(request)
    return response


async def handle_sync_response(request, search, conversation_history):
    result = await search.asearch(request.messages[-1].content, conversation_history=conversation_history)
    if isinstance(search, DRIFTSearch):
        response = result.response
        response = response["nodes"][0]["answer"]
    else:
        response = result.response
    reference = utils.get_reference(response)
    if reference and settings.show_references:
        response += f"\n{utils.generate_ref_links(reference, request.model)}"
    from openai.types.chat.chat_completion import Choice
    completion = ChatCompletion(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        created=int(time.time()),
        model=request.model,
        object="chat.completion",
        choices=[
            Choice(
                index=0,
                finish_reason="stop",
                message=ChatCompletionMessage(
                    role="assistant",
                    content=response
                )
            )
        ],
        usage=CompletionUsage(
            completion_tokens=-1,
            prompt_tokens=result.prompt_tokens,
            total_tokens=-1
        )
    )
    return JSONResponse(content=jsonable_encoder(completion))


async def handle_stream_response(request, search, conversation_history):
    async def wrapper_astream_search():
        token_index = 0
        chat_id = f"chatcmpl-{uuid.uuid4().hex}"
        full_response = ""
        async for token in search.astream_search(request.messages[-1].content, conversation_history):  # Call the original generator
            if token_index == 0:
                token_index += 1
                continue

            chunk = ChatCompletionChunk(
                id=chat_id,
                created=int(time.time()),
                model=request.model,
                object="chat.completion.chunk",
                choices=[
                    Choice(
                        index=token_index - 1,
                        finish_reason=None,
                        delta=ChoiceDelta(
                            role="assistant",
                            content=token
                        )
                    )
                ]
            )
            yield f"data: {chunk.json()}\n\n"
            token_index += 1
            full_response += token

        content = ""
        reference = utils.get_reference(full_response)
        if reference and settings.show_references:
            content = f"\n{utils.generate_ref_links(reference, request.model)}"
        finish_reason = 'stop'
        chunk = ChatCompletionChunk(
            id=chat_id,
            created=int(time.time()),
            model=request.model,
            object="chat.completion.chunk",
            choices=[
                Choice(
                    index=token_index,
                    finish_reason=finish_reason,
                    delta=ChoiceDelta(
                        role="assistant",
                        # content=result.context_data["entities"].head().to_string()
                        content=content
                    )
                ),
            ],
        )
        yield f"data: {chunk.json()}\n\n"
        yield f"data: [DONE]\n\n"

    return StreamingResponse(wrapper_astream_search(), media_type="text/event-stream")


@app.post("/v1/chat/completions")
async def chat_completions(request: gtypes.ChatCompletionRequest):
    if not all([local_search, global_search, drift_search, basic_search]):
        logger.error("Search engines are not initialized. Check server logs for details.")
        raise HTTPException(status_code=503, detail="Search engines are not initialized. Check server logs for details.")

    try:
        history = request.messages[:-1]
        conversation_history = ConversationHistory.from_list([message.dict() for message in history])

        if request.model == consts.INDEX_GLOBAL:
            search_engine = global_search
        elif request.model == consts.INDEX_LOCAL:
            search_engine = local_search
        elif request.model == consts.INDEX_DRIFT:
            search_engine = drift_search
        else:
            search_engine = basic_search

        if not request.stream:
            return await handle_sync_response(request, search_engine, conversation_history)
        else:
            return await handle_stream_response(request, search_engine, conversation_history)
    except Exception as e:
        logger.error(msg=f"chat_completions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/advice_questions", response_model=gtypes.QuestionGenResult)
async def get_advice_question(request: gtypes.ChatQuestionGen):
    raise NotImplementedError("get_advice_question is not implemented since version 1.1.2")
    if request.model == consts.INDEX_LOCAL:
        local_context = await switch_context(index=request.model)
        question_gen.context_builder = local_context
    else:
        raise NotImplementedError(f"model {request.model} is not supported")
    question_history = [message.content for message in request.messages if message.role == "user"]
    candidate_questions = await question_gen.agenerate(
        question_history=question_history, context_data=None, question_count=5
    )
    # the original generated question is "- what about xxx?"
    questions: list[str] = [question.removeprefix("-").strip() for question in candidate_questions.response]
    resp = gtypes.QuestionGenResult(questions=questions,
                                    completion_time=candidate_questions.completion_time,
                                    llm_calls=candidate_questions.llm_calls,
                                    prompt_tokens=candidate_questions.prompt_tokens)
    return resp


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring systems"""
    try:
        # Basic health check - verify search engines are initialized
        if not all([local_search, global_search, drift_search, basic_search]):
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "message": "Search engines not initialized"}
            )
        
        # Return healthy status
        return JSONResponse(
            status_code=200,
            content={"status": "healthy", "message": "Service is running"}
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": str(e)}
        )


@app.get("/v1/models", response_model=gtypes.ModelList)
async def list_models():
    models: list[gtypes.Model] = [
        gtypes.Model(id=consts.INDEX_LOCAL, object="model", created=1644752340, owned_by="graphrag"),
        gtypes.Model(id=consts.INDEX_GLOBAL, object="model", created=1644752340, owned_by="graphrag"),
        gtypes.Model(id=consts.INDEX_DRIFT, object="model", created=1644752340, owned_by="graphrag"),
        gtypes.Model(id=consts.INDEX_BASIC, object="model", created=1644752340, owned_by="graphrag")
    ]
    return gtypes.ModelList(data=models)


@app.get("/v1/references/{index_id}/{datatype}/{id}", response_class=HTMLResponse)
async def get_reference(index_id: str, datatype: str, id: str):
    if not os.path.exists(settings.data):
        raise HTTPException(status_code=404, detail=f"Data directory {settings.data} not found")
        
    if datatype not in ["entities", "sources", "reports", "relationships", "documents"]:
        raise HTTPException(status_code=404, detail=f"Datatype {datatype} not supported")

    # Debug mode can be enabled manually if needed for troubleshooting
    # But now that we've fixed the issues, we don't need to automatically enable it for reports
    original_debug_mode = None
    # Uncomment the following block if you need to troubleshoot issues again
    # if datatype == "reports":
    #     try:
    #         from webserver.search.indexdata import enable_debug_for_request, restore_debug_mode
    #         original_debug_mode = enable_debug_for_request()
    #         logger.info("Temporarily enabled debug mode for report request")
    #     except Exception as debug_error:
    #         logger.warning(f"Failed to enable debug mode: {debug_error}")

    try:
        # Basic logging
        logger.info(f"Retrieving {datatype} with ID {id} from {settings.data}")
        
        data = await search.get_index_data(settings.data, datatype, id)
        
        # Log successful data retrieval (no need for detailed logging now that issues are resolved)
        logger.info(f"Successfully retrieved {datatype} data with ID {id}")
        
        html_file_path = os.path.join("webserver", "templates", f"{datatype}_template.html")
        with open(html_file_path, 'r') as file:
            html_content = file.read()
        template = Template(html_content)
        html_content = template.render(data=data)
        
        # Restore original debug mode if it was changed
        if original_debug_mode is not None:
            try:
                from webserver.search.indexdata import restore_debug_mode
                restore_debug_mode(original_debug_mode)
                logger.info("Restored original debug mode")
            except Exception as restore_error:
                logger.warning(f"Failed to restore debug mode: {restore_error}")
                
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error getting reference data: {e}", exc_info=True)
        
        # Enhanced error information for debugging CommunityReport issues
        if datatype == "reports" and "CommunityReport.__init__()" in str(e):
            # Print detailed information about the error
            error_msg = f"GraphRAG data model error: {str(e)}\n"
            error_msg += "This is likely due to a change in the CommunityReport class in GraphRAG 2.1.0."
            logger.error(error_msg)
        
        # Restore original debug mode if it was changed and we had an error
        if original_debug_mode is not None:
            try:
                from webserver.search.indexdata import restore_debug_mode
                restore_debug_mode(original_debug_mode)
                logger.info("Restored original debug mode after error")
            except Exception as restore_error:
                logger.warning(f"Failed to restore debug mode: {restore_error}")
                
        raise HTTPException(status_code=500, detail=f"Error getting reference data: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=settings.server_port)
