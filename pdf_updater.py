import csv
from datetime import datetime
import glob
import pathlib
import re
import sys
import os

from pypdf import PdfReader
from pypdf import PdfWriter
from pypdf.errors import EmptyFileError


RE_OFFSET = re.compile("([+-])(\d{2})'(\d{2})'$")

# https://forscore.co/developers-pdf-metadata/

# https://forscore.co/pdf-metadata/
# “author” is used to fill in forScore’s “composer” field, “subject” becomes “genre”, and “keywords” become “tags.”
# Bonus tip: If you want to get really fancy, forScore can read
#     specially-formatted keywords as rating and difficulty. Use the keyword
#     “forScore-difficulty:2” with a number between 1 and 3, or use the keyword
#     “forScore-rating:3” with a number between 1 and 5.
META_MAP = {
    '/Author': 'Composer',
    '/Title': 'Title',
    '/Subject': 'Genre',
    '/Keywords': 'Tags',
    '/rating': 'Rating',
    '/difficulty': 'Difficulty',
    '/rating': 'Rating',
    '/duration': 'Duration',
    # Note: These don't match directly to a single input. Their presence here
    #       is primarily informational.
    '/keysf': 'Key',
    '/keysmi': 'Key',
}

REV_META_MAP = dict((v, k) for (k, v) in META_MAP.items())

FLAT = '♭'
SHARP = '♯'

KEY_MAP = {
    (-7, 0): 'C Flat Major',
    (-6, 0): 'G Flat Major',
    (-5, 0): 'D Flat Major',
    (-4, 0): 'A Flat Major',
    (-3, 0): 'E Flat Major',
    (-2, 0): 'B Flat Major',
    (-1, 0): 'F Major',
    (0, 0): 'C Major',
    (1, 0): 'G Major',
    (2, 0): 'D Major',
    (3, 0): 'A Major',
    (4, 0): 'E Major',
    (5, 0): 'B Major',
    (6, 0): 'F Sharp Major',
    (7, 0): 'C Sharp Major',

    (-7, 1): 'A Flat Minor',
    (-6, 1): 'E Flat Minor',
    (-5, 1): 'B Flat Minor',
    (-4, 1): 'F Minor',
    (-3, 1): 'C Minor',
    (-2, 1): 'G Minor',
    (-1, 1): 'D Minor',
    (0, 1): 'A Minor',
    (1, 1): 'E Minor',
    (2, 1): 'B Minor',
    (3, 1): 'F Sharp Minor',
    (4, 1): 'C Sharp Minor',
    (5, 1): 'G Sharp Minor',
    (6, 1): 'D Sharp Minor',
    (7, 1): 'A Sharp Minor',
}

REV_KEY_MAP = dict((v, k) for (k, v) in KEY_MAP.items())


def parse_key(key):
    key = key.replace(' ', '').lower()

    part1 = key[0].upper()

    if key[1:].startswith(FLAT) or key[1:].startswith('flat'):
        part2 = 'Flat'
    elif key[1:].startswith(SHARP) or key[1:].startswith('sharp'):
        part2 = 'Sharp'
    else:
        part2 = ''

    part3 = 'Major'
    if key.endswith('minor'):
        part3 = 'Minor'
    elif key.endswith('major'):
        part3 = 'Major'
        
    lookup_key = f'{part1} {part2} {part3}'

    return REV_KEY_MAP.get(lookup_key)


def fmt_timestamp(timestamp):
    # https://www.verypdf.com/pdfinfoeditor/pdf-date-format.htm
    #
    #    (D:YYYYMMDDHHmmSSOHH'mm')
    #
    #    where
    #
    #    YYYY is the year
    #    MM is the month
    #    DD is the day (01-31)
    #    HH is the hour (00-23)
    #    mm is the minute (00-59)
    #    SS is the second (00-59)
    #    O is the relationship of local time to Universal Time (UT), denoted by one of the characters +, -, or Z (see below)
    #    HH followed by ' is the absolute value of the offset from UT in hours (00-23)
    #    mm followed by ' is the absolute value of the offset from UT in minutes (00-59)

    #    The quotation mark character (') after HH and mm is part of the
    #    syntax. All fields after the year are optional. (The prefix D:,
    #    although also optional, is strongly recommended.) The default values
    #    for MM and DD are both 01; all other numerical fields default to zero
    #    values. A plus sign (+) as the value of the O field signifies that
    #    local time is later than UT, a minus sign (-) that local time is
    #    earlier than UT, and the letter Z that local time is equal to UT. If
    #    no UT information is specified, the relationship of the specified time
    #    to UT is considered to be unknown. Whether or not the time zone is
    #    known, the rest of the date should be specified in local time.

    offset = timestamp.strftime('%z')
    if offset:
        offset_sign = offset[0]
        offset_hr = offset[1:3] 
        offset_min = offset[3:6]
        fmt_offset = f"{offset_sign}{offset_hr}'{offset_min}'"
    else:
        fmt_offset = ''

    return timestamp.strftime(f"D:%Y%m%d%H%M%S{fmt_offset}")


