import re
import os
import argparse
import importlib
import sys
sys.path.append('.')


def process_file(path):
    file = open(path, 'r')
    lines = file.readlines()
    file.close()
    new_lines = []
    matched = False
    for line in lines:
        if "<math>" in line:
            matched = True
        if "</math>" in line:
            matched = False
        if matched:
            if "<math>" in line:
                new_lines.append(line.rstrip())
            elif "</math>" in line:
                new_lines.append(line.lstrip())
            else:
                new_lines.append(line.strip())
        else:
            new_lines.append(line)
    file = open(path, 'w')
    file.writelines(new_lines)
    file.close()

    file = open(path, 'r')
    lines = file.readlines()
    file.close()
    new_lines = []
    for line in lines:
        if ("<math>" in line) and ("<math><mrow>" not in line):
            line = line.replace("<math>", "<math><mrow>")
        if ("</math>" in line) and ("</mrow></math>" not in line):
            line = line.replace("</math>", "</mrow></math>")
        new_lines.append(line)
    file = open(path, 'w')
    file.writelines(new_lines)
    file.close()

def process_folder(path, pat2sub):
    for name in os.listdir(path):
        if name.startswith('.'): continue
        subpath = os.path.join(path, name)
        if os.path.isdir(subpath):
            process_folder(subpath, pat2sub)
        if os.path.isfile(subpath):
            process_file(subpath, pat2sub)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', type=str, help='file or folder for owl files')
    args = parser.parse_args()
    if os.path.isdir(args.path):
        process_folder(args.path)
    if os.path.isfile(args.path):
        process_file(args.path)

if __name__ == "__main__":
    main()