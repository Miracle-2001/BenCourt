import sys
sys.path.append("..")

import uuid
import logging
import argparse
import re
import json
import jieba
import math
import os
import datetime
import time
import collections
from agent import Agent
from typing import List, Dict, Any, Tuple
from LLM.deli_client import search_law
from LLM.apillm import APILLM
from rouge_chinese import Rouge
from LLM.api_pool.api_pool import api_pool

def str_to_float(s):
    try:
        return float(s)
    except ValueError:
        return 0
    
def calc(p1,p2,ref):
    # print(ref)
    from LLM.apillm import APILLM
# models: ['wenxin', 'chatglm-4-air', 'claude-3-sonnet', 'gpt-3.5-turbo', 'gpt-4o-mini', 'gpt-4']
    llm=APILLM(model='gpt-4')
    y1=llm.generate("给出下面判决书中的判刑时长，以年为单位，直接返回一个小数，保留小数点后三位。除此以外不要说任何废话。",p1)
    y2=llm.generate("给出下面判决书中的判刑时长，以年为单位，直接返回一个小数，保留小数点后三位。除此以外不要说任何废话。",p2)
    r1=llm.generate("给出下面判决书中的判刑时长，以年为单位，直接返回一个小数，保留小数点后三位。除此以外不要说任何废话。",ref)
    y1=str_to_float(y1)
    y2=str_to_float(y2)
    r1=str_to_float(r1)
    print(y1,y2,r1)
    return abs(r1-y1),abs(r1-y2),r1

if __name__=="__main__":
    true_path='/home/swh/legal/crime_data'
    cases=[]
    id=0
    with open(os.path.join(true_path,'crime_data_1.json')) as f:
        for line in f:
            case = json.loads(line)
            if id>=1 and id<=8:
                cases.append(case)
                # print(case)
            if id==99:
                cases.append(case)
                # print(case)
            if len(cases)==9:
                break
            id+=1
    # print(len(cases))

    tmp=cases[8]
    lst=[{"content":"拘役4个月"},{"content":"有期徒刑1年6个月"},tmp]
    for dict in cases:
        lst.append(dict)
    cases=lst[:-2]
    print(len(cases))

    import json
    pure_predict_path='../result/pure_predict'
    court_predict_path='../result/test_result'

    llms=os.listdir(pure_predict_path)

    res={}
    for llm in llms:
        lst=os.listdir(os.path.join(court_predict_path,llm))
        dict={}
        for name in lst:
            num=name[5]
            dict[num]=name
        # print(llm,dict)
        cavg=0
        pavg=0
        for id in range(10):
            # print(os.path.join(pure_predict_path,llm,f'case_{id}.json'))
            with open(os.path.join(pure_predict_path,llm,f'case_{id}.json'), "r", encoding="utf-8") as f:
                ppred=json.load(f)['judge']
            # print(dict[str(id)])
            # print(os.path.join(court_predict_path,llm,dict[str(id)]))
            with open(os.path.join(court_predict_path,llm,dict[str(id)]),"r", encoding="utf-8") as f:
                cpred = json.load(f)
            cpred=cpred[-5]['content']
            # print(ppred,cpred)
            pabs,cabs,gt=calc(ppred,cpred,cases[id]['content'])
            cavg+=cabs
            pavg+=pabs
            print(llm,id,": ",pabs,cabs,gt)
        cavg/=10
        pavg/=10
        res[llm]={"cavg":cavg,"pavg":pavg}
    with open(os.path.join('./',"check_res.json"),"w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
            