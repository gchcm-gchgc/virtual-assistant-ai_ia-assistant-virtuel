import os
from openai import AsyncOpenAI
import json
import time

from typing import Tuple, AsyncGenerator
from typing import AsyncGenerator
from typing import List, Dict

import asyncio
from utils import Utils
from queries import Queries
from databases import Databases
from embeddings import Embeddings
from prompts import REPHRASE_PROMPT, ANSWER_PROMPT, ANSWER_SYSTEM_MSG
from mappers import Mappers
from langdetect import detect

class ChatBot:
    """
    A chatbot class that handles conversation management, language detection, and question answering.

    This class integrates various components like database access, embeddings, and language models
    to provide a comprehensive chatbot functionality.

    Attributes:
        vector_search_result_size (int): Number of results to return from vector search.
        rephrase_prompt_history_size (int): Number of historical messages to consider for rephrasing.
        answers_prompt_history_size (int): Number of historical messages to consider for answering.
        model_name (str): Name of the language model to use.
        client (AsyncOpenAI): AsyncOpenAI client for API calls.
        chat_histories (Dict[str, Dict[str, Any]]): Storage for chat histories by session ID.
        session_timeout (int): Timeout duration for chat sessions in seconds.
        utils (Utils): Utility instance.
        dbs (Databases): Database connections instance.
        mappers (Mappers): Data mappers instance.
        queries (Queries): Database queries instance.
        embeddings (Embeddings): Text embeddings instance.
    """
    def __init__(
            self,
            vector_search_result_size=10, rephrase_prompt_history_size=3, answers_prompt_history_size=5,
            rephrase_model_name="hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4",
            answer_model_name = "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
            rephrase_model_base_url="http://localhost:10000/v1", 
            answer_model_base_url="http://localhost:10005/v1",
            api_key=os.environ['TOKEN'],
            session_timeout=3600*24,
        ):
        self.vector_search_result_size = vector_search_result_size
        self.rephrase_prompt_history_size = rephrase_prompt_history_size
        self.answers_prompt_history_size = answers_prompt_history_size
        self.rephrase_model_name = rephrase_model_name
        self.answer_model_name = answer_model_name
        self.rephrase_model_client = AsyncOpenAI(
            base_url=rephrase_model_base_url,
            api_key=api_key,
        )
        self.answer_model_client = AsyncOpenAI(
            base_url=answer_model_base_url,
            api_key=api_key,
        )
        self.chat_histories = {}
        self.session_timeout = session_timeout
        self.utils = Utils()
        self.dbs = Databases(utils=self.utils)
        self.mappers = Mappers()
        self.queries = Queries()
        self.embeddings = Embeddings()
        self.logs_db_name = os.environ['MONGO_COLLECTION_LOG_NAME']

    def _get_chat_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Retrieve the chat history for a given session ID.

        Arguments:
        session_id : str : The unique identifier for the chat session

        Returns:
        list : The chat history for the given session
        """
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = {"history": [], "last_update": time.time()}
        return self.chat_histories[session_id]["history"]
    
    def _update_chat_history(self, session_id: str, user_message: str, assistant_message: str) -> None:
        """
        Update the chat history for a given session with new messages.

        Arguments:
        session_id : str : The unique identifier for the chat session
        user_message : str : The message from the user
        assistant_message : str : The response from the assistant
        """
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = {"history": [], "last_update": time.time()}
        
        self.chat_histories[session_id]["history"].append({"user": user_message, "assistant": assistant_message})
        self.chat_histories[session_id]["last_update"] = time.time()

        # Cleanup old sessions
        self._cleanup_old_sessions()


    def _cleanup_old_sessions(self) -> None:
        """
        Remove expired chat sessions based on the session_timeout.
        """
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, data in self.chat_histories.items()
            if current_time - data["last_update"] > self.session_timeout
        ]
        for session_id in expired_sessions:
            del self.chat_histories[session_id]

    def _detect_language(self, question: str) -> str:
        return detect(question)

    async def _common_chat_operations(self, question: str, session_id: str, case_id: int, act_rec: int):
        lang = self._detect_language(question)
        chat_history = self._get_chat_history(session_id)
        rephrase_prompt = self._get_rephrase_prompt(question, chat_history)
        rephrased_question = await self._rephrase(rephrase_prompt)

        question_emb = self.embeddings.mpnet.get_embeddings(rephrased_question)
        vector_search_results = await self.queries.mongo.multi_collection_vector_search(self.dbs.mongo, question_emb, k=self.vector_search_result_size)

        context = ""
        need_case_details = False
        for ele in vector_search_results:
            context += f"Origin: {ele['origin']}\nContent: {ele['content']}\n---"
            if "case_details" in ele['collection']:
                need_case_details = True

        # Check if case details needed
        if need_case_details:
            case_details = vars(self.queries.postgres.get_cases_by_id_and_act_rec(self.dbs.postgres, case_id, act_rec))
            case_details_mapped = self.mappers.case_details.get_data_mapped(case_details, lang)
            context += '\n\nCase Details:\n' + str(case_details_mapped)

        answer_prompt = self._get_answer_prompt(question, context, chat_history)
        
        return answer_prompt, chat_history

    async def chat(self, question: str, session_id: str, case_id: int, act_rec: int) -> AsyncGenerator[str, None]:
        answer_prompt, chat_history = await self._common_chat_operations(question, session_id, case_id, act_rec)

        final_answer = []
        origin_task = asyncio.create_task(self._extract_origin(answer_prompt))

        async for chunk in self._process_answer(answer_prompt):
            final_answer.append(chunk)
            yield chunk

        # Finalize processing after streaming is complete
        final_answer_str = "".join(final_answer)
        origin = await origin_task

        # Update session data and chat history
        self._update_session_data(session_id, question, final_answer_str, origin)
        self._update_chat_history(session_id, question, final_answer_str)

    async def _process_answer(self, answer_prompt) -> AsyncGenerator[str, None]:
        origin_flag = False

        async for response_chunk in self._answer(answer_prompt):
            if not origin_flag:
                if "<<" in response_chunk:
                    origin_flag = True
                    parts = response_chunk.split("<<", 1)
                    yield parts[0]
                else:
                    yield response_chunk

    async def _extract_origin(self, answer_prompt) -> str:
        origin = ""
        origin_flag = False

        async for response_chunk in self._answer(answer_prompt):
            if not origin_flag:
                if "<<" in response_chunk:
                    origin_flag = True
                    origin = response_chunk.split("<<", 1)[1]
            else:
                origin += response_chunk

        return self._clean_origin(origin)

    def _clean_origin(self, origin: str) -> str:
        origin = origin.strip()
        
        if origin.startswith("STOP>>"):
            origin = origin[6:].strip()
        
        if "Origin: " in origin:
            origin = origin.split("Origin: ", 1)[1].strip()
        
        if origin.endswith(">>"):
            origin = origin[:-2].strip()

        return origin

    async def _update_session_data(self, session_id: str, question: str, final_answer: str, origin: str):
        await self.utils.logs.upsert_session_data(
            db=self.dbs.mongo.db,
            collection_name=self.logs_db_name,
            session_id=int(session_id),
            origin=origin,
            question=question,
            answer=final_answer
        )

    async def chat_prompt_answer(self, question: str, session_id: str, case_id: int, act_rec: int) -> Dict[str, str]:
        answer_prompt, chat_history = await self._common_chat_operations(question, session_id, case_id, act_rec)

        final_answer = ""
        async for response_chunk in self._answer(answer_prompt):
            final_answer += response_chunk

        self._update_chat_history(session_id, question, final_answer)
        return {"prompt": str(answer_prompt), "response": final_answer}

    async def _rephrase(self, prompt: List[Dict[str, str]]) -> str:
        completion = await self.rephrase_model_client.chat.completions.create(
            model=self.rephrase_model_name,
            messages=prompt,
            temperature=0.05,
            top_p=0.95,
            max_tokens=500,
            stream=False,
        )
        return completion.choices[0].message.content.strip()
        

    async def _answer(self, prompt: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        stream = await self.answer_model_client.chat.completions.create(
            model=self.answer_model_name,
            messages=prompt,
            temperature=0.05,
            top_p=0.95,
            max_tokens=4096,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                yield content
    

    def _get_answer_prompt(self, current_question: str, context: str, chat_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        chat_history_str = json.dumps(
            chat_history[-self.answers_prompt_history_size:], 
            indent=2, ensure_ascii=False)
        messages = [
            {"role": "system", "content": ANSWER_SYSTEM_MSG},
            {"role": "user", "content": ANSWER_PROMPT.format(context, chat_history_str, current_question)}
        ]
        return messages
    
    
    def _get_rephrase_prompt(self, current_question: str, chat_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        chat_history_str = json.dumps(
            chat_history[-self.answers_prompt_history_size:], 
            indent=2, ensure_ascii=False)
        messages = [
            {"role": "user", "content": REPHRASE_PROMPT.format(chat_history_str, current_question)}
        ]
        return messages