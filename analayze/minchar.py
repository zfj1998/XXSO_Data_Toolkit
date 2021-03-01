import json
f = open('../matcheddata/tgt-train.json')
# data=json.load(f)

import jsonlines

start=1
end=100
now=start
for line in f.readlines():
    print(line)
    i=json.loads(line)
    title=i['title'].replace(" ","").strip()
    topone=i['top_three_simple'][0]['title'].replace(" ","").strip().lower()
    if title==topone:
        print('ok')
    else:
        print(title)
        print(topone)
    now+=1
    if now==end:
        break

