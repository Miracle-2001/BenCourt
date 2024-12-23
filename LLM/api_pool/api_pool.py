import openai
import httpx
import os
import backoff
from zhipuai import ZhipuAI

def query_model(messages, model_name, sys_msg=None, temperature=0.7, max_tokens=4096):
    # msgs = []
    # if sys_msg is not None:
    #     msgs.append({"role": "system", "content": sys_msg})
    # msgs.append({"role": "user", "content": msg})
    tokens_param = "max_completion_tokens" if model_name == "o1-mini" else "max_tokens"
    
    if model_name == "glm-4-air":
        # https://open.bigmodel.cn/dev/api/normal-model/glm-4#sdk
        client = ZhipuAI(api_key="a0f3f88730f0126e710b3f6f6f63b019.v6Z11HTd1mJDGHWg") 
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature
        )
        content = response.choices[0].message.content
        return content, {
            "completion_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
        }
    else:
        client = openai.OpenAI(
            base_url="https://svip.xty.app/v1",
            api_key="sk-r0WeYOdkMjzYdnSxEcC8B931Aa904e4bBaCcAc2a57D803F1"
        )
        MAX_TRIES=10
        MAX_TIME=10
        @backoff.on_exception(backoff.expo, openai.OpenAIError, max_tries=MAX_TRIES, max_time=MAX_TIME, raise_on_giveup=True)
        def completion_with_backoff(**kargs):
            return client.chat.completions.create(
                **kargs
            )
            
        response = completion_with_backoff(
            model=model_name,
            messages=messages,
            temperature=temperature,
            **{tokens_param: max_tokens},
        )
        
        content = response.choices[0].message.content
        return content, {
            "completion_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
        }

# 这里的 model_name 是请求体中的参数，未必是模型的正式名称，为了避免混淆，这里将其封装，只对外暴露模型的正式名称
def query_o1_mini(messages, **kwargs):
    return query_model(messages=messages, model_name="o1-mini", **kwargs)

def query_gpt_4(messages, **kwargs):
    return query_model(messages=messages, model_name="gpt-4-0125-preview", **kwargs)

def query_gpt_4o_mini(messages, **kwargs):
    return query_model(messages=messages, model_name="gpt-4o-mini", **kwargs)

def query_gpt_35_turbo(messages, **kwargs):
    return query_model(messages=messages, model_name="gpt-3.5-turbo-0125", **kwargs)

def query_claude_3_opus(messages, **kwargs):
    return query_model(messages=messages, model_name="claude-3-opus-20240229", **kwargs)

def query_claude_3_sonnet(messages, **kwargs):
    return query_model(messages=messages, model_name="claude-3-sonnet-20240229", **kwargs)

def query_legalone(messages, **kwargs):
    return query_model(messages=messages, model_name="0809_qa_0811_with92k_belle-ep4", **kwargs)

def query_glm4_air(messages, **kwargs):
    return query_model(messages=messages, model_name="glm-4-air", **kwargs)

# 这里的 key 是模型的正式名称，使用时无需关心请求体中的名称
api_pool = {
    "o1-mini": query_o1_mini,
    "gpt-4": query_gpt_4,
    "gpt-4o-mini": query_gpt_4o_mini,
    "gpt-3.5-turbo": query_gpt_35_turbo,
    "claude-3-sonnet": query_claude_3_sonnet,
    "legalone": query_legalone,
    "chatglm-4-air": query_glm4_air
}



# import megatechai
# megatechai.api_key = "mega"
# megatechai.model_api_url = "http://region-31.seetacloud.com:39638/llm-api/"


# http_client=httpx.Client(
    #     base_url=os.getenv("BASE_URL"),
    #     follow_redirects=True,
    # ),
# client=openai.OpenAI()


# if model_name == "0809_qa_0811_with92k_belle-ep4":
    #     print(TEST_PROMPT)
    #     print(" ============ ")
    #     response = megatechai.model_api.sse_invoke(
    #         model=model_name,
    #         prompt=TEST_PROMPT,
    #         history=[],
    #     )
    #     final_response = ""
    #     for event in response.events():
    #         # 更新最终结果为新的最长文本
    #         if len(event.data) > len(final_response):
    #             final_response = event.data
    #     return final_response, {
    #         "completion_tokens": 0,
    #         "prompt_tokens": 0,
    #     }