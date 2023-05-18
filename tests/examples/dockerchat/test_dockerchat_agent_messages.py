from llmagent.agent.base import AgentConfig
from examples.dockerchat.docker_chat_agent import DockerChatAgent
from examples.dockerchat.dockerchat_agent_messages import (
    InformURLMessage,
    FileExistsMessage,
)

from llmagent.agent.message import AgentMessage
from llmagent.language_models.base import LLMConfig
from llmagent.cachedb.redis_cachedb import RedisCacheConfig
from typing import Optional
from functools import reduce
import pytest

cfg = AgentConfig(
    debug=False,
    vecdb=None,
    llm=LLMConfig(
        type="openai",
        chat_model="gpt-3.5-turbo",
        cache_config=RedisCacheConfig(fake=True),
    ),
)

NONE_MSG = "nothing to see here"

URL_MSG = "A messaging containing the word URL"

ASK_URL_RESPONSE = """You have not yet sent me the URL. 
            Start by asking for the URL, then confirm the URL with me"""

GOT_URL_RESPONSE = """
Ok, confirming the URL. 
"""

FILE_EXISTS_MSG = """
Ok, thank you.
{
'request': 'file_exists',
'filename': '___test.txt'
} 
Hope you can tell me!
"""

INFORM_URL_MSG = """
great, please see if this is the right URL:
{
'request': 'inform_url',
'url': 'https://github.com/openai/chatgpt-retrieval-plugin'
}
"""


class TestDockerChatAgent(DockerChatAgent):
    def handle_message_fallback(self, input_str: str = "") -> Optional[str]:
        # if URL not yet known, tell LLM to ask for it, unless this msg
        # contains the word URL
        if self.repo_path is None and "url" not in input_str.lower():
            return ASK_URL_RESPONSE

    def inform_url(self, msg: InformURLMessage) -> str:
        self.repo_path = msg.url
        return GOT_URL_RESPONSE


agent = TestDockerChatAgent(cfg)


def test_enable_message():
    agent.enable_message(FileExistsMessage)
    assert "file_exists" in agent.handled_classes
    assert agent.handled_classes["file_exists"] == FileExistsMessage

    agent.enable_message(InformURLMessage)
    assert "inform_url" in agent.handled_classes
    assert agent.handled_classes["inform_url"] == InformURLMessage


def test_disable_message():
    agent.enable_message(FileExistsMessage)
    agent.enable_message(InformURLMessage)

    agent.disable_message(FileExistsMessage)
    assert "file_exists" not in agent.handled_classes

    agent.disable_message(InformURLMessage)
    assert "inform_url" not in agent.handled_classes


@pytest.mark.parametrize("msg_cls", [InformURLMessage, FileExistsMessage])
def test_usage_instruction(msg_cls: AgentMessage):
    usage = msg_cls().usage_example()
    assert any(
        template in usage
        for template in reduce(
            lambda x, y: x + y, [ex.use_when() for ex in msg_cls.examples()]
        )
    )


def test_dockerchat_agent_handle_message():
    """
    Test whether messages are handled correctly, and that
    message enabling/disabling works as expected.
    """
    agent.enable_message(FileExistsMessage)
    agent.enable_message(InformURLMessage)
    # any msg before inform_url will result in an agent response
    # telling LLM to ask for URL
    assert agent.handle_message(NONE_MSG) == ASK_URL_RESPONSE
    assert agent.handle_message(FILE_EXISTS_MSG) == ASK_URL_RESPONSE
    assert agent.handle_message(INFORM_URL_MSG) == GOT_URL_RESPONSE

    agent.disable_message(FileExistsMessage)
    assert agent.handle_message(FILE_EXISTS_MSG) is None
