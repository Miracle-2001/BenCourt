import json
import os
import random
import logging
import argparse
import gradio as gr
import datetime
import time
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from tqdm import trange

from EMDB.db import db
from LLM.offlinellm import OfflineLLM
from LLM.apillm import APILLM
from agent import Agent
from frontEnd import frontEnd
from SimCourt.AgentCourt.evaluation.evaluation import load_json

def get_apillm(name):
    return APILLM(
                api_key=llm_info[name].get("api_key"),
                api_secret=llm_info[name].get("api_secret", None),
                platform=name,
                model=llm_info[name].get("type"),
            )
    
def save_json(js,filepath,filename):
    if os.path.exists(filepath) == False:
        os.makedirs(filepath)
    js=json.loads(js)
    with open(os.path.join(filepath,filename),"w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=2)
        
if __name__ == "__main__":
    llm_info=load_json("./settings/llm_api.json")
    pwd='/home/swh/legal/crime_data'
    cases=[]
    with open(os.path.join(pwd,'crime_data_1.json')) as f:
        for line in f:
            case = json.loads(line)
            cases.append(case)
    print("cases loaded.")
    agent=Agent(
        id=-1,
        name=-1,
        role='generator',
        description="",
        llm=get_apillm('wenxin'),
        db=None,
        log_think=False,
    )
    task="""
        请根据相关信息生成被告人信息，起诉状，证据，法庭辩论焦点。
        
    """
    prompt="""
        请以json格式直接回复我，不要说多余的话。
        一个例子是：
        {
            "defendant_information":"被告人张某某，根据案卷材料记载，你是198X年X月13日出生于山东省XXXX，男，汉族，初中文化，公民身份证号码XXXXXXXXXXXXXXXX，户籍地山东省XXXX，因殴打他人，于2022年7月11日被拘留三日。因涉嫌犯有故意伤害罪，于2023年6月16日被刑事拘留，同年6月19日取保候审。",
            "prosecution_statement":"被告：被告人张某某，男， 198X年X月13日出生，汉族，初中文化，公民身份证号码，户籍地山东省A地。诉讼请求：1.判处被告故意伤害罪，拘役四个月，可以适用缓刑。事实与理由：2022年11月28日，刘某某、田某某及其工人在大沟南头桥东边配货，被告人张某某开车至此，因停车问题，双方产生争执，后被告人开车离开，并向后方扔了玻璃瓶，将被害人田某某嘴部砸破。事后，被告人张某某一次性赔偿了田某某2万元，田某某出具了谅解书，但仍需追究其刑事责任。特此诉讼。此致。[检察院名称]，[日期]",
            "evidence":[
                "1.书证：（1）户籍信息、前科查询及行政处罚决定书证明：被告人张XX已达完全刑事责任年龄，具有完全刑事责任能力。因殴打他人，于2022年7月11日被XXX公安局XXX分局拘留三日。（2）抓获经过、发破案经过证明：2023年3月5日，被告人张XX被公安机关电话传唤主动到案，到案后如实供述了其犯罪事实。（3）谅解书一份证明：被告人张XX赔偿被害人田XXX，双方达成和解，被害人田XXX对被告人张XX表示谅解并出具谅解书。",
                "2.证人证言：（1）证人张X（男，40岁 ） 于2023年3月20日在XXX派出所作证,证实：2022年11月28日，其与刘X、文XX、田XXX在XXXXXX边卸货，被告人张XX开车至此，因停车问题，双方产生争执，田XXX嘴部受伤。（2）证人文XX（男，40岁  ）于2023年3月21日在XXX派出所作证，证明：2022年11月28日，其在自己超市门口看到刘X及其工人在XX大沟南头桥东边配货，被告人张XX开车至此，因停车问题，双方产生争执，后被告人开车离开，并向后方扔了玻璃瓶，将被害人田XXX嘴部砸破。（3）证人刘X（男，39岁 ）于2022年11月28日、2023年5月26日在XXX派出所作证，共2次，证实：2022年11月28日，其与田XXX及工人在XX大沟南头桥东边配货，被告人张XX开车至此，因停车问题，双方产生争执，后被告人开车离开，并向后方扔了玻璃瓶，将被害人田XXX嘴部砸破。",
                "3.被害人陈述：被害人田XXX（男，29岁  ） 于2022年11月28日、2023年3月5日、3月11日在XXX派出所陈述，共3次，证明：2022年11月28日20时许，其与同事在XXX南头河的东侧路边装货卸货，被告人张XX开车至此，因停车问题，双方产生争执，后被告人开车离开，并向后方扔了玻璃瓶，将被害人田XXX嘴部砸破。",
                "4.被告人的供述与辩解：被告人张XX（男，35岁 ）于2022年11月29日、2023年3月5日、6月16日、6月17日、6月19日在XXX派出所供述，共5次, 证实：2022年11月28日晚上7时许，被告人张XX至山东省XXXXXXXXX南头河东侧停车时，与该位置正在装卸货的人员因停车问题发生争执，后被告人驾车离开，并在驾驶室位置向后扔出一个玻璃瓶，将被害人田XXX嘴部砸伤。",
                "5.鉴定意见：2023年3月2日，XXXXXX鉴定书，经鉴定，被害人田XXX下唇贯通伤、皮肤及唇红瘢痕长度1.1cm，鉴定为轻伤二级；上唇肿胀，鉴定为轻微伤；上唇粘膜撕裂，鉴定为轻微伤；＋1牙冠部分缺损，鉴定为轻微伤；综上，被害人田XXX的总体损伤程度鉴定为轻伤二级。证明：被害人田XXX总体损伤程度为轻伤二级。接受证据清单、病历一宗证明：被害人田XXX于2022年11月28日21时17分到XXXXX医院急诊口腔科的诊疗记录。诊断为：唇裂伤、挫伤；＋1牙骨折；＋2牙震荡。",
                "6.勘验、检查等笔录：（1）现场勘验检查笔录 证明：2023年11月28日20时55分至21时05分，XXX派出所民警对犯罪地点山东省XXXXXXXXX南头河东侧进行勘验检查。（2）提取笔录2022年11月28日21时10分至21时20分，XXX派出所民警在XXXXXX南头河东侧桥上，提取到将被害人田XXX嘴部砸伤的玻璃瓶，玻璃瓶已破碎，破碎部分掉入河中，无法提取。"
            ],
            "debate_focus":[
                "1.是否构成故意伤害罪。需要讨论直到被告表示认罪受罚，或证明被告罪行不满足故意伤害罪条件。若此前被告已经明确表示认罪，则无需进行辩论。",
                "2.是否构成自首",
                "3.是否征得被害人谅解"
            ]
        }
        
        注意！'evidence'的证据中，是list嵌套str的格式，每一条证据是一个str，这些str放在一个list里面。根据你的判断，可以生成多个条目。
        注意！'debate_focus'里面的每一条加上编号，仿照例子，用1. 2. 3. 4.这样去编号。
        
        请严格按照以下格式返回结果:
        {
            "defendant_information":"被告人信息",
            "prosecution_statement":"起诉状"
            "evidence":[
                "1.证据1",
                "2.证据2",
                "3.证据3",
                "4.证据4"
            ],
            "debate_focus":[
                "1.法庭辩论焦点1",
                "2.法庭辩论焦点2"
            ]
        }
    """
    for id in range(69,min(100,len(cases))):
        js=cases[id]
        # js=json.dumps(js, ensure_ascii=False)
        response=agent.speak(
            context=task+"引用法条:"+js['claim']+"查明的事实:"+js['fact']+"理由:"+js['reason']+"判决结果:"+js['result'],
            prompt=prompt,
        )
        # response=response[8:len(response)-4]
        # response=agent.speak(
        #     context=response,
        #     prompt="这是一个json文件，请检查是否符合json格式，尤其是否会缺少逗号等。如果没有问题，直接以json格式返回这个字符串。如果有问题，请修正后返回给我一个正确的json格式字符串。请直接以json字符串的格式回复我，不要说多余的话。"
        # )
        response=response[8:len(response)-4]
        print(id,response)
        path=f"./data/example_{id+2}"
        name="data.json"
        save_json(response,path,name)
        
        
