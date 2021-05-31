import unittest
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

if __name__ == '__main__':
    unittest.main()
