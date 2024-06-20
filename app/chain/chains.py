#!/usr/bin/env python
# coding: utf-8
import asyncio
import os
import sys
from operator import itemgetter
from pathlib import Path

import cachetools
from langchain.llms import OpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from app.core.vectordb import retriever

sys.path.append(str(Path('.').resolve()))
from app.llm.huggingface_llm import get_model_tokenizer, HuggingFaceLLM

retrieval_chain_cache = cachetools.LRUCache(maxsize=128)
retrieval_chain_cache_lock = asyncio.Lock()
with_history_retrieval_cache = cachetools.LRUCache(maxsize=128)
with_history_retrieval_cache_lock = asyncio.Lock()


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


async def rag_chain(model_name):
    async with with_history_retrieval_cache_lock:
        if model_name not in with_history_retrieval_cache:
            if model_name in ["gpt-4", "gpt-4o"]:
                llm = ChatOpenAI(model=model_name, streaming=True)
            else:
                model, tokenizer = await get_model_tokenizer(model_name)
                llm = HuggingFaceLLM(model=model, tokenizer=tokenizer)
            prompt = ChatPromptTemplate.from_messages([
                MessagesPlaceholder(variable_name="history"),
                ('user', """Anwser the following question by context:
        
            question: {question}
        
            context: {context}        
            """)
            ])
            _internal_chain = (
                    RunnablePassthrough().assign(context=itemgetter('question')
                                                         | retriever.with_config(run_name="Docs")
                                                         | format_docs)
                    | prompt | llm.with_config(run_name="my_llm") | StrOutputParser()
            )
            with_history_retrieval_cache[model_name] = _internal_chain
        return with_history_retrieval_cache[model_name]
