import json
f = open('./py-tgt-train.json')
# data=json.load(f)

import jsonlines

# 有相同的标题的为止
ok=0
# now=1
match_count=0
not_match_count=0
match_file_path='./match-pytgt-train.json'
notmatch_file_path='./notmatch-pytgt-train.json'

linedex=1
with open(match_file_path,mode="w",encoding="utf-8") as mfw:
    with open(notmatch_file_path,mode="w",encoding="utf-8") as nmfw:
        for line in f.readlines():
            i=json.loads(line)
            title=i['title']
            title1=title.replace(" ","").strip()#夏新数据末尾\n删去
            topone=i['top_three_simple'][0]['title'].lower()#全部转换为小写，因为夏新的就是小写
            topone1=topone.replace(" ","").replace("'","").replace("\"","").replace("``","").replace("@","")
            #去除特殊符号，夏新的问题中应该也去除了特殊符号
            # 产生json格式记录
            line_dict={}
            line_dict["title"] = title
            line_dict["top_three_simple"]=i['top_three_simple']
            line_dict['linedex']=linedex
            line_json = json.dumps(line_dict)
            linedex+=1
            if title1==topone1:
                # 匹配的情况下的记录写入文件
                mfw.write(line_json + '\n') 
                match_count+=1
                # print('ok')
                ok=1
            else:
                nmfw.write(line_json + '\n')
                not_match_count+=1
                print("___________________________")
                print(title)
                print(topone)
                # print("-----------------------------")
        print('match count:',match_count)
        print('not match count:',not_match_count)


        nmfw.close()              
    mfw.close()
