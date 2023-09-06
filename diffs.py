f1 = '/gws/nopw/j04/esacci_portal/kerchunk/kfiles/esacci12.json'
f2 = 'extracted.json'

with open(f1) as f:
    c1 = f.readlines()[0]

with open(f2) as f:
    c2 = f.readlines()[0]

print(len(c1), len(c2))

for x in range(int(len(c1)/100)):
    if c1[x*100:(x+1)*100] != c2[x*100:(x+1)*100]:
        print(x)
        print(c1[x*100:(x+1)*100])
        print(c2[x*100:(x+1)*100])
        x=input()