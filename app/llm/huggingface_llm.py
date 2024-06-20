#!/usr/bin/env python
# coding: utf-8

# implements a custom llm


import asyncio
import functools
import os
import platform
from pathlib import Path
from threading import Thread
from typing import Optional, List, Any, Iterator, Mapping, AsyncIterator

import cachetools
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from langchain_core.language_models import LLM
from langchain_core.outputs import GenerationChunk, LLMResult, Generation
from overrides import overrides
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import TextIteratorStreamer

from app.core.config import setting



model_tokenizer_cache = cachetools.LRUCache(maxsize=128)
lock = asyncio.Lock()


async def get_model_tokenizer(model_name):
    async with lock:
        if model_name not in model_tokenizer_cache:
            loop = asyncio.get_running_loop()
            model = await loop.run_in_executor(None, functools.partial(AutoModelForCausalLM.from_pretrained,
                                                                       os.path.join(setting.MODEL_DIR, model_name),
                                                                       torch_dtype="auto", trust_remote_code=True,
                                                                       device_map=setting.DEVICE,
                                                                       offload_folder=str(Path.home() / 'offload_dir')))
            tokenizer = await loop.run_in_executor(None, functools.partial(AutoTokenizer.from_pretrained,
                                                                           os.path.join(setting.MODEL_DIR, model_name),
                                                                           trust_remote_code=True))
            model_tokenizer_cache[model_name] = (model, tokenizer)
        return model_tokenizer_cache[model_name]


class HuggingFaceLLM(LLM):
    model: Any
    tokenizer: Any

    def prepare_model_inputs(self, prompts: List[str], padding: bool = False):
        # convert str to input_ids
        input_texts = []
        for prompt in prompts:
            messages = [
                {"role": "system", "content": "You are a helpful assistant"},
                {'role': 'user', 'content': prompt}
            ]
            input_texts.append(self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True))
        model_inputs = self.tokenizer(input_texts, padding=padding, return_tensors='pt').to(setting.DEVICE)
        return model_inputs

    def _call(self, prompt: str, stop: Optional[List[str]] = None,
              run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs) -> str:
        model_inputs = self.prepare_model_inputs([prompt])
        # model forward pass
        generated_ids = self.model.generate(model_inputs.input_ids, max_new_tokens=512)
        generated_ids = [generated_ids[len(input_ids):] for input_ids, generated_ids in
                         zip(model_inputs.input_ids, generated_ids)]
        # decode generation_ids
        output_text = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return output_text

    @overrides
    def _generate(
            self,
            prompts: List[str],
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> LLMResult:
        model_inputs = self.prepare_model_inputs(prompts, padding=True)
        # model forward pass
        generated_ids = self.model.generate(model_inputs.input_ids, max_new_tokens=512)
        generated_ids = [generated_ids[len(input_ids):] for input_ids, generated_ids in
                         zip(model_inputs.input_ids, generated_ids)]
        # decode generation_ids
        output_texts = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)
        return LLMResult(generations=[[Generation(text=output_text)] for output_text in output_texts])

    async def _agenerate(
            self,
            prompts: List[str],
            stop: Optional[List[str]] = None,
            run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> LLMResult:
        return self._generate(prompts, stop, run_manager, **kwargs)

    def _stream(self,
                prompt: str,
                stop: Optional[List[str]] = None,
                run_manager: Optional[CallbackManagerForLLMRun] = None,
                **kwargs: Any
                ) -> Iterator[GenerationChunk]:
        model_inputs = self.prepare_model_inputs([prompt])
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True)
        generation_kwargs = dict(model_inputs, streamer=streamer, max_new_tokens=512)
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        for new_text in streamer:
            run_manager.on_llm_new_token(new_text, chunk=GenerationChunk(text=new_text))
            yield GenerationChunk(text=new_text)

    async def _astream(self,
                       prompt: str,
                       stop: Optional[List[str]] = None,
                       run_manager: Optional[CallbackManagerForLLMRun] = None,
                       **kwargs: Any
                       ) -> AsyncIterator[GenerationChunk]:
        model_inputs = self.prepare_model_inputs([prompt])
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True)
        generation_kwargs = dict(model_inputs, streamer=streamer, max_new_tokens=512)
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, functools.partial(self.model.generate, **generation_kwargs))
        # iterate a blocking iterator with asyncio and next
        while True:
            DONE = object()
            new_text = await loop.run_in_executor(None, next, streamer, DONE)
            if new_text is DONE:
                break
            await run_manager.on_llm_new_token(new_text, chunk=GenerationChunk(text=new_text))
            yield GenerationChunk(text=new_text)

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {
            'model_name': 'CustomLLM'
        }

    @property
    def _llm_type(self) -> str:
        return "custom"
