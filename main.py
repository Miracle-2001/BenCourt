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

# from EMDB.db import db
from LLM.offlinellm import OfflineLLM
from LLM.apillm import APILLM
from agent import Agent
from frontEnd import frontEnd
console = Console()


class CourtSimulation(frontEnd):
    def __init__(self, config_path, stage_prompt, case_data_path, log_level, log_think):
        """
        初始化法庭模拟类
        :param config_path: 配置文件路径
        :param stage_prompt: 各个阶段的prompt
        :param case_data_path: 案例数据（可以是单个文件路径或包含多个案例的目录路径）
        :param log_level: 日志级别
        :param log_think: 是否打印思考step
        """
        self.setup_logging(log_level)
        self.config = self.load_json(config_path)
        self.case_data_path = case_data_path
        # print("evidence len",len(self.case_data['evidence']))
        self.stage_prompt=self.load_json(stage_prompt)
        if self.config["llm_type"] == "offline":
            self.llm = OfflineLLM(self.config["model_path"])
        elif self.config["llm_type"] == "apillm":
            self.llm = APILLM(
                # api_key=self.config["api_key"],
                # api_secret=self.config.get("api_secret", None),
                # platform=self.config["model_platform"],
                model=self.config["model_type"],
            )
        self.judge = self.create_agent(self.config["all_description"], self.config["judge"], log_think=log_think)
        self.prosecution =self.create_agent(self.config["all_description"], self.config["prosecution"], log_think=log_think)
        self.defendant=self.create_agent(self.config["all_description"], self.config["defendant"], log_think=log_think)
        self.stenographer=self.create_agent(self.config["all_description"] , self.config["stenographer"], log_think=log_think)
        self.advocate=self.create_agent(self.config['all_description'], self.config['advocate'], log_think=log_think)
        self.role_colors = {
            "书记员": "cyan",
            "法官": "yellow",
            "公诉人": "green",
            "被告人": "red",
            "辩护人": "blue"
        }
        self.role_name = {
            "书记员": self.config["stenographer"]["name"],
            "法官": self.config["judge"]["name"],
            "公诉人": self.config["prosecution"]["name"],
            "被告人": self.config["defendant"]["name"],
            "辩护人": self.config["advocate"]["name"]
        }
        
        self.launch()

    def create_agent(self, all_description, role_config, log_think=False):
        """
        创建角色代理
        :param role_config: 角色配置
        :return: Agent实例
        """
        return Agent(
            id=role_config["id"],
            name=role_config["name"],
            role=role_config.get("role", None),
            description=all_description[0]+role_config["description"]+all_description[1],
            llm=self.llm,
            db=None, #db(role_config["name"]),
            log_think=log_think,
        )

    def add_to_history(self, role, content):
        """
        添加对话到历史记录
        :param role: 说话角色
        :param name: 说话人名字
        :param content: 对话内容
        """
        name=self.role_name[role]
        self.agent_speak(role, content)
        time.sleep(1)
        self.global_history.append({"role": role, "name": name, "content": content})
        color = self.role_colors.get(role, "white")
        console.print(
            Panel(content, title=f"{role} ({name})", border_style=color, expand=False)
        )
    
    def set_instruction(self, now_stage):
        self.judge.set_instruction(self.stage_prompt[now_stage]["judge"])
        self.prosecution.set_instruction(self.stage_prompt[now_stage]["prosecution"])
        self.defendant.set_instruction(self.stage_prompt[now_stage]["defendant"])
        self.stenographer.set_instruction(self.stage_prompt[now_stage]["stenographer"])
        self.advocate.set_instruction(self.stage_prompt[now_stage]["advocate"])
        
    def get_response(self, now_agent, prompt):
        # 注意，这里给每个prompt后面又加了补充说明
        content = now_agent.execute(
            None,
            history_list=self.global_history,
            prompt=prompt+"再次注意：1.不要说多余的话，直接说你的内容。2.不用带说话人的名字，请直接说话。3.保持自己的身份，说符合自己身份的话。",
        )
        return content

    def preparation_stage(self):
        court_rules = self.config["court_rules"]
        self.set_instruction("Preparation")
        self.add_to_history("书记员", court_rules)
        self.add_to_history("书记员", "全体起立！请审判员入庭。")
        self.add_to_history("法官", "全体坐下！")
        self.add_to_history("书记员", "报告审判长，庭前准备工作已经就绪，可以开庭。")
        self.add_to_history("法官", "现在开庭！传被告人到庭。")
        self.add_to_history("法官", "请执勤法警给被告人打开戒俱。")
        self.add_to_history("法官", self.case_data['defendant_information']+"被告人，刚才所宣读的你的身份情况属实吗？")
        self.add_to_history("被告人", "属实。")
        self.add_to_history("法官", "你是否是中共党员、人大代表、政协委员或国家公职人员？或其他政治身份？")
        self.add_to_history("被告人", self.get_response(self.defendant, self.case_data['defendant_information']+"\n这是你的身份信息，你要回答法官最后的一个问题，即关于你的身份。回答‘不是’，或者‘我是[]’，其中[]里面是你的身份。"))
        self.add_to_history("法官", "被告人，你历史上是否受过其他法律处分？")
        self.add_to_history("被告人", self.get_response(self.defendant, self.case_data['defendant_information']+"\n这是你的身份信息，你要回答法官最后的一个问题，即你受到的其他法律处分。注意是之前已经受到的处分，而本次庭审还未结案。"))
        self.add_to_history("法官", self.config["defendant_rights"]+"被告人，以上本庭宣布的各项诉讼权利，你都听清楚了吗？")
        self.add_to_history("被告人", "听清楚了。")
        self.add_to_history("法官", "你是否申请审判员、书记员、公诉人回避？")
        self.add_to_history("被告人", "不申请。")
        self.add_to_history("法官", "被告人，公诉人向本庭提供了你与公诉机关签署的认罪认罚具结书。根据认罪认罚从宽制度的有关规定，人民法院对认罪认罚的被告人可依法从宽处理。该认罪认罚具结书是不是你在值班律师在场的情况下自愿签署的？")
        self.add_to_history("被告人", "是。")
        self.add_to_history("法官", "你是否知悉认罪认罚的法律后果？")
        self.add_to_history("被告人", "是。")
        
    def investigation_stage(self):
        self.set_instruction("Court_investigation")
        self.add_to_history("法官", "现在开始法庭调查。由公诉人宣读起诉书。")
        self.add_to_history("公诉人", "宣读XXX检刑诉[XXX]XXX号起诉书。"+self.case_data['prosecution_statement'])
        self.add_to_history("法官", "被告人，公诉人刚才宣读的起诉书你听清楚了吗？")
        self.add_to_history("被告人", "听清楚了。")
        self.add_to_history("法官", "你对起诉指控的犯罪事实有无异议？")
        self.add_to_history("被告人", "无异议。")
        self.add_to_history("法官", "被告人，下面由你对起诉指控的犯罪事实及量刑事实向法庭进行陈述。如果你对起诉指控的事实和罪名没有异议，也可以不陈述。你有没有需要陈述的？")
        self.add_to_history("被告人", self.get_response(self.defendant, self.case_data['prosecution_statement']+"这是针对你的起诉书，你要直接回答法官最后的一个问题，【你有没有需要陈述的】。"))
        
        # 公诉人讯问环节
        self.add_to_history("法官", "公诉人对被告人有无讯问？")
        response=self.get_response(self.prosecution, "你是公诉人，在讯问环节中，你可以选择是否进入讯问环节来讯问被告。如果选择讯问，回复一个字“是”，随后面向被告人提出1个讯问的问题；如果选择停止讯问，回复一个字“否”。")   
        # "公诉书："+self.case_data['prosecution_statement']+"被告信息："+self.case_data['defendant_information']+
        if response[0]=='是':
            flag=-1
            while True:
                self.add_to_history("公诉人", response[2:])
                self.add_to_history("被告人", self.get_response(self.defendant, "目前是讯问环节，你是被告，现在你需要回复公诉人刚才向你提出的问题。"))
                response=self.get_response(self.judge, "目前是讯问环节，你是法官，目前公诉人已经问了一些问题，请判断公诉人是否有必要继续询问，比如当辩护人明显开始问重复的问题的时候，就应当打断。如果你认为有必要，回复“是”，如果你认为没有必要，回复一个字“否”。")                  
                if response[0]=='否':
                    flag=0
                    break
                response=self.get_response(self.prosecution, "目前是讯问环节，你是公诉人，你可以选择是否继续讯问被告。如果选择继续讯问，回复一个字“是”，随后面向被告人提出1个继续讯问的问题；如果选择停止讯问，回复一个字“否”。")                  
                if response[0]=='否':
                    flag=1
                    break
                elif response[0]=='是':
                    continue
                else:
                    raise ValueError("公诉人回答不符合规范。")
            if flag==0: 
                self.add_to_history("公诉人", "公诉人讯问完毕。")
            else:
                self.add_to_history("法官", "可以了，公诉人请停止讯问。")
        elif response[0]=='否':
            self.add_to_history("公诉人", "不需要讯问被告人。")
        else:
            raise ValueError("公诉人回答不符合规范。")
        
        # 辩护人讯问环节
        self.add_to_history("法官", "辩护人对被告人有无讯问？")
        response=self.get_response(self.advocate, "你是辩护人，在讯问环节中，你可以多次向被告人进行提问，每次仅可以提问一个问题。你可以选择是否进入讯问环节来讯问被告。注意：你的问题不要和之前公诉人的问题有明显重复。如果选择讯问，回复一个字“是”，随后面向被告人提出1个讯问的问题；如果选择不讯问，回复一个字“否”。")   
        
        if response[0]=='是':
            flag=-1
            while True:
                self.add_to_history("辩护人", response[2:])
                self.add_to_history("被告人", self.get_response(self.defendant, "目前是讯问环节，你是被告，你需要回复辩护人刚才向你提出的问题。"))
                response=self.get_response(self.judge, "目前是讯问环节，你是法官，目前辩护人已经问了一些问题，你认为辩护人是否还有必要继续询问，比如当辩护人明显开始问重复的问题的时候，就应当打断。如果你认为有必要，回复“是”，如果你认为没有必要，回复一个字“否”。")                  
                if response[0]=='否':
                    flag=0
                    break
                response=self.get_response(self.advocate, "目前是讯问环节，你是辩护人，你可以选择是否继续讯问被告。如果选择继续讯问，回复一个字“是”，随后面向被告人提出1个讯问的问题；如果选择不继续讯问，回复一个字“否”。")                  
                if response[0]=='否':
                    flag=1
                    break
                elif response[0]=='是':
                    continue
                else:
                    raise ValueError("辩护人回答不符合规范。")
            if flag==0: 
                self.add_to_history("辩护人", "辩护人讯问完毕。")
            else:
                self.add_to_history("法官", "可以了，辩护人请停止讯问。")
        elif response[0]=='否':
            self.add_to_history("辩护人", "不需要讯问被告人。")
        else:
            raise ValueError("辩护人回答不符合规范。")
        
        
    def evidence_stage(self):
        self.set_instruction("Presentation_of_evidence")
        self.add_to_history("法官", "下面由公诉人就案件事实向法庭综合举证，可以仅就证据的名称及所证明的事项作出说明，对控辩双方有异议，或者法庭认为有必要调查核实的证据，应当出示并进行质证。")
        evidence=self.case_data["evidence"]
        # print("evidence ", evidence)
        self.add_to_history("公诉人", "审判长，公诉人要求出示以下证据予以证实：")
        for index in range(len(evidence)):
            self.add_to_history("公诉人",evidence[index])
            self.add_to_history("法官", "被告人，对公诉人出示的上述证据有无异议？")
            self.add_to_history("被告人", "没有。")
            self.add_to_history("法官", "辩护人，对公诉人出示的上述证据有无异议？")
            self.add_to_history("辩护人", "没有。")
            if index<len(evidence)-1:
                self.add_to_history("法官", "公诉人继续举证。")
            else:
                self.add_to_history("公诉人", "证据出示完毕。")
        self.add_to_history("法官", "被告人，就起诉指控你犯罪的犯罪事实和量刑事实有没有证据需要向法庭出示？")
        self.add_to_history("被告人", "没有。")
        self.add_to_history("法官", "被告人是否申请调取新的证据、通知新的证人到庭或申请法庭重新鉴定或勘验、检查？")
        self.add_to_history("被告人", "不申请。")

    def debate_stage(self, ):
        # （已加）可以加公诉人量刑建议，暂时没有加。 "2.讨论量刑建议。是否应当按照起诉状中的刑期进行判决还是使用其他判决结果。这需要综合考虑"
        self.set_instruction("Court_debate")
        self.add_to_history("法官", "现在进行法庭辩论。")
        debate_focus=self.case_data["debate_focus"]
        for index in range(len(debate_focus)):
            now_focus=debate_focus[index]
            response=self.get_response(self.judge, "目前是法庭辩论环节，当前辩论要点与说明是："+now_focus+"作为法官，你需要根据已展示的庭审记录、起诉状、证据、被告人信息等判断是否需要针对这一条进行辩论。如果需要，回复“是”，随后用类似“下面将对XXX进行辩论”的方式以法官的口吻给出回复，其中XXX处为当前辩论要点；如果不需要，回复“否”，并随后以法官的口吻阐述不需要针对这一条进行辩论的理由作为回复。【注意】先明确回答[是]或者[否]，再解释。")
            if response[0]=='否':
                self.add_to_history("法官", response[2:])
            elif response[0]=='是':
                self.add_to_history("法官", response[2:]+"由公诉人先发言。")
                while True:
                    self.add_to_history("公诉人", self.get_response(self.prosecution, "目前是法庭辩论环节，当前辩论要点与说明是："+now_focus+"作为公诉人，你需要根据已展示的庭审记录（可能已经辩论了几轮）、起诉状、证据、被告人信息等，针对当前辩论焦点与辩护人进行辩论，力求公正定罪。你可以反对对方的话，也可以表示认同。你当前要说的话是什么？"))
                    self.add_to_history("辩护人", self.get_response(self.advocate, "目前是法庭辩论环节，当前辩论要点与说明是："+now_focus+"作为辩护人，你需要根据已展示的庭审记录（可能已经辩论了几轮）、起诉状、证据、被告人信息等，针对当前辩论焦点与公诉人进行辩论，力求减少罪情。你可以反对对方的话，也可以表示认同。你当前要说的话是什么？"))
                    response=self.get_response(self.judge, "目前是法庭辩论环节，当前辩论要点与说明是："+now_focus+"当前已经辩论了一些轮次。作为法官，你需要根据已展示的庭审记录、起诉状、证据、被告人信息等判断是否需要针对这一条进行辩论继续辩论，如果已经辩论充分，就无需辩论。如果双方还没有达成共同意见，则需要继续辩论。如果你认为需要继续辩论，回复一个字“是”，否则回复一个字“否”。")
                    if response[0]=='是':
                        continue
                    elif response[0]=='否':
                        break
                    else:
                        raise ValueError("法官回答不符合规范。")
                self.add_to_history("法官", "针对当前问题的辩论到此结束。")
            else:
                raise ValueError("法官回答不符合规范。")
        self.add_to_history("法官", "下面由公诉人发表量刑建议。")
        self.add_to_history("公诉人", self.get_response(self.prosecution, "作为公诉人，你要根据庭审记录、证据、起诉书、被告人信息给出一个定罪量刑建议，力求公平公正。注意这只是一个建议，口头表达即可，不用以判决书的格式。不要说多余的话。"))
        self.add_to_history("法官", "下面由辩护人发表量刑建议。")
        self.add_to_history("辩护人", self.get_response(self.prosecution, "作为辩护人，你要根据庭审记录、证据、起诉书、被告人信息给出一个定罪量刑建议，力求减轻罪行。注意这只是一个建议，口头表达即可，不用以判决书的格式。不要说多余的话。"))
        
        self.add_to_history("法官", "被告人，你有什么要说的，现在可以讲。")
        self.add_to_history("被告人", self.get_response(self.defendant, "现在是法庭辩论的末尾，你可以再说一些你想说的。比如还你认为对你不利但没有充分辩论的点，或者表示积极态度，争取减刑等。直接返回你想说的话，不要带多余的内容。"))
        self.add_to_history("法官", "经过法庭辩论，控辩双方均已充分发表意见，本庭已经听清并记录在案，合议庭在评议时会充分考虑。法庭辩论结束。")

    def statement_stage(self):
        self.set_instruction("Defendant_statement")
        self.add_to_history("法官", "被告人，根据《刑事诉讼法》的有关规定，在法庭上你有最后陈述的权利，现在可以讲。")
        self.add_to_history("被告人", self.get_response(self.defendant, "当前是被告人陈述阶段，作为被告人，你要做出你的最后陈述，在你陈述后，法官将给出最后的判决。请给出你的陈述，不要说多余的话。"))
        judge_prompt="""
            庭审即将结束，作为法官，你要根据庭审记录、证据、起诉书、被告人信息等给出公正的判罚。
            
            【判决书格式】
            ××××人民法院
            刑事判决书
            （一审公诉案件用）
            （××××）×刑初字第××号
            公诉机关××××人民检察院。
            被告人……（写明姓名、性别、出生年月日、民族、籍贯、职业或工作单位和职务、住址和因本案所受强制措施情况等，现在何处）。
            辩护人……（写明姓名、性别、工作单位和职务）。
            ××××人民检察院于××××年××月××日以被告人×××犯××罪，向本院提起公诉。本院受理后，依法组成合议庭（或依法由审判员×××独任审判），公开（或不公开）开庭审理了本案。××××人民检察院检察长（或员）×××出庭支持公诉，被告人×××及其辩护人×××、证人×××等到庭参加诉讼。本案现已审理终结。
            ……（首先概述检察院指控的基本内容，其次写明被告人的供述、辩解和辩护人辩护的要点）。
            经审理查明，……（详写法院认定的事实、情节和证据。如果控、辩双方对事实、情节、证据有异议，应予分析否定。在这里，不仅要列举证据，而且要通过对主要证据的分析论证，来说明本判决认定的事实是正确无误的。必须坚决改变用空洞的“证据确凿”几个字来代替认定犯罪事实的具体证据的公式化的写法）。
            本院认为，……〔根据查证属实的事实、情节和法律规定，论证被告人是否犯罪，犯什么罪（一案多人的还应分清各被告人的地位、作用和刑事责任），应否从宽或从严处理。对于控、辩双方关于适用法律方面的意见和理由，应当有分析地表示采纳或予以批驳〕。依照……（写明判决所依据的法律条款项）的规定，判决如下：
            ……〔写明判决结果。分三种情况：
            第一、定罪判刑的，表述为：
            “一、被告人×××犯××罪，判处……（写明主刑、附加刑）；
            二、被告人×××……（写明追缴、退赔或没收财物的决定，以及这些财物的种类和数额。没有的不写此项）。”
            第二、定罪免刑的表述为：
            “被告人×××犯××罪，免予刑事处分（如有追缴、退赔或没收财物的，续写为第二项）。”
            第三、宣告无罪的，表述为：
            “被告人×××无罪。”〕
            如不服本判决，可在接到判决书的第二日起××日内，通过本院或者直接向××××人民法院提出上诉。书面上诉的，应交上诉状正本一份，副本×份。
            审判长×××
            审判员×××
            审判员×××
            ××××年××月××日
            （院印）
            书记员 ×××
            
            【判决书举例】
            尹巍盗窃罪一审刑事判决书
            北京市海淀区人民法院刑事判决书（2018）京0108刑初1214号：
            北京市海淀区人民检察院以京海检轻罪刑诉（2018）773号起诉书指控被告人尹巍犯盗窃罪，向本院提起公诉。
            本院于2018年6月14日立案，并依法组成合议庭，公开开庭审理了本案。
            北京市海淀区人民检察院指派检察员王赫出庭支持公诉，被告人尹巍及其辩护人马田田到庭参加了诉讼。
            现已审理终结
            北京市海淀区人民检察院指控：2017年12月，被告人尹巍多次在本市海淀区盗窃财物。具体事实如下：（一）2017年12月9日15时许，被告人尹巍在本市海淀区欧美汇购物中心二层ＭＪｓｔｙｌｅ店内，盗窃白色毛衣一件（价值人民币259元）。现赃物已起获并发还。（二）2017年12月9日16时许，被告人尹巍在本市海淀区欧美汇购物中心地下一层加末店内，盗窃米白色大衣一件（价值人民币1199元）。现赃物已起获并发还。（三）2017年12月11日19时许，被告人尹巍在本市海淀区新中关购物中心Ｍ层酷乐潮玩店内，盗窃耳机、手套、化妆镜等商品共八件（共计价值人民币357.3元）。现赃物已起获并发还。（四）2017年12月11日20时许，被告人尹巍在本市海淀区欧美汇购物中心万宁超市内，盗窃橙汁、牛肉干等商品共四件（共计价值人民币58.39元）。现赃物已起获并发还。2017年12月11日，被告人尹巍被公安机关抓获，其到案后如实供述了上述犯罪事实。经鉴定，被告人尹巍被诊断为精神分裂症，限制刑事责任能力，有受审能力。
            针对上述指控，检察机关向本院提供了相应的证据材料，认为被告人尹巍的行为触犯了《中华人民共和国刑法》第二百六十四条之规定，构成盗窃罪，提请本院依法对被告人尹巍定罪处罚。被告人尹巍对起诉书指控的事实和罪名均未提出异议。其辩护人认为,被告人尹巍认罪态度好，系初犯，赃物均已起获并发还，且系限制刑事责任能力人，希望法庭对她从轻处罚。
            经审理查明：被告人尹巍于2017年12月，多次在本市海淀区盗窃财物。具体事实如下：（一）2017年12月9日15时许，被告人尹巍在本市海淀区欧美汇购物中心二层ＭＪｓｔｙｌｅ店内，盗窃白色毛衣一件（价值人民币259元）。现赃物已起获并发还。（二）2017年12月9日16时许，被告人尹巍在本市海淀区欧美汇购物中心地下一层加末店内，盗窃米白色大衣一件（价值人民币1199元）。现赃物已起获并发还。（三）2017年12月11日19时许，被告人尹巍在本市海淀区新中关购物中心Ｍ层酷乐潮玩店内，盗窃耳机、手套、化妆镜等商品共八件（共计价值人民币357.3元）。现赃物已起获并发还。（四）2017年12月11日20时许，被告人尹巍在本市海淀区欧美汇购物中心万宁超市内，盗窃橙汁、牛肉干等商品共四件（共计价值人民币58.39元）。现赃物已起获并发还。2017年12月11日，被告人尹巍被公安机关抓获，其到案后如实供述了上述犯罪事实。经鉴定，被告人尹巍被诊断为精神分裂症，限制刑事责任能力，有受审能力。
            上述事实，被告人尹巍及其辩护人在开庭审理过程中亦无异议，并有被告人尹巍的供述，证人侯某、乌某、田某、韩某、赵某、许某的证言，辨认笔录，受案登记表，精神疾病司法鉴定意见书，扣押笔录、扣押决定书、扣押清单，到案经过，户籍资料等证据证实，足以认定本院认为，被告人尹巍以非法占有为目的，多次盗窃他人财物，其行为已构成盗窃罪，应予惩处。
            北京市海淀区人民检察院指控被告人尹巍犯盗窃罪的事实清楚，证据确实充分，指控罪名成立。被告人尹巍到案后能够如实供述自己的犯罪事实，认罪态度好，且赃物均已起获并发还；另外，被告人尹巍系尚未完全丧失辨认或者控制自己行为能力的精神病人，故本院依法对其从轻处罚。辩护人的相关辩护意见本院酌予采纳。
            依照《中华人民共和国刑法》第二百六十四条、第十八条第三款、第六十七条第三款、第五十三条之规定，判决如下被告人尹巍犯盗窃罪，判处有期徒刑九个月，罚金人民币一千元。（刑期从判决执行之日起计算；判决执行以前先行羁押的，羁押一日折抵刑期一日，即自2017年12月11日起至2018年9月10日止。罚金限自本判决生效之次日起十日内缴纳。）
            如不服本判决，可在接到判决书的第二日起十日内，通过本院或者直接向北京市第一中级人民法院提出上诉。书面上诉的，应当提交上诉状正本一份，副本一份
            审判长：于洋
            人民陪审员：袁士芳
            人民陪审员：罗红云
            二〇一八年八月三日
            （院印）
            书记员 杜鹃
            
            【回复的时候请注意】
            1.要给出具体的刑期，精确到几个月。
            2.格式中，部分xx处，如果根据已有信息能确定内容，就补全，否则保留xx的格式。
            3.回复的开头为'现对本案判决如下：'，随后请你以判决书的格式给出你的判罚。
            """
        self.add_to_history("法官", self.get_response(self.judge, judge_prompt))
        self.add_to_history("法官", "本次庭审结束，法警将被告人带出法庭。现在休庭。")
        self.add_to_history("书记员", "全体起立。请审判员退庭。")
        self.add_to_history("书记员", "请公诉人退庭。")
        self.add_to_history("书记员", "旁听人员退庭。")

    def reflect_and_summary(self):
        """
        反思和总结
        """
        self.prosecution.reflect(self.global_history)
        self.defendant.reflect(self.global_history)

    def save_progress(self, index):
        """
        记录运行状态
        :param index: 当前案例索引
        """
        progress = {"current_case_index": index}
        with open("progress.json", "w") as f:
            json.dump(progress, f)

    def load_progress(self):
        """
        加载运行状态
        :return: 运行状态字典或None
        """
        if os.path.exists("progress.json"):
            with open("progress.json", "r") as f:
                return json.load(f)
        return None

    def run_simulation(self, simulation_id=None):
        """
        运行整个法庭模拟过程
        """
        # initialize court
        self.case_data=self.load_json(os.path.join(self.case_data_path,f"example_{simulation_id}", "data.json"))
        prosecution_statement = self.case_data["prosecution_statement"]
        evidence=self.case_data["evidence"]
        debate_focus=self.case_data["debate_focus"]
        self.global_history = []
        console.print("除法官外的其他人员入场", style="bold")
        #preparation stage
        self.preparation_stage()
        #investigation stage
        self.investigation_stage()
        #Presentation_of_evidence stage
        self.evidence_stage()
        #Court_debate stage
        self.debate_stage()
        #Defendant_statement stage
        self.statement_stage()
        
        #end and save
        console.print(f"案例庭审结束", style="bold")
        timestamp = datetime.datetime.now().strftime("%m%d_%H%M")
        # confirm dir exist
        if self.llm.platform == "proxy":
            modelname = self.llm.model
        else:
            modelname = self.llm.platform
        save_dir = f"test_result/{modelname}"
        os.makedirs(save_dir, exist_ok=True)
        
        self.save_court_log(
            f"{save_dir}/case_{simulation_id}_{timestamp}.json"
        )
        self.save_history(0)

    def save_court_log(self, file_path):
        """
        保存法庭日志
        :param file_path: 保存文件路径
        """
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.global_history, f, ensure_ascii=False, indent=2)
        logging.info(f"Court session log saved to {file_path}")

def parse_arguments():
    """
    解析命令行参数
    :return: 解析后的参数
    """
    parser = argparse.ArgumentParser(description="Run a simulated court session.")
    parser.add_argument(
        "--init_config",
        default="settings/example_role_config.json",
        help="Path to the role configuration file",
    )
    parser.add_argument(
        "--stage_prompt",
        default="settings/stage_prompt.json",
        help="Path to the stage prompt file",
    )
    parser.add_argument(
        "--case",
        default="data",
        help="Path to the case data file in JSON format",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--log_think", action="store_true", help="Log the agent think step"
    )
    return parser.parse_args()

def main():
    """
    主函数
    """
    args = parse_arguments()
    simulation = CourtSimulation(args.init_config, args.stage_prompt, args.case,  args.log_level, args.log_think)

if __name__ == "__main__":
    main()
