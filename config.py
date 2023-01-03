import configparser

STT_SECTION_KEY="SpeechToText"
TRANSCRIPTIONS_SECTION_KEY="Transcriptions"
OUTPUT_SECTION_KEY="ErrorRateOutput"
TRANSFORMATIONS_SECTION_KEY="Transformations"

class Config:
    config = None

    def __init__(self, config_file:str):
        # (interpolation=None) so that '%' is not treated like an environment variable
         # inline_comment_prefixes allows comments inline, after the value
        self.config_file = config_file
        self.config = configparser.ConfigParser(interpolation=None, inline_comment_prefixes='#;')
        self.config.read(config_file)

    def getBoolean(self, section, key, default_value=None):
        return self.getValue(section, key, default_value) == "True"

    def getValue(self, section, key, default_value=None):
        value = None
        if section in self.config:
           list = self.config[section]
           value = list.get(key, default_value)
        return value

    def getKeys(self, section):
        if section in self.config:
            return [key for key,value in self.config.items(section)]
        return None

    def setValue(self, section:str, key:str, value:str):
        if section in self.config:
           self.config.set(section, key, value)

    def writeFile(self, file_name:str):
        with open(file_name, 'w') as configfile:
            self.config.write(configfile)

        #value = None
        if section in self.config:
           self.config.set(section, key, value)
        return

    def writeFile(self, file:str):
        #value = None
        with open(file, 'w') as configfile:
            self.config.write(configfile)
        return
