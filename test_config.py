from re import S
import unittest, os
from config import Config


def getInstance():
    return Config('config.ini.sample')

class MyTest(unittest.TestCase):
    def test_get_value(self):
        c = getInstance()
        self.assertEqual(c.getValue('SpeechToText','base_model_name'), 'en-US_NarrowbandModel')

    def test_get_missing_section(self):
        c = getInstance()
        self.assertEqual(c.getValue('NotARealSection','NotARealKey'), None)

    def test_get_missing_key(self):
        c = getInstance()
        self.assertEqual(c.getValue('SpeechToText', 'NotARealKey'), None)

    def test_get_boolean_false(self):
        c = getInstance()
        self.assertEqual(c.getBoolean('SpeechToText', 'use_bearer_token'), False)

    def test_get_boolean_true(self):
        c = getInstance()
        self.assertEqual(c.getBoolean('Transformations', 'remove_empty_strings'), True)

    def test_get_value_with_percent(self):
        c = getInstance()
        self.assertEqual(c.getValue('Transformations','remove_word_list'), 'uh,uhuh,%hesitation,hesitation')

    def test_set_value_with_key(self):
        c = getInstance()
        c.setValue('SpeechToText','smart_formatting', 'True')
        self.assertEqual(c.getValue('SpeechToText', 'smart_formatting'), 'True')

    def test_write_file(self):
        c = getInstance()
        c.writeFile('config.ini.unit_test')
        self.assertEqual(Config('config.ini.unit_test').getValue('SpeechToText','base_model_name'), 'en-US_NarrowbandModel')
        os.remove('config.ini.unit_test')

    
if __name__ == '__main__':
    unittest.main()
