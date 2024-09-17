# Functional Guides
The Poe bot query API allows creators to invoke other bots on Poe (which includes bots created by Poe like GPT-3.5-Turbo and Claude-Instant and bots created by other creators) and this access is provided for free so that creators do not have to worry about LLM costs. For every user message, server bot creators get to make up to ten calls to another bot of their choice.

Declare dependency in your PoeBot class
You have to declare your bot dependencies using the settings endpoint.

Python

async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
    return fp.SettingsResponse(server_bot_dependencies={"GPT-3.5-Turbo": 1})
In your get_response handler, use the stream_request function to invoke any bot you want. The following is an example where we forward the user's query to GPT-3.5-Turbo and return the result.

Python

async def get_response(
    self, request: fp.QueryRequest
) -> AsyncIterable[fp.PartialResponse]:
    async for msg in fp.stream_request(
        request, "GPT-3.5-Turbo", request.access_key
    ):
        yield msg
The final code (including the setup code you need to host this on Modal) that goes into your main.py is as follows:

Python

from __future__ import annotations
from typing import AsyncIterable
from modal import Image, Stub, asgi_app
import fastapi_poe as fp

class GPT35TurboBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        async for msg in fp.stream_request(
            request, "GPT-3.5-Turbo", request.access_key
        ):
            yield msg

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={"GPT-3.5-Turbo": 1})
    
REQUIREMENTS = ["fastapi-poe==0.0.36"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("turbo-example-poe")

@stub.function(image=image)
@asgi_app()
def fastapi_app():
    bot = GPT35TurboBot()
    app = fp.make_app(bot, allow_without_key=True)
    return app
Now, before you use the bot, you will have to follow the steps listed here in order to get Poe to fetch your bots settings (one time only after you override get_settings). Once that is done, try to use your bot on Poe and you will see the response from GPT-3.5-Turbo. You can modify the code and do more interesting things (like apply some business logic on the response or conditionally call another API).



Using OpenAI function calling
The Poe API allows you to use OpenAI function calling when accessing OpenAI models. In order to use this feature, you will simply need to provide a tools list which contains objects describing your function and an executables list which contains functions that correspond to the tools list. The following is an example.

Python

def get_current_weather(location, unit="fahrenheit"):
    """Get the current weather in a given location"""
    if "tokyo" in location.lower():
        return json.dumps({"location": "Tokyo", "temperature": "11", "unit": unit})
    elif "san francisco" in location.lower():
        return json.dumps(
            {"location": "San Francisco", "temperature": "72", "unit": unit}
        )
    elif "paris" in location.lower():
        return json.dumps({"location": "Paris", "temperature": "22", "unit": unit})
    else:
        return json.dumps({"location": location, "temperature": "unknown"})


tools_executables = [get_current_weather]

tools_dict_list = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]
tools = [fp.ToolDefinition(**tools_dict) for tools_dict in tools_dict_list]
Additionally, you will need to define a dependency of two calls on an OpenAI model of your choice (in this case, the GPT-3.5-Turbo). You need a dependency of two because as part of the OpenAI function calling flow, you need to call OpenAI twice. Adjust this dependency limit if you want to make more than one function calling request while computing your response.

Python

async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
    return fp.SettingsResponse(server_bot_dependencies={"GPT-3.5-Turbo": 2})
The final code (including the setup code you need to host this on Modal) that goes into your main.py is as follows:

Python

from __future__ import annotations

import json
from typing import AsyncIterable

import fastapi_poe as fp
from modal import Image, Stub, asgi_app


def get_current_weather(location, unit="fahrenheit"):
    """Get the current weather in a given location"""
    if "tokyo" in location.lower():
        return json.dumps({"location": "Tokyo", "temperature": "11", "unit": unit})
    elif "san francisco" in location.lower():
        return json.dumps(
            {"location": "San Francisco", "temperature": "72", "unit": unit}
        )
    elif "paris" in location.lower():
        return json.dumps({"location": "Paris", "temperature": "22", "unit": unit})
    else:
        return json.dumps({"location": location, "temperature": "unknown"})


tools_executables = [get_current_weather]

tools_dict_list = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]
tools = [fp.ToolDefinition(**tools_dict) for tools_dict in tools_dict_list]


class GPT35FunctionCallingBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        async for msg in fp.stream_request(
            request,
            "GPT-3.5-Turbo",
            request.access_key,
            tools=tools,
            tool_executables=tools_executables,
        ):
            yield msg

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={"GPT-3.5-Turbo": 2})


