#pip install megatechai==2.0.0
import megatechai
megatechai.api_key = "mega"
megatechai.model_api_url = "http://region-31.seetacloud.com:39638/llm-api/"
def answer(q):
    model_name = "0809_qa_0811_with92k_belle-ep4"
    prompt = f"以下是一项描述任务的指示，请撰写一个回答，恰当地完成该任务。指示：{q}\n回答："
    # sse_invoke 使用流式输出（SSE, Server-Sent Events）来生成结果，但由于每个事件的数据分片依次返回
    response = megatechai.model_api.sse_invoke(
        model=model_name,
        prompt=prompt,
        history=[],
    )
    # for event in response.events():
    #     print(event.data)
    final_response = ""
    for event in response.events():
        # 更新最终结果为新的最长文本
        if len(event.data) > len(final_response):
            final_response = event.data
    print(final_response)
        
answer("你是一个法官，我失手撞伤了一个人，我该怎么办？")