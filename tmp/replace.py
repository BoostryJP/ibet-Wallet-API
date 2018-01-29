#coding:utf-8

f = open('MyCoin.sol','r')
Allf = f.read()
text = Allf.replace('\n','')
text = text.replace('\r','')
print(text)

f.close()
