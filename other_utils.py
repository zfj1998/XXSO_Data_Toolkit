'''
抽取jsonl数据中的code、text部分
'''
import json
import linecache
from dataset_construct import write_lines
from transformers import AutoTokenizer
from collections import Counter
from nltk import word_tokenize, wordpunct_tokenize
import ipdb

special_tokens_id = list(range(33, 48))
special_tokens_id += list(range(58, 65))
special_tokens_id += list(range(91, 97))
special_tokens_id += list(range(123, 127))
special_tokens = [chr(i) for i in special_tokens_id]

def convention_tokenize(text):
    '''
    针对特殊符号分词
    '''
    for st in special_tokens:
        text = f' {st} '.join(text.split(st)).strip()
    tokens = text.split()
    return tokens

def split_things(content, code_only, text_only):
    if type(content) == str:
        integrated = content
    else:
        integrated = ''
        for i in content:
            if code_only and i[0] == 'code':
                integrated += ' ' + i[1]
            elif text_only and i[0] == 'text':
                integrated += ' ' + i[1]
            elif (not code_only) and (not text_only):
                integrated += ' ' + i[1]
    # for onmt
    # result = ' '.join(convention_tokenize(integrated))[:510]
    # for codebert
    result = convention_tokenize(integrated)
    return result

