N = '麻毬'
age = 33
#环境影响身体状态, 身体状态影响行动力
环境 = {
        '温度': 25,  # 温度
        '湿度': 50,     # 湿度
        '光色': 70,  # 0是冷100是暖
        '亮度': 50,   #亮度值
        '噪音': 80,        # 噪音
        '空气质量': 65,   # 空气质量
        '人际关系':20
    }
身体状态 = {
    '大脑状态': 20,
    '清洁程度':35,
    '口腔状态':50,     #尤其是喝完豆浆之类的饮品后要注意,睡前要清理
    '腹痛': 20,
    '饱食度': 50,
    '疲惫': 40,
    '心情': 30,
    '指甲长度':60,
    '头皮瘙痒':50,
    '口渴': 45,
    '心情':40
    }
def 觅食():
    身体状态['饱食度']=95
    return 身体状态['饱食度']
def 关窗():
    环境['噪音'] -= 40
    环境['空气质量'] -=15
    return f'当前环境噪音为{环境['噪音']} 空气质量为{环境['空气质量']}'
def 行动力():
    a=身体状态['饱食度']
    b=身体状态['心情']
    行动力=a-b
    return f'行动力为{行动力}'
关窗后=关窗()
print(f'关窗后 {关窗后}')
print(行动力())
饭后=觅食()
print(f'饭后{行动力()}')
p=print
p("Nihao")

import tkinter as tk
from PIL import Image, ImageTk


class 纸片人老婆界面:
    def __init__(self):
        self.主窗口 = 主窗口
        self.主窗口.title("麻毬老婆系统")

        # 载入图片
        self.普通图 = ImageTk.PhotoImage(Image.open("image/girl_happy.png"))
        self.动作图 = ImageTk.PhotoImage(Image.open("image/girl_sleepy.png"))

        # 当前显示的图片标签
        self.图片标签 = tk.Label(self.主窗口, image=self.普通图)
        self.图片标签.pack(side="left")

        # 按钮：执行动作
        self.按钮 = tk.Button(self.主窗口, text="执行动作", command=self.切换到动作图)
        self.按钮.pack()

        # 按钮：恢复普通状态
        self.按钮2 = tk.Button(self.主窗口, text="恢复", command=self.切换到普通图)
        self.按钮2.pack()

    def 切换到动作图(self):
        self.图片标签.config(image=self.动作图)

    def 切换到普通图(self):
        self.图片标签.config(image=self.普通图)


# 创建主窗口
主窗口 = tk.Tk()

# 创建界面对象并绑定主窗口
老婆 = 纸片人老婆界面()

# 进入消息循环
主窗口.mainloop()