import statistics            #import +  模块的名字
statistics.median([2,5,7,887,54,321,45,5])     #模块名 + 函数名(median是计算中位数的函数)
a=statistics.median([2,5,7,887,54,321,45,5])
print(a)                  #数据个数是偶数  中位数是中间两个数字的平均值


def 萌工口(变量A):
    """根据触发事件返回相应的反应"""
    元组表 = {
        '看到主人': '翘起屁股摇尾巴',
        '被摸头': '发出呼噜声',
        '饿了': '可怜巴巴地看着你',
        '生气': '鼓起脸颊不理你'
    }
    return 元组表.get(变量A, '什么也不做')
print(f"aa={萌工口('看到主人')}")    #花括号将变量括起来

import threading
import time


def 正数():
    for i in range(1, 11):  # 只数到10，方便观察
        print(f"正数: {i}")
        time.sleep(3)


def 倒数():
    for i in range(10, 0, -1):  # 只从10倒数，方便观察
        print(f"倒数: {i}")
        time.sleep(1)

threading.Thread(target=正数, daemon=True)               #创建了一个线程   daemon=ture是附属线程
threading.Thread(target=正数, daemon=True).start()       #启动
threading.Thread(target=倒数).start()                    #创建一个线程并启动
