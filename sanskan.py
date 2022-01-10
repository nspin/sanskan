import sys
import re
import glob
import json
from pathlib import Path
from argparse import ArgumentParser, FileType

def main():
    parser = ArgumentParser()
    parser.add_argument('query_file', metavar='QUERY_FILE', type=FileType('r'))
    args = parser.parse_args()

    try:
        query_obj = json.load(args.query_file)
    except json.JSONDecodeError as e:
        print('Error decoding JSON from {}: {}'.format(args.query_file.name, e), file=sys.stderr)
        sys.exit(1)

    try:
        query = Query(query_obj)
    except QueryDeserializeError as e:
        print('Error deserializing query from {}: {}'.format(args.query_file.name, e), file=sys.stderr)
        sys.exit(1)

    print('query: {}'.format(query))

    query.run()

class QueryDeserializeError(Exception):
    pass

class Query:

    def __init__(self, obj):
        if 'directory' not in obj:
            raise QueryDeserializeError('missing "directory" key')
        if not isinstance(obj['directory'], str):
            raise QueryDeserializeError('"directory" must be a string')
        if 'fragments' not in obj:
            raise QueryDeserializeError('missing "fragments" key')
        if not isinstance(obj['fragments'], list) or not all(isinstance(s, str) for s in obj['fragments']):
            raise QueryDeserializeError('"fragments" must be a list of strings')

        self.directory = Path(obj['directory'])
        self.fragments = obj['fragments']

        flags = re.IGNORECASE
        self.fragment_regexes = [ re.compile(re.escape(fragment), flags) for fragment in self.fragments ]

    def __str__(self):
        conjunction = ' & '.join('{}'.format(repr(fragment)) for fragment in self.fragments)
        return "[ {} ] in {}".format(conjunction, self.directory)

    def search_text(self, text):
        for regex in self.fragment_regexes:
            match = regex.search(text)
            if match is None:
                return False
        return True

    def run(self):
        if not self.directory.is_dir():
            print('Error: {} is not a directory'.format(self.directory), file=sys.stderr)
            sys.exit(1)

        num_matches = 0

        text_paths = self.directory.glob('**/*.htm')
        for text_path in text_paths:
            with open(text_path) as f:
                text = f.read()
            if self.search_text(text):
                print('match: {}'.format(text_path))
                num_matches += 1

        print('summary: {} matches'.format(num_matches))
    
if __name__ == '__main__':
    main()
