'''
抽取jsonl数据中的code、text部分
'''
import json
from dataset_construct import write_lines
from transformers import AutoTokenizer
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
                ipdb.set_trace()

if __name__ == '__main__':
    source_path = './data/dataset/all/python-a3-s2-len-lte-1000.{}.jsonl'
    target_path = './data/dataset/codebert.python.a3s2.both.lte1000.{}.jsonl'
    onmt_src_path = './data/dataset/src.{}.python.a3s2.both.lte1000.txt'
    onmt_tgt_path = './data/dataset/tgt.{}.python.a3s2.both.lte1000.txt'
    # for mode in ['valid', 'test', 'train']:
    for mode in ['valid', 'test', 'train']:
        # construct_data_for_codebert(source_path.format(mode), target_path.format(mode), False, False)
        construct_data_for_onmt(target_path.format(mode), onmt_src_path.format(mode), onmt_tgt_path.format(mode))