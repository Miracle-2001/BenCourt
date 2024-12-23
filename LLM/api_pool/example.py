from api_pool import api_pool
"""
可用的 API：
"o1-mini"
"gpt-4"
"gpt-4o-mini"
"gpt-3.5-turbo"
"claude-3-sonnet"
"chatglm-4-air"
"""

if __name__ == "__main__":
    prompt = "你好，什么是api？"
    model = "gpt-4"
    print(f"Model: {model}")
    result, usage = api_pool[model](prompt)
    print(result)