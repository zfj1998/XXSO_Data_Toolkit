'''
抽取jsonl数据中的code、text部分
'''
import json
from dataset_construct import write_lines
from transformers import AutoTokenizer
from nltk import word_tokenize, wordpunct_tokenize

tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')

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
    result = ' '.join(word_tokenize(tokenizer.decode(tokenizer.encode(integrated)[1:-1]))) 
    result = ' \' '.join(result.split('\''))
    result = ' . '.join(result.split('.')).split()[:510]
    # for codebert
    # result = integrated.strip().split() 
    return result

def construct_data_for_codebert(source_path, target_path, code_only, text_only):
    BODY_KEY = 'src_tokens'
    # BODY_KEY = 'code_tokens'
    TITLE_KEY = 'target_tokens'
    # TITLE_KEY = 'docstring_tokens'
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

if __name__ == '__main__':
    source_path = './data/dataset/python-a3-s2-without-len-limit.{}.jsonl'
    target_path = './data/dataset/python.both.onmt.v2.trunc510.{}.jsonl'
    # for mode in ['valid', 'test', 'train']:
    for mode in ['valid', 'test', 'train']:
        construct_data_for_codebert(source_path.format(mode), target_path.format(mode), False, False)