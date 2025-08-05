import re
import os
import argparse
import importlib
import sys
sys.path.append('.')

pat2sub = {
    r'file:/ontology': "https://raw.githubusercontent.com/sustainable-processes/KG4DT/refs/heads/dev-alkyne-hydrogenation/ontology",
}

def process_file(path, pat2sub):
    file = open(path, 'r')
    owl = file.read()
    file.close()
    for pat, sub in pat2sub.items():
        owl = re.sub(pat, sub, owl, flags=re.S)
    file = open(path, 'w')
    file.write(owl)
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
        process_folder(args.path, pat2sub)
    if os.path.isfile(args.path):
        process_file(args.path, pat2sub)

if __name__ == "__main__":
    main()