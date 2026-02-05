import configparser
import logging
import os
from typing import Dict, List, Optional, Any, Union

STT_SECTION_KEY="SpeechToText"
TRANSCRIPTIONS_SECTION_KEY="Transcriptions"
OUTPUT_SECTION_KEY="ErrorRateOutput"
TRANSFORMATIONS_SECTION_KEY="Transformations"

class Config:
    def __init__(self, config_file: str):
        # (interpolation=None) so that '%' is not treated like an environment variable
        # inline_comment_prefixes allows comments inline, after the value
        self.config_file = config_file
        self.config = configparser.ConfigParser(interpolation=None, inline_comment_prefixes='#;')
        
        try:
            if not os.path.exists(config_file):
                logging.warning(f"Config file {config_file} not found")
            else:
                self.config.read(config_file)
        except Exception as e:
            logging.error(f"Error reading config file {config_file}: {str(e)}")

    def getBoolean(self, section: str, key: str, default_value: Optional[Any] = None) -> bool:
        return self.getValue(section, key, default_value) == "True"

    def getValue(self, section: str, key: str, default_value: Optional[Any] = None) -> Optional[str]:
        value = None
        if section in self.config:
            section_dict = self.config[section]
            value = section_dict.get(key, default_value)
        return value

    def getKeys(self, section: str) -> Optional[List[str]]:
        if section in self.config:
            return [key for key, value in self.config.items(section)]
        return None

    def setValue(self, section: str, key: str, value: str) -> None:
        if section in self.config:
            self.config.set(section, key, value)
        else:
            # Create section if it doesn't exist
            self.config.add_section(section)
            self.config.set(section, key, value)

    def writeFile(self, file_name: str) -> bool:
        """
        Write the configuration to a file.

        Args:
            file_name: Path to the file to write

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(file_name, 'w') as configfile:
                self.config.write(configfile)
            return True
        except Exception as e:
            logging.error(f"Error writing config to {file_name}: {str(e)}")
            return False
