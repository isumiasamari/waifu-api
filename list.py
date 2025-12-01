人生list=['game','sex','money',6]
人生list.extend(('friend',8))
人生list.remove('sex')               #对象.方法名()  append是追加的意思
print(人生list)
print(len(人生list))               #len可以求列表元素的数量
print(人生list[3])                 #索引第3个元素

class A:
    def __init__(self):
        print("我被创建了")

A()   # 运行后会打印：我被创建了

blist=[1,15,17,33,35,79,68,28,57,15]
起始 = 0
for a in blist:
    起始 = 起始 + a
print(起始)
典王=('''作为小县城唯一玩过{XX}的人
        {XX}启动
        玩{XX}救了我一命'''.format(XX="鸣潮"))
print(典王)
list=[5,4,4,9,45,54,6,33,31]
a=0
c=0
b=0
print(len(list))
while a<len(list):
    b=list[a]
    c+=b
    a += 1
    d=c/a
print(d)
f=0
g=0
e=0
e = input('请输入数字')
while e != 'q':
    f+=int(e)
    g += 1
    w = f / g
    e = input('请输入数字')
if g==0:
   w=0
else:
   w=f/g
print(w)