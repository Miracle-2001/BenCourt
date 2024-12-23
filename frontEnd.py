import gradio as gr
import os
import datetime
import json
import logging

from rich.logging import RichHandler

class frontEnd:
    def __init__(self,):
        pass
        
    @staticmethod
    def setup_logging(log_level):
        """
        设置日志配置
        :param log_level: 日志级别
        """
        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True)],
        )

    @staticmethod
    def load_json(file_path):
        """
        加载JSON文件
        :param file_path: 文件路径
        :return: JSON数据
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def load_case_data(case_path):
        """
        加载案例数据
        :param case_path: 案例文件路径或目录路径
        :return: 包含所有案例数据的列表
        """
        cases = []
        with open(case_path, "r", encoding="utf-8") as file:
            for line in file:
                case = json.loads(line)
                cases.append(case)
        return cases
    
    def plaintiff_response(self,user_input):
        return f" {user_input}" 

    def defendant_response(self,user_input):
        return f" {user_input}" 

    def clerk_response(self,user_input):
        return f" {user_input}"  

    def judge_response(self,user_input):
        return f" {user_input}"
    
    def advocate_response(self,user_input):
        return f" {user_input}"
    
    def update(self,):
        return [self.plaintiff_box, self.defendant_box, self.clerk_box, self.judge_box, self.advocate_box, self.history_all]
    # 院审，启动
    def start_simluation(self,simulation_id):
        self.history_all = ""
        self.history_plaintiff = ""
        self.history_defendant = ""
        self.history_clerk = ""
        self.history_judge=""
        self.history_advocate=""
        self.clear()
        # self.agent_speak("审判长","sdgsdgdgghdfgh")
        self.run_simulation(simulation_id=int(simulation_id))

    # 选择某个agent发言
    def clear(self):
        self.defendant_box=""
        self.plaintiff_box=""
        self.judge_box=""
        self.clerk_box=""
        self.advocate_box=""
        
    def agent_speak(self,role,content):
        # print(role,content)
        self.clear()
        if role == "公诉人":
            response = self.plaintiff_response(content)
            self.plaintiff_box = response
            self.history_plaintiff += f"\n{response}"
            self.history_all += f"公诉人：{response}\n"
        elif role == "被告人":
            response = self.defendant_response(content)
            self.defendant_box = response
            self.history_defendant += f"\n{response}"
            self.history_all += f"被告人：{response}\n"
        elif role == "书记员":
            response = self.clerk_response(content)
            self.clerk_box = response
            self.history_clerk += f"\n{response}"
            self.history_all += f"书记员：{response}\n"
        elif role=="法官":
            # print(content)
            response = self.judge_response(content)
            self.judge_box=response
            self.history_judge+= f"\n{response}"
            self.history_all+=f"法官：{response}\n"
        elif role=="辩护人":
            # print(content)
            response = self.advocate_response(content)
            self.advocate_box=response
            self.history_advocate+= f"\n{response}"
            self.history_all+=f"辩护人：{response}\n"
        else:
            raise ValueError("没有这个角色")
    # 定义存档函数
    def save_history(self,simulation_id=0):
        # 确保 'test_result' 文件夹存在
        os.makedirs('test_result', exist_ok=True)
        
        # 生成带有时间戳的文件名
        timestamp = datetime.datetime.now().strftime("%m%d_%H%M")
        filename = f"test_result/log_ID_{simulation_id}_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.history_all)
            return f"本次庭审记录已保存到 {filename}"
        except Exception as e:
            return f"保存失败: {e}"
    
    
    # 创建 Gradio 界面
    def launch(self,):
        self.history_all = ""
        self.defendant_box=""
        self.plaintiff_box=""
        self.judge_box=""
        self.clerk_box=""
        self.advocate_box=""
        with gr.Blocks() as iface:
            gr.Markdown("<div align='center'>  <font size='70'> Multi-Agent judge-Controlled Chat </font> </div>")
            
            self.simulation_id = gr.Textbox(label="输入您想要模拟的案件编号")
            self.submit_btn = gr.Button("启动！")
            
            with gr.Row():  # 两列布局
                with gr.Column(): # 这一行的第一列，各个角色的发言
                    with gr.Row(equal_height=True):
                        with gr.Column(scale=1, min_width=60):  # 控制图标宽度较小
                            gr.Image("files/gradio_demo/pic/judge.png", label="judge图标", elem_id="judge_icon", width=60, height=60, show_label=False)
                        with gr.Column(scale=4):  # 控制文本框宽度较大
                            self.judge_output = gr.Textbox(label="法官", lines=2, visible=True)
                            # self.judge_output = self.test()
                    with gr.Row(equal_height=True):
                        with gr.Column(scale=1, min_width=60):
                            gr.Image("files/gradio_demo/pic/clerk.png", label="书记员图标", elem_id="clerk_icon", width=60, height=60, show_label=False)
                        with gr.Column(scale=4):  # 控制文本框宽度较大
                            self.clerk_output = gr.Textbox(label="书记员", lines=2, visible=True)
                    with gr.Row(equal_height=True):
                        with gr.Column(scale=1, min_width=60):  # 控制图标宽度较小
                            gr.Image("files/gradio_demo/pic/plaintiff.png", label="原告图标", elem_id="plaintiff_icon", width=60, height=60, show_label=False)
                        with gr.Column(scale=4):  # 控制文本框宽度较大
                            self.plaintiff_output = gr.Textbox(label="公诉人", lines=2, visible=True)
                    with gr.Row(equal_height=True):
                        with gr.Column(scale=1, min_width=60):
                            gr.Image("files/gradio_demo/pic/defendant.png", label="被告图标", elem_id="defendant_icon", width=60, height=60, show_label=False)
                        with gr.Column(scale=4):  # 控制文本框宽度较大
                            self.defendant_output = gr.Textbox(label="被告人", lines=2, visible=True)
                    with gr.Row(equal_height=True):
                        with gr.Column(scale=1, min_width=60):
                            gr.Image("files/gradio_demo/pic/defendant.png", label="被告图标", elem_id="defendant_icon", width=60, height=60, show_label=False)
                        with gr.Column(scale=4):  # 控制文本框宽度较大
                            self.advocate_output = gr.Textbox(label="辩护人", lines=2, visible=True)
                        
                with gr.Column(): # 这一行的第二列，全局对话记录
                    with gr.Row():
                        self.save_btn = gr.Button("存档")
                        self.save_output = gr.Textbox(label="存档状态", lines=1, interactive=False)
                    self.global_output = gr.Textbox(label="全部庭审记录", lines=16, visible=True)
            

            self.submit_btn.click(
                fn=self.start_simluation,
                inputs=self.simulation_id,
                outputs=None #[plaintiff_output, defendant_output, clerk_output, judge_output, global_output]
            )
            self.save_btn.click(
                    fn=self.save_history,
                    inputs=self.simulation_id,
                    outputs=self.save_output
                )
            iface.load(fn=self.update,
               inputs=None, 
               outputs=[self.plaintiff_output, self.defendant_output, self.clerk_output, self.judge_output, self.advocate_output, self.global_output], 
               every=0.5)
            iface.launch()