def construct_data_for_codebert(source_path, target_path, code_only, text_only):
    BODY_KEY = 'code_tokens'
    TITLE_KEY = 'docstring_tokens'
    with open(source_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_json = json.loads(line)
            content = line_json['@Body']
            title = line_json['@Title']
            new_line = {
                BODY_KEY: split_things(content, code_only, text_only),
                TITLE_KEY: split_things(title, code_only, text_only)
            }
            new_line = '{}\n'.format(json.dumps(new_line))
            write_lines([new_line], target_path)

def construct_data_for_onmt(readf,writesrc,writetgt):
    with open(readf,'r', encoding='utf-8') as rf, \
         open(writesrc,'w') as wfs, \
         open(writetgt,'w') as wft:
        for line in rf.readlines():
            line=json.loads(line)
            src=line['code_tokens']
            tgt=line['docstring_tokens']
            try:
                src_word = ' '.join(src).lower()
                wfs.write(f'{src_word}\n')
                tgt_word = ' '.join(tgt).lower()
                wft.write(f'{tgt_word}\n')
            except Exception as e:
                print(e)
                ipdb.set_trace()

def compare_str(str_a, str_b):
    '''
    对字符串分词并比较token集合的交集与两方的重合度
    重合度都高于90%才认为是一样的str
    '''
    set_a = set(convention_tokenize(str_a.lower()))
    set_b = set(convention_tokenize(str_b.lower()))
    inter = set_a & set_b
    ratio_a = len(inter) / len(set_a)
    ratio_b = len(inter) / len(set_b)
    if ratio_a >= 0.99 and ratio_b >= 0.99:
        return True
    return False

def check_match_ratio(matched_path, target_path):
    '''
    比对match的两个str，均去除单引号，然后看token集合的重复率为100%的有多少个
    '''
    matched_lines = linecache.getlines(matched_path)
    count = 0
    with open(target_path, 'w', encoding='utf-8') as f:
        for line in matched_lines:
            line_json = json.loads(line.strip())
            gao_title = line_json['gao-title']
            zfj_title = line_json['zfj-title']
            zfj_title = zfj_title.replace('\'', '')
            # gao_title = gao_title.replace('\'', '')
            zfj_title = zfj_title.replace('\"', '')
            # gao_title = gao_title.replace('\"', '')
            zfj_title = zfj_title.replace('`', '')
            zfj_title = zfj_title.replace('@', '')
            if compare_str(zfj_title, gao_title):
                f.write(line)

def extract_matched_data(matching_basis, zfj_file, gao_code_file, gao_title_file, zfj_target, gao_target):
    '''
    抽取Gao和zfj匹配的数据集，首先观察代码的整齐程度，然后用于CodeBERT和Gaonmt测试
    zfj_file是a1s2等已经清洗完毕的json格式数据，因此本函数的输出为：
        1. zfj_file中抽取出的行组成的文件
        2. gao_title, gao_code组成的文件
    后续要使用这两个文件做数据集的划分以及适配不同模型的数据格式
    '''
    match_info = linecache.getlines(matching_basis)
    zfj_ids = []
    gao_lino = []
    existed_id = set()
    for match in match_info:
        match_json = json.loads(match.strip())
        if match_json['zfj-id'] in existed_id: #去除Gao数据集中的重复项
            continue
        existed_id.add(match_json['zfj-id'])
        zfj_ids.append(match_json['zfj-id'])
        gao_lino.append(match_json['gao-lino'])
    zfj_ids_set = set(zfj_ids)
    gao_lino_set = set(gao_lino)
    assert len(zfj_ids) == len(zfj_ids_set)
    assert len(gao_lino) == len(gao_lino_set)
    zfj_lines = linecache.getlines(zfj_file)
    zfj_lines_dict = {}
    for line in zfj_lines:
        line_json = json.loads(line.strip())
        if not line_json['@Id'] in zfj_ids_set:
            continue
        zfj_lines_dict[line_json['@Id']] = line
    with open(zfj_target, 'w', encoding='utf-8') as f:
        for zfj_id in zfj_ids:
            line = zfj_lines_dict[zfj_id]
            f.write(line)
    with open(gao_target, 'w', encoding='utf-8') as f:
        for lino in gao_lino:  
            gao_code = linecache.getline(gao_code_file, lino)
            gao_code = ''.join([i if ord(i) < 128 else ' ' for i in gao_code])
            gao_title = linecache.getline(gao_title_file, lino)
            line_json = {
                '@Source': f'{gao_code_file}, {gao_title_file}',
                '@Lino': lino,
                '@Title': gao_title,
                '@Body': [['code', gao_code.strip()]]
            }
            line_str = json.dumps(line_json, ensure_ascii=False)
            f.write(f'{line_str}\n')

def split_dataset_by_difficulty():
    '''
    按照tf-idf规则抽取title包含于body的数据
    '''
    pass

if __name__ == '__main__':
    source_path = './data/dataset/all/python-a1-s2-len-lte-1000-match-gao.{}.jsonl'
    target_path = './data/dataset/codebert.python.a1s2.both.lte1000.match-gao.{}.jsonl'
    onmt_src_path = './data/dataset/src.{}.python.a1s2.both.lte1000.match-gao.txt'
    onmt_tgt_path = './data/dataset/tgt.{}.python.a1s2.both.lte1000.match-gao.txt'
    for mode in ['valid', 'test', 'train']:
        construct_data_for_codebert(source_path.format(mode), target_path.format(mode), False, False)
        construct_data_for_onmt(target_path.format(mode), onmt_src_path.format(mode), onmt_tgt_path.format(mode))
    # check_match_ratio('./data/Gao/python/a1s2_matched_tgt_train.jsonl', './data/Gao/python/a1s2_matched_tgt_train.trust.jsonl')
    matching_basis = './data/Gao/python/a1s2_matched_tgt_train.trust.with-repeat.jsonl'
    zfj_file = "./data/dataset/all/python-a1-s2-len-lte-1000.jsonl"
    gao_code_file = './data/Gao/python/src-train-test.txt'
    gao_title_file = './data/Gao/python/tgt-train-test.txt'
    zfj_target = "./data/dataset/all/python-a1-s2-len-lte-1000-match-gao.jsonl"
    gao_target = "./data/dataset/all/python-a1-s2-len-lte-1000-match-gao-code-only.jsonl"
    # extract_matched_data(matching_basis, zfj_file, gao_code_file, gao_title_file, zfj_target, gao_target)


# def check_repeat(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         id_set = set()
#         repeat = []
#         for line in f:
#             line_json = json.loads(line.strip())
#             line_id = line_json['@Id']
#             if line_id in id_set:
#                 repeat.append(line_id)
#             else:
#                 id_set.add(line_id)
#         print(repeat)