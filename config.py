import configparser

STT_SECTION_KEY="SpeechToText"
TRANSCRIPTIONS_SECTION_KEY="Transcriptions"
OUTPUT_SECTION_KEY="ErrorRateOutput"
TRANSFORMATIONS_SECTION_KEY="Transformations"

class Config:
    config = None

    def __init__(self, config_file:str):
        # (interpolation=None) so that '%' is not treated like an environment variable
        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(config_file)

    def getBoolean(self, section, key):
        return self.getValue(section, key) == "True"

    def getValue(self, section, key):
        value = None
        if section in self.config:
           list = self.config[section]
           value = list.get(key, None)
        return value

