from datetime import datetime
from datetime import timedelta
from datetime import timezone
import os
import tempfile
import unittest

from pdf_updater import fmt_timestamp
from pdf_updater import KEY_MAP
from pdf_updater import parse_key
from pdf_updater import parse_timestamp_str
from pdf_updater import dict_to_metadata
from pdf_updater import read_metadata
from pdf_updater import write_metadata


class TestKeySignature(unittest.TestCase):

    def test_parse(self):
        # Verify the key output of the parser maps to the expected key
        expected_key = 'C Sharp Major'
        test_data = {
            'C Sharp Major': [
                'C Sharp Major',
                'C♯ Major',
                'C ♯ Major',
                'c ♯    major',
                'c     ♯major',
            ],
            'B Flat Minor': [
                'B Flat Minor',
                'B♭ Minor',
                'B ♭ Minor',
                'b ♭ minor',
                'b ♭    minor',
                'b     ♭minor',
            ],
        }

        for expected_key, inputs in test_data.items():
            for key_str in inputs:
                key = parse_key(key_str)
                self.assertEqual(KEY_MAP[key], expected_key)


class TestTimestamp(unittest.TestCase):

    def test_fmt(self):
        tz = timezone(timedelta(hours=-5), 'EST')
        timestamp = datetime(year=2023, month=12, day=17, hour=10,
                             minute=56, tzinfo=tz)
        timestamp_str = fmt_timestamp(timestamp)
        expected_fmt = "D:20231217105600-05'00'"
        self.assertEqual(timestamp_str, expected_fmt)

    def test_parse(self):
        timestamp_str = "D:20231217105600-05'00'"
        timestamp = parse_timestamp_str(timestamp_str)

        tz = timezone(timedelta(hours=-5), 'EST')
        expected_timestamp = datetime(year=2023, month=12, day=17, hour=10,
                                      minute=56, tzinfo=tz)
        self.assertEqual(timestamp, expected_timestamp)


class TestMetadataConvert(unittest.TestCase):

    def test_transform(self):
        metadata_input = {
            "Composer": "Jeremy Nxxxxxxx",
            "Title": "Sacred Harp Metal Mash",
            "Genre": "Glam Rock",
            "Tags": "awesome drum-solo distortion",
            "Reference": "467",
        }

        # Reference will not be included because I can't find anything about it
        # being handled specifically, in forScore docs:
        #   * https://forscore.co/developers-pdf-metadata/
        expected_output = {
            '/Author': 'Jeremy Nxxxxxxx',
            '/Title': 'Sacred Harp Metal Mash',
            '/Subject': 'Glam Rock',
            '/Keywords': 'awesome drum-solo distortion'
        }

        output = dict(dict_to_metadata(metadata_input))
        self.assertEqual(output, expected_output)


    def test_pdf(self):
        tempf_orig = tempfile.NamedTemporaryFile()
        file_name1 = tempf_orig.name
        filename_modified = os.path.join(os.path.dirname(file_name1), 'modified-%s' % os.path.basename(file_name1))
        metadata_in = dict(item for item in dict_to_metadata({
            "Composer": "Jeremy Nxxxxxxx",
            "Title": "Sacred Harp Metal Mash",
            "Genre": "Glam Rock",
            "Tags": "awesome drum-solo distortion",
        }))
        write_metadata(file_name1, metadata_in)
        metadata_out = read_metadata(filename_modified)
        # PyPDF automatically adds itself as the producer
        metadata_out.pop('/Producer')
        os.unlink(filename_modified)
        print(metadata_in, metadata_out)
        self.assertEqual(metadata_in, metadata_out) 


if __name__ == '__main__':
    unittest.main()
