from dis import print_instructions

print('"fuck"')
总余额=50000     # 这是一年的消费支出
本月消费=1495
本月余额=总余额-本月消费
print(f'本月余额{本月余额}')
import math   # 求解一元二次方程
a=-1
b=-2
c=3
x1=(-b+math.sqrt(b**2-4*a*c))/(2*a)
x2=(-b-math.sqrt(b**2-4*a*c))/(2*a)
print(x1,x2)
print(5,'nihao',x2,x1)
c = 'hello0oooo'[5]
print(c)
print(len('01234567'))
print(type(c))
print(a+2)
import random
from datetime import datetime, timedelta,date
from dateutil.relativedelta import relativedelta

今天 = date.today()
今年 = 今天.year

print(f'今天是{今天}')

class 纸片人老婆:
   def __init__(self,name,age,seikaku):
       self.name = name
       self.age = max(age, 18)
       self.seikaku = seikaku
       self.心情 =['开心','失落','欲求不满','惊讶','无聊','害羞']
       self.数值状态={
       '身高' : 143,
       '体重' : 38,
       '亲密度' : 70 ,
       '体力' : 70 ,
       'inran' : 70,
       '饱食度' : 80
       }

       self.出生时间 = datetime(2025,11,19,8,40)
       self.生日=date(2025,11,19)

   def 调整(self, 数值类型, 变化量,):
           旧值 = self.数值状态[ 数值类型]
           新值 = 旧值 + 变化量
           self.数值状态[ 数值类型] = max(0, min(100, 新值))
           return self.数值状态[ 数值类型] - 旧值      # 返回实际变化量
   def 活动(self,心情参数):
       心情表 = {
           '开心':'蹦蹦跳跳',
           '失落':'卷起身子',
           '欲求不满':'用桌角0721',
           '惊讶':'张嘴瞪眼',
           '无聊':'抱怨',
           '害羞':'低头用手扯住裙角'
       }
       return 心情表.get(心情参数,'不知道做什么')

   def 更新心情(self):
       心情条件 = {
           "无聊": self.数值状态["体力"] < 20,
           "失落": self.数值状态["饱食度"] < 90,
           "欲求不满": self.数值状态["inran"] > 80
       }
       # 查找满足条件的第一个心情
       for 心情类型, 条件 in 心情条件.items():
           if 条件:
               心情 = 心情类型
               break
       else:
           # 如果没有条件满足，随机选择心情
           心情 = random.choice(["开心", "无聊", "害羞"])

       return f'{self.name}今天的心情是{心情} {self.活动(心情)}'

麻毬=纸片人老婆('麻毬',14,'萌')

print(f'{麻毬.更新心情()}')
