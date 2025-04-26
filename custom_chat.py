from langchain_openai import ChatOpenAI
from typing import Iterator
from langchain_core.messages import BaseMessage, AIMessageChunk
from openai import OpenAI
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

class CustomChatOpenAI(ChatOpenAI):
    """自定义的ChatOpenAI类，支持reasoning_content处理"""

    def _create_client(self) -> OpenAI:
        return OpenAI(
            base_url=self.openai_api_base,
            api_key=self.openai_api_key.get_secret_value() if self.openai_api_key else None,
        )

    def _process_stream(
        self,
        messages,
        **kwargs,
    ) -> Iterator[AIMessageChunk]:
        client = self._create_client()
        stream = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
            **kwargs
        )

        in_think_tag = False
        think_closed = False

        for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                # 只允许出现一次 <think>...</think>
                if not in_think_tag and not think_closed:
                    yield AIMessageChunk(content="<think>\n")
                    in_think_tag = True
                if in_think_tag and not think_closed:
                    yield AIMessageChunk(content=delta.reasoning_content)
                # 如果已经关闭了 think，则忽略后续 reasoning_content

            elif hasattr(delta, 'content') and delta.content:
                if in_think_tag and not think_closed:
                    yield AIMessageChunk(content="\n</think>\n")
                    in_think_tag = False
                    think_closed = True
                yield AIMessageChunk(content=delta.content)

        # 如果流结束时 <think> 还没关闭，补一个
        if in_think_tag and not think_closed:
            yield AIMessageChunk(content="\n</think>\n")

    def stream(
        self,
        messages,
        **kwargs,
    ) -> Iterator[AIMessageChunk]:
        message_dicts = [
            {"role": "user" if msg.type == "human" else msg.type, "content": msg.content}
            for msg in messages
        ]
        return self._process_stream(message_dicts, **kwargs)

    def _generate(
        self,
        messages,
        **kwargs,
    ):
        client = self._create_client()
        message_dicts = [
            {"role": "user" if msg.type == "human" else msg.type, "content": msg.content}
            for msg in messages
        ]
        response = client.chat.completions.create(
            model=self.model_name,
            messages=message_dicts,
            stream=False,
            **kwargs
        )
        choice = response.choices[0]
        content = ""
        if hasattr(choice.message, "reasoning_content") and choice.message.reasoning_content:
            content += "<think>\n\n" + choice.message.reasoning_content + "\n</think>\n\n"
        if hasattr(choice.message, "content") and choice.message.content:
            content += choice.message.content
        message = AIMessage(content=content)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def invoke(
        self,
        input,
        **kwargs,
    ):
        if self.streaming:
            if isinstance(input, str):
                messages = [{"role": "user", "content": input}]
            else:
                messages = [
                    {"role": "user" if msg.type == "human" else msg.type, "content": msg.content}
                    for msg in input
                ]
            return self._process_stream(messages, **kwargs)
        else:
            if isinstance(input, str):
                messages = [BaseMessage(content=input, type="human")]
            else:
                messages = input
            result = self._generate(messages, **kwargs)
            return result.generations[0].message