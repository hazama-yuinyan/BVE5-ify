# encoding: utf-8

import sys
import re
import json
from string import Template
from os.path import abspath

# iterate over a sequence and return the index of the first element that satisfies the predicate
# returns -1 if none of the elements match the predicate
def index_of(seq, pred):
    i = 0
    for elem in seq:
        if pred(elem):
            return i
        else:
            i += 1

    return -1

def search_and_replace(input_list, substitution):
    replaced_content_with = u"" if len(substitution["replace"]) == 0 else append_semicolon(substitution["replace"])
    index = index_of(input_list, lambda line: append_semicolon(substitution["search"]) in line)
    input_list[index] = input_list[index].replace(append_semicolon(substitution["search"]), replaced_content_with)
    return input_list

def append_semicolon(str):
    return str + u";"

def make_line_statement(str):
    return u"\t" + str + u";\n"

def add_position(position_map, key, data):
    position_map[key] = map(make_line_statement, data)

def modify(position_map, key, data):
    for item in data:
        if isinstance(item, dict):
            position_map[key] = search_and_replace(position_map[key], item)
        else:
            position_map[key].append(make_line_statement(item))

def main():
    str_section_start = u"\tSection.BeginNew(0, 1, 2, 3, 4);"
    str_beacons = u"\tBeacon.Put(170, 0, 0); Beacon.Put(170, 1, 0); Beacon.Put(170, 2, 0); Beacon.Put(170, 3, 0); Beacon.Put(170, 4, 0);\n"
    original_file_name = sys.argv[1]
    output_file_name = sys.argv[2]

    with open(abspath(original_file_name)) as file:
        file_content = file.readlines()
        assert len(file_content) == 18104, u"ファイルの長さが想定と違います。".encode("cp932")
        assert "BveTs Map 1.00" in file_content[0], u"このスクリプトはバージョン1.00のBVE5用マップファイル向けに作られています。このあとの処理で不具合が発生するかもしれません。".encode("cp932")
        file_content = map(lambda line: unicode(line, "utf-8"), file_content)
        # First, comment out all occurrences of "Beacon.Put", "Section.BeginNew" and "Signal["
        commented_out = map(lambda line: line.replace(u"Beacon.Put(", u"//Beacon.Put(").replace(u"Section.BeginNew(", u"//Section.BeginNew(").replace(u"Signal[", u"//Signal["), file_content)
    
    # Rewrite the speed limit setting
    line_num = index_of(commented_out, lambda elem: u"Signal.SpeedLimit" in elem)
    commented_out[line_num] = u"\tSignal.SpeedLimit(0, 110);\n"

    # Add initial beacons on position 145
    line_num = index_of(commented_out, lambda line: "145;" in line)
    addition_lines = [str_section_start + u"\n", str_beacons, u"\tBeacon.Put(180, 0, 200100);\n", u"\tBeacon.Put(191, 0, 0);\n", u"\tBeacon.Put(192, 0, 33);\n", u"\tBeacon.Put(193, 0, 3);\n", u"\tBeacon.Put(194, 0, 5);\n", u"\tBeacon.Put(176, 0, 30);\n", u"\tBeacon.Put(179, 0, 105);\n"]
    for i in range(len(addition_lines)):
        commented_out.insert(line_num + 1 + i, addition_lines[i])

    # Before further processing, we first create a map from position to the corresponding contents
    position_map = {}; pos_num = -1
    header_end = index_of(commented_out, lambda line: re.match(r"\d+;", line)) # Find the start of the body
    for line in commented_out[header_end:]:
        if re.match(r"\d+;", line):
            if pos_num != -1:
                position_map[pos_num] = tmp_list

            pos_num = int(line.replace(u";", "").replace(u"\n", ""))    # To exclude '\n' and ';'
            tmp_list = []
        else:
            tmp_list.append(line)

    # Do actual modification
    with open(abspath("./modification_data.json")) as json_file:
        modification_data = json.load(json_file)
        tmpl_substitution = modification_data["mapping"]
        body = modification_data["body"]
    
    for pos in body:
        pos_in_int = int(pos)
        try:
            if pos_in_int in position_map:
                modify(position_map, pos_in_int, body[pos])
            else:
                add_position(position_map, pos_in_int, body[pos])
        except Exception as e:
            print ("Error occurred while processing pos:", pos_in_int, ", body:", body[pos])
            print (e.message)
            raise e

    pos_content_pairs = [(pos, content) for (pos, content) in position_map.iteritems()]
    pos_content_pairs.sort(key=lambda x: x[0])    # Use the first item of each tuple for sort key
    result_content = map(lambda elem: (elem[0], map(lambda line: Template(line).substitute(tmpl_substitution), elem[1])), pos_content_pairs)
    
    with open(abspath(output_file_name), "w") as out_file:
        out_file.writelines(commented_out[0 : header_end])

        for pair in result_content:
            out_file.write((append_semicolon(str(pair[0])) + "\n").encode("utf-8"))
            out_file.writelines(map(lambda line: line.encode("utf-8"), pair[1]))


if __name__ == "__main__":
    main()