def parse_timestamp_str(timestamp_str):
    # Transform the offset so that strptime can parse it.
    timestamp_str = RE_OFFSET.sub(r'\1\2\3', timestamp_str)
    return datetime.strptime(timestamp_str, 'D:%Y%m%d%H%M%S%z')


def dict_to_metadata(meta_dict):
    for key, val in meta_dict.items():
        if key == 'Key':
            key_sig = parse_key(val)
            yield ('/keysf', key_sig[0])
            yield ('/keysmi', key_sig[1])
        else:
            meta_key = REV_META_MAP.get(key)
            if meta_key:
                yield (meta_key, val)
            else:
                print('Unknown Key:', key)


def add_filename_prefix(filename, prefix):
    modified_filename = '%s%s' % (prefix, os.path.basename(filename))
    return os.path.join(os.path.dirname(filename), modified_filename)


def read_metadata(filename):
    pdf = PdfReader(filename)
    return pdf.metadata


def write_metadata(filename, metadata):
    filename_modified = add_filename_prefix(filename, 'modified-')
    dst_pdf = PdfWriter()
    try:
        src_pdf = PdfReader(filename)
    except EmptyFileError:
        src_pdf = None
    else:
        for page in src_pdf.pages:
            dst_pdf.add_page(page)

        # Preserve the existing metadata
        dst_pdf.add_metadata(src_pdf.metadata)

    # Add the new metadata
    dst_pdf.add_metadata(metadata)

    # Save the new PDF to a file
    with open(filename_modified, "wb") as f:
        dst_pdf.write(f)


def update_pdfs(pdf_dir, csv_filename):
    with open(csv_filename, newline='') as csvf:
        data = csv.DictReader(csvf)
        for row in data:
            filename = row.pop('Filename')
            file_path = os.path.join(pdf_dir, filename)
            if os.path.isfile(file_path):
                metadata = dict(dict_to_metadata(row))
                write_metadata(file_path, metadata)
            else:
                print("File '{filename}' does not exist. Skipping.")

def init_csv(pdf_dir, csv_filename):
    with open(csv_filename, newline='', mode='w') as csvf:
        headers = ['Filename', 'Title', 'Composer', 'Genre', 'Tags', 'Duration']
        writer = csv.DictWriter(csvf, fieldnames=headers)
        writer.writeheader()
        template = dict((h, None) for h in headers)
        for filepath in pathlib.Path(pdf_dir).glob('*.pdf'):
            template['Filename'] = filepath.name
            print(template)
            writer.writerow(template)


if __name__ == '__main__':
    import argparse

    additional_info = """
PDF_DIR should be a directory containing a series of PDF files, without
subdirectories.

CSV_FILE should be a CSV formatted file, with the first row serving as
column names. At least one column should be named 'Filename', and contain
the name of the PDF file to be updated. The rest of the row should contain
the metadata to be added to the specified file.

Example:

    Filename,Title,Composer,Genre,Tags,Duration
    foo.pdf,Sacred Harp Metal Mash,Jeremy Nxxxxxxx,Glam Rock,"awesome drum-solo guitar-shred easter",17:43


Note:
    If the --init-csv optoin is specified, an initial CSV file will be
    built from the PDF files found in the specified PDF_DIR, and written to
    CSV_FILE. Metadata may then be added to that file, and used in
    subsequent updates.

    """


    parser = argparse.ArgumentParser(
                    formatter_class=argparse.RawDescriptionHelpFormatter,
                    prog='PDF Metadata Writer',
                    description='Writes the metadata specified via a CSV file to matching PDFs',
                    epilog=additional_info)

    parser.add_argument('--init-csv', default=False, action='store_true', dest='init_csv')
    parser.add_argument('csv_file')
    parser.add_argument('pdf_dir')

    options = parser.parse_args()

    if options.init_csv:
        # TODO: Do I actually need to do anything here?
        pass
    elif not os.path.isfile(options.csv_file):
        print('Error: First argument must be a valid file name')
        sys.exit(1)

    if not os.path.isdir(options.pdf_dir):
        print('Error: Second argument must be a valid directory name')
        sys.exit(1)

    if options.init_csv:
        init_csv(options.pdf_dir, options.csv_file)
    else:
        update_pdfs(options.pdf_dir, options.csv_file)