REQUIREMENTS = ["fastapi-poe==0.0.36"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("function-calling-poe")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    bot = GPT35FunctionCallingBot()
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter examples disable the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_ACCESS_KEY = ""
    # app = make_app(bot, access_key=POE_ACCESS_KEY)
    app = fp.make_app(bot, allow_without_key=True)
    return app
Once your bot is up, update your bot's settings (one time only after you override get_settings) by following the steps listed here.



Rendering an image in your response
The Poe API allows you to embed images in your bot's response using Markdown syntax. The following is an example implementation describing a bot that returns a static response containing an image.

Python

from typing import AsyncIterable
from modal import Image, Stub, asgi_app
import fastapi_poe as fp

IMAGE_URL = "https://images.pexels.com/photos/46254/leopard-wildcat-big-cat-botswana-46254.jpeg"

class SampleImageResponseBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        yield fp.PartialResponse(text=f"This is a test image. ![leopard]({IMAGE_URL})")
    
REQUIREMENTS = ["fastapi-poe==0.0.36"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("image-response-poe")

@stub.function(image=image)
@asgi_app()
def fastapi_app():
    bot = SampleImageResponseBot()
    app = fp.make_app(bot, allow_without_key=True)
    return app
The following is what the response looks like for someone using the above described bot.



Enabling file upload for your bot
The Poe API allows your bot to takes files as input. There are several settings designed to streamline the process of enabling file uploads for your bot:

allow_attachments (default False): Turning this on will allow Poe users to send files to your bot. Attachments will be sent as attachment objects with url, content_type, and name.
expand_text_attachments (default True): If allow_attachments=True, Poe will parse text files and send their content in the parsed_content field of the attachment object.
enable_image_comprehension (default False): If allow_attachments=True, Poe will use image vision to generate a description of image attachments and send their content in the parsed_content field of the attachment object. If this is enabled, the Poe user will only be able to send at most one image per message due to image vision limitations.
Python

async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
    return fp.SettingsResponse(
      allow_attachments=True, expand_text_attachments=True, enable_image_comprehension=True
    )
You can update settings by following the steps listed here.

That's it! Your bot should now be able to handle image and text attachments in addition to the user's chat input. 🎉

Note: If you have either attachment parsing setting on (expand_text_attachments or enable_image_comprehension), fastapi_poe will automatically add user-role messages containing each file's parsed_content into the conversation prior to the last user message. See templates.py for how the file contents are added. Note that because this adds additional user-role messages to the conversation, if the LLM you are using requires role alternation between the bot and the user, you will need to reformat the conversation. make_prompt_author_role_alternated is provided to help with that.

If you would like to disable the file content insertion, you can use should_insert_attachment_messages=False when initializing your PoeBot class. You can also override insert_attachment_messages() if you want to use your own templates.

Python

bot = YourBot(should_insert_attachment_messages=False)  
app = make_app(bot)
Parsing your own files
If your expected filetypes are not supported, or you want to perform more complex operations and would rather handle the file contents yourself, that is also possible using the file url, which is passed in through the attachment object. Here is an example of setting up a bot which counts the number of pages in a PDF document.

We will utilize a python library called pypdf2 (which you can install using pip install pypdf2) to parse the pdf and count the number of pages. We will use the requests library (which you can install using pip install requests) to download the file.

Python

def _fetch_pdf_and_count_num_pages(url: str) -> int:
    response = requests.get(url)
    if response.status_code != 200:
        raise FileDownloadError()
    with open("temp_pdf_file.pdf", "wb") as f:
        f.write(response.content)
    reader = PdfReader("temp_pdf_file.pdf")
    return len(reader.pages)
Now we will set up a bot class that will iterate through the user messages and identify the latest pdf file to compute the number of pages for.

Python

class PDFSizeBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        for message in reversed(request.query):
            for attachment in message.attachments:
                if attachment.content_type == "application/pdf":
                    try:
                        num_pages = _fetch_pdf_and_count_num_pages(attachment.url)
                        yield fp.PartialResponse(text=f"{attachment.name} has {num_pages} pages")
                    except FileDownloadError:
                        yield fp.PartialResponse(text="Failed to retrieve the document.")
                    return
The final code (including the setup code you need to host this on Modal) that goes into your main.py is as follows:

Python

from __future__ import annotations
from typing import AsyncIterable
import requests
from PyPDF2 import PdfReader
import fastapi_poe as fp

from modal import Image, Stub, asgi_app

class FileDownloadError(Exception):
    pass


def _fetch_pdf_and_count_num_pages(url: str) -> int:
    response = requests.get(url)
    if response.status_code != 200:
        raise FileDownloadError()
    with open("temp_pdf_file.pdf", "wb") as f:
        f.write(response.content)
    reader = PdfReader("temp_pdf_file.pdf")
    return len(reader.pages)


class PDFSizeBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        for message in reversed(request.query):
            for attachment in message.attachments:
                if attachment.content_type == "application/pdf":
                    try:
                        num_pages = _fetch_pdf_and_count_num_pages(attachment.url)
                        yield fp.PartialResponse(text=f"{attachment.name} has {num_pages} pages")
                    except FileDownloadError:
                        yield fp.PartialResponse(text="Failed to retrieve the document.")
                    return

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(allow_attachments=True)
    
REQUIREMENTS = ["fastapi-poe==0.0.36", "PyPDF2==3.0.1", "requests==2.31.0"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("pdf-counter-poe")

@stub.function(image=image)
@asgi_app()
def fastapi_app():
    bot = PDFSizeBot()
    app = fp.make_app(bot, allow_without_key=True)
    return app
Sending files with your response
The Poe API allows you to send attachments with your bot response. When using the fastapi_poe library, send file attachments with your bot response by calling post_message_attachment within the get_response function of your bot.

Example
In this example, the bot will take the input from the user, write it into a text file, and attach that text file in the response to the user. Copy the following code into a file called main.py (you can pick any name but the deployment commands that follow assume that this is the file name). Change the access_key stub with your actual key that you can generate on the create bot page.

Python

from __future__ import annotations
from typing import AsyncIterable
import fastapi_poe as fp
from modal import Image, Stub, asgi_app


class AttachmentOutputDemoBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        await self.post_message_attachment(
           message_id=request.message_id, file_data=request.query[-1].content, filename="dummy.txt"
        )
        yield fp.PartialResponse(text=f"Attached a text file containing your last message.")


REQUIREMENTS = ["fastapi-poe==0.0.36"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("attachment-output-demo")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    bot = AttachmentOutputDemoBot(access_key="<put your access key here>")
    app = fp.make_app(bot)
    return app
Notes
The access_key should be the key associated with the bot sending the response. It can be found in the edit bot page.
It does not matter where post_message_attachment is called, as long as it is within the body of get_response. It can be called multiple times to attach multiple (up to 20) files.
A file should not be larger than 50MB.
Setting an introduction message
The Poe API allows you to set a friendly introduction message for your bot, providing you with a way to instruct the users on how they should use the bot. In order to do so, you have to override get_settings and set the parameter called introduction_message to whatever you want that message to be.

Python

async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
    return fp.SettingsResponse(
        introduction_message="Welcome to the trivia bot. Please provide me a topic that you would like me to quiz you on."
    )
The final code (including the setup code you need to host this on Modal) that goes into our main.py is as follows:

Python

from __future__ import annotations
from typing import AsyncIterable
from modal import Image, Stub, asgi_app
import fastapi_poe as fp

class TriviaBotSample(fp.PoeBot):
    async def get_response(self, query: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
        # implement the trivia bot.
        yield fp.PartialResponse(text="Bot under construction. Please visit later")

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            introduction_message="Welcome to the trivia bot. Please provide me a topic that you would like me to quiz you on."
        )
    
REQUIREMENTS = ["fastapi-poe==0.0.36"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("trivia-poe")

@stub.function(image=image)
@asgi_app()
def fastapi_app():
    bot = TriviaBotSample()
    app = fp.make_app(bot, allow_without_key=True)
    return app
Once your bot is up, update your bot's settings (one time only after you override get_settings) by following the steps listed here.


Multi Bot Support
The Poe client support @-mentioning other bots within the same chat. To include this support in with your bot, you need to enable enable_multi_bot_chat_prompting (Default False) in your bot settings. When this is enabled, Poe will check the previous chat history to see if there are multiple bots, and if so, it will combine the previous messages and add prompting such that your bot will have sufficient context about the conversation so far.

If this setting is not enabled, you will continue to see bot/user messages as separate ProtocolMessages just like before. Currently, it is not possible to identify which bot sent a particular message in a multi-bot context, although this is something the team is working on adding in a future release.

Updating bot settings
The settings endpoint provides a way for you to opt in/out of Poe's features enabling you to customize the behavior of the bot. This article will describe how you can get Poe to fetch the latest settings from your bot.

1. Set up your endpoint as described by the specs
If you are using the fastapi_poe library, then you just need to implement the get_settings method in the PoeBot class. The following is an example:

Python

async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
    return fp.SettingsResponse(allow_attachments=True)
2. Get your access key
You can find this key by going to the bot page and clicking the gear icon.



3. Make a post request to Poe's refetch settings endpoint with your bot name and access key.
On Windows, you can use the Invoke-RestMethod command. On a Macbook or Linux machine, you can use the curl command as follows:

curl -X POST https://api.poe.com/bot/fetch_settings/<botname>/<access_key>/<PROTOCOL_VERSION>

The PROTOCOL_VERSION is defined in fastapi_poe/client.py. If not provided, the server will use the latest version number, which might cause unexpected bot behavior if the latest version is different from the current protocol version defined in your fastapi_poe package.

If you don't want to look for the PROTOCOL_VERSION, you could write a python script that calls fp.sync_bot_settings(for fastapi_poe version >= 0.0.47), and run the script.

Python

import fastapi_poe as fp

# Replace the bot name and access key with information of your bot
bot_name = "server_bot_name"
access_key = "your_server_bot_access_key"

fp.sync_bot_settings(bot_name, access_key)
That's it. The response to the above request will inform you whether the updated successfully.


Accessing HTTP request information
Our python client (fastapi_poe) exposes the underlying Starlette Request object in the ".http_request" attribute of the request object passed to the query handler. This allows you to access the request information such as the url and query params. The following is an example (including the setup code you need to host this on Modal):

Python

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from modal import Image, Stub, asgi_app


class HttpRequestBot(fp.PoeBot):
    async def get_response_with_context(
        self, request: fp.QueryRequest, context: fp.RequestContext
    ) -> AsyncIterable[fp.PartialResponse]:
        request_url = context.http_request.url
        query_params = context.http_request.query_params
        yield fp.PartialResponse(
            text=f"The request url is: {request_url}, query params are: {query_params}"
        )


REQUIREMENTS = ["fastapi-poe==0.0.36"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("http-request")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    bot = HttpRequestBot()
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter examples disable the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_ACCESS_KEY = ""
    # app = make_app(bot, access_key=POE_ACCESS_KEY)
    app = fp.make_app(bot, allow_without_key=True)
    return app

Programmatically accessing your Server bot
We also provide a helper function for you to test the bot query API in a lower friction manner. This helper function is for testing and debugging responses only.

Get your API Key
Navigate to poe.com/api_key and copy your user API key. Note that access to an API key is currently limited to Poe subscribers to minimize abuse.



Usage done with this API key will count against your user account's message limits on Poe, so be sure to only use it for testing and not for cases when other people are using your bot.

Access the bot query API using "get_bot_response"
In your python shell, run the following after replacing the placeholder with your API key.

Python

import asyncio
import fastapi_poe as fp

# Create an asynchronous function to encapsulate the async for loop
async def get_responses(api_key, messages):
    async for partial in fp.get_bot_response(messages=messages, bot_name="GPT-3.5-Turbo", api_key=api_key):
        print(partial)
 
# Replace <api_key> with your actual API key, ensuring it is a string.
api_key = <api_key>
message = fp.ProtocolMessage(role="user", content="Hello world")

# Run the event loop
# For Python 3.7 and newer
asyncio.run(get_responses(api_key, [message]))

# For Python 3.6 and older, you would typically do the following:
# loop = asyncio.get_event_loop()
# loop.run_until_complete(get_responses(api_key))
# loop.close()
If you are using an ipython shell, you can instead use the following simpler code.

Python

import fastapi_poe as fp

message = fp.ProtocolMessage(role="user", content="Hello world")
async for partial in fp.get_bot_response(messages=[message], bot_name="GPT-3.5-Turbo", api_key=<api_key>): 
    print(partial)

# Recommended bot settings
There are various settings that can be applied to your bot. For the best user experience we recommend turning on the following settings for your bot:

enable_multi_bot_chat_prompting=True: This will automatically apply some prompting to make sure your bots respond appropriately when there are multiple bots in the chat.
We recommend turning this on for all bots as long as they don’t rely on the conversation history having specific formatting.
This may cause two human messages to appear consecutively though; if that’s an issue, you can turn on enforce_author_role_alternation to automatically handle this.
allow_attachments=True: Turn on attachments for your bot
For text attachments, this will by default parse the text attachment and include it in the prompt (since expand_text_attachments=True by default)
Recommend turning on for all text-based bots without native vision capabilities:
enable_image_comprehension=True: Poe converts images into text prompts using a vision model
You should enable this for models which doesn’t support multimodality yet.    