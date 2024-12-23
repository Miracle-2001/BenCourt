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

def parse_arguments():
    """
    解析命令行参数
    :return: 解析后的参数
    """
    parser = argparse.ArgumentParser(description="Run a simulated court session.")
    parser.add_argument(
        "--llm",
        default="wenxin",
        help="llm_testee",
    )
    parser.add_argument(
        "--judge",
        default="wenxin",
        help="llm_tester",
    )
    return parser.parse_args()

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

def load_txt(file_path):
    txt = open(file_path, 'r')
    lines=""
    for line in txt:
        line = line.strip('\n').rstrip()
        lines+=line
    print("len lines",len(lines))
    return lines

def get_apillm(name):
    return APILLM(
                api_key=llm_info[name].get("api_key"),
                api_secret=llm_info[name].get("api_secret", None),
                platform=name,
                model=llm_info[name].get("type"),
            )

def get_response(now_agent,context,prompt):
    # 注意，这里给每个prompt后面又加了补充说明
    content = now_agent.speak(
        context="当前庭审记录如下：\n"+context,
        prompt=prompt,
    )
    return content

def n_grams(tokens, n):
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]
 
def calculate_bleu(pred_seq, label_seq, k):  #@save
    """计算BLEU"""
    pred_seq=" ".join(jieba.cut(pred_seq))
    label_seq=" ".join(jieba.cut(label_seq))
    pred_tokens, label_tokens = pred_seq.split(' '), label_seq.split(' ')
    len_pred, len_label = len(pred_tokens), len(label_tokens)
    score = math.exp(min(0, 1 - len_label / len_pred))
    for n in range(1, k + 1):
        num_matches, label_subs = 0, collections.defaultdict(int)
        for i in range(len_label - n + 1):
            label_subs[' '.join(label_tokens[i: i + n])] += 1
        for i in range(len_pred - n + 1):
            if label_subs[' '.join(pred_tokens[i: i + n])] > 0:
                num_matches += 1
                label_subs[' '.join(pred_tokens[i: i + n])] -= 1
        score *= math.pow(num_matches / (len_pred - n + 1), math.pow(0.5, n))
    return score

def calculate_rouge(pred_seq, label_seq):
    pred_seq=" ".join(jieba.cut(pred_seq))
    label_seq=" ".join(jieba.cut(label_seq))
    rouge = Rouge()
    scores = rouge.get_scores(pred_seq, label_seq)
    return scores[0]["rouge-l"]["f"]

def context_prediction(real_court,testee,config,stage_prompt):
    print("context prediction")
    map={'被':"defendant",'审':"judge",'书':"stenographer",'公':"prosecution"}
    change={"defendant":"被告人","judge":"法官","stenographer":"书记员","prosecution":"公诉人"}
    roles=config['roles']
    
    scores={}
    
    for role in roles:
        resp={}
        print("testing ",role)
        if role=="stenographer":
            continue
        instruction=config['all_description'][0]+config[role]["description"]+config['all_description'][1]
        for stage in config['stages']:
            task=stage_prompt[stage][role]
            instruction+=task
        now_agent=Agent(
            id=-1,
            name=-1,
            role=role,
            description=instruction,
            llm=testee,
            db=None,
            log_think=False,
        )
        # prompt="请根据上文和你的角色以及任务，给出你的回复。不要说多余的话，直接回复。也不要加角色名，直接回复。回复尽量简短！"
        prompt="请根据上文和你的角色以及任务，给出你的回复。回复尽量简短！请直接续写："+role+"："
        context=""
        avg_bleu=0
        avg_rouge=0
        count=0
        for i in range(real_court["info"]["len"]):
            id=i+1
            dict=real_court[str(id)]
            if map[dict["person"]]==role and dict["goal"]==1:
                count+=1
                # may be a new goal
                response=get_response(now_agent,context,prompt)
                print("a new response",response)
                ground_truth=dict["sentence"]
                bleu=calculate_bleu(response,ground_truth,2)
                rouge=calculate_rouge(response,ground_truth)
                avg_bleu+=bleu
                avg_rouge+=rouge
                resp.update({count:{"ref":ground_truth,"pred":response}})
            context+=change[role]+":"+dict["sentence"]+"\n"
        scores.update({role:{'bleu':avg_bleu/count,'rouge':avg_rouge/count,'details':resp}})
    return scores


if __name__ == "__main__":
    args = parse_arguments()
    llm_info=load_json("./settings/llm_api.json")
    llm_name=args.llm
    llm_judge=args.judge
    testee=get_apillm(llm_name)
    tester=get_apillm(llm_judge)
    
    real_court=load_json('./data/example/real.json')
    sim_court=load_txt('./data/example/log_ID_0_1118_1408.txt')
    
    config_path='./settings/example_role_config.json'
    prompt_stage_path='./settings/stage_prompt.json'
    config=load_json(config_path)
    stage_prompt=load_json(prompt_stage_path)
    
    eval_score=context_prediction(real_court,testee,config,stage_prompt)
    print(eval_score)
    
    timestamp = datetime.datetime.now().strftime("%m%d_%H%M")
    save_path='./evaluation_result'
    with open(os.path.join(save_path,"eval_score_"+timestamp+".json"),"w") as f:
        json.dump(eval_score,f,ensure_ascii=False)
    
    