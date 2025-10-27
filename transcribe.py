from datetime import datetime
import argparse
import json
import os
import sys
import re
import csv
import concurrent.futures
import threading
from typing import Dict, List, Optional, Any
from config import Config
import logging

from ibm_watson import SpeechToTextV1
from ibm_watson.websocket import RecognizeCallback, AudioSource
from auth import create_stt_service

import os.path
from os import path

import pandas as pd

from uuid import uuid4

DEFAULT_CONFIG_INI='config.ini'
DEFAULT_LOGLEVEL='DEBUG'

FILE_EXTENSIONS = ("mp3", "mpeg", "ogg", "wav", "webm", "opus")

class Transcriptions:
    """
    Class to store and manage transcription results.
    """
    def __init__(self):
        self.data: Dict[str, str] = {}

    def add(self, transcriptionKey: str, transcriptionValue: str) -> None:
        """
        Add a transcription result.

        Args:
            transcriptionKey: Audio file name
            transcriptionValue: Transcription text
        """
        self.data[transcriptionKey] = transcriptionValue

    def getData(self) -> Dict[str, str]:
        """
        Get all transcription results.

        Returns:
            Dict mapping audio file names to transcriptions
        """
        return self.data

class MyRecognizeCallback(RecognizeCallback):
    """
    Callback handler for Watson STT websocket recognition.
    """

    def __init__(self, audio_file_name: str, transcriptions: Transcriptions):
        RecognizeCallback.__init__(self)
        self.audio_file_name: str = audio_file_name
        self.transcriptions: Transcriptions = transcriptions
        logging.debug(f"Initialized callback for {audio_file_name}")

    def on_data(self, data):
        #print(json.dumps(data, indent=2))
        try:
            transcription = ""
            for result in data['results']:
                transcription += result["alternatives"][0]["transcript"]
            #print(transcription)
            self.transcriptions.add(self.audio_file_name, transcription)
        except KeyError as e:
            logging.exception(f"{self.audio_file_name} - Missing key(s) in transcription data: {e}")
        except Exception as e:
            logging.exception(f"{self.audio_file_name} - Error processing transcription: {e}")

    def on_error(self, error):
        logging.error(f'{self.audio_file_name} - Recognize Error received: {error}')
        logging.exception(f"Error transcribing {self.audio_file_name}:",exc_info=error)

    def on_inactivity_timeout(self, error):
        logging.error(f'{self.audio_file_name} - Inactivity timeout: {error}')

class Transcriber:

    def __init__(self, config):
        self.config = config
        self.STT = create_stt_service(config)
        self.transcriptions = Transcriptions()
        self.audio_types = {}
        self.audio_types["wav"]  = "audio/wav"
        self.audio_types["mp3"]  = "audio/mp3"
        self.audio_types["mpeg"] = "audio/mpeg"
        self.audio_types["ogg"]  = "audio/ogg"
        self.audio_types["webm"]  = "audio/webm"
        self.audio_types["opus"]  = "audio/webm"

    def getAudioType(self, file: str) -> Optional[str]:
        try:
            filetype = file.lower().split(".")[-1]
            return self.audio_types.get(filetype, None)
        except (IndexError, AttributeError) as e:
            logging.debug(f"Error determining audio type for {file}: {e}")
            return None

    def transcribe(self, filename):
        logging.debug(f"Transcribing file: {filename}")

        #Model connection configs
        base_model                = self.config.getValue("SpeechToText", "base_model_name")
        language_customization_id = self.config.getValue("SpeechToText", "language_model_id")
        acoustic_customization_id = self.config.getValue("SpeechToText", "acoustic_model_id")
        grammar_name              = self.config.getValue("SpeechToText", "grammar_name")

        #Float parameter configs
        end_of_phrase_silence_time   = float(self.config.getValue("SpeechToText", "end_of_phrase_silence_time"))
        inactivity_timeout           =   int(self.config.getValue("SpeechToText", "inactivity_timeout"))
        speech_detector_sensitivity  = float(self.config.getValue("SpeechToText", "speech_detector_sensitivity"))
        background_audio_suppression = float(self.config.getValue("SpeechToText", "background_audio_suppression"))
        character_insertion_bias     = float(self.config.getValue("SpeechToText", "character_insertion_bias", 0.0))
        smart_formatting_version     =   int(self.config.getValue  ("SpeechToText", "smart_formatting_version", 0))
        if language_customization_id is not None:
            customization_weight         = float(self.config.getValue("SpeechToText", "customization_weight"))
        else:
            customization_weight = None

        #Boolean configs
        interim_results              = self.config.getBoolean("SpeechToText", "interim_results")
        audio_metrics                = self.config.getBoolean("SpeechToText", "audio_metrics")
        smart_formatting             = self.config.getBoolean("SpeechToText", "smart_formatting")
        low_latency                  = self.config.getBoolean("SpeechToText", "low_latency")
        skip_zero_len_words          = self.config.getBoolean("SpeechToText", "skip_zero_len_words")
        custom_transaction_id        = self.config.getBoolean("SpeechToText", "custom_transaction_id")

        callback = MyRecognizeCallback(filename, self.transcriptions)

        if custom_transaction_id:
            transaction_id = str("{}".format(datetime.now().strftime('%Y%m-%d%H-%M%S-') + str(uuid4())))
            new_headers = self.STT.default_headers.copy() if self.STT.default_headers else {}
            new_headers['X-Global-Transaction-Id'] = transaction_id
            self.STT.set_default_headers(new_headers)
            logging.debug(f"--> Transaction ID: {transaction_id}")

        #print(f"Requesting transcription of {filename}")
        with open(filename, "rb") as audio_file:
            try:
                self.STT.recognize_using_websocket(audio=AudioSource(audio_file),
                    content_type=self.getAudioType(filename),
                    recognize_callback=callback,
                    model=base_model,
                    language_customization_id=language_customization_id,
                    acoustic_customization_id=acoustic_customization_id,
                    grammar_name=grammar_name,
                    end_of_phrase_silence_time=end_of_phrase_silence_time,
                    inactivity_timeout=inactivity_timeout,
                    speech_detector_sensitivity=speech_detector_sensitivity,
                    background_audio_suppression=background_audio_suppression,
                    smart_formatting=smart_formatting,
                    smart_formatting_version=smart_formatting_version,
                    low_latency=low_latency,
                    skip_zero_len_words=skip_zero_len_words,
                    character_insertion_bias=character_insertion_bias,
                    customization_weight=customization_weight,
                    #At most one of interim_results and audio_metrics can be True
                    interim_results=interim_results,
                    audio_metrics=audio_metrics
                )
                #print(f"Requested transcription of {filename}")
            except Exception as e:
                logging.exception(f"Error transcribing {filename}: {str(e)}")

    def report(self):
        report_file_name = self.config.getValue("Transcriptions", "stt_transcriptions_file")
        csv_columns = ['Audio File Name','Transcription']
        #print(self.transcriptions.getData())
        data = self.transcriptions.getData()

        with open(report_file_name, 'w', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(csv_columns)
            writer.writerows(data.items())
            logging.info(f"Wrote transcriptions for {len(data)} audio files to {report_file_name}")

        reference_file_name = self.config.getValue("Transcriptions", "reference_transcriptions_file")
        if reference_file_name is not None:
            try:
                if path.exists(reference_file_name):
                    logging.debug(f"Found reference transcriptions file - {reference_file_name} - attempting merge with model's transcriptions")

                    file1_df = pd.read_csv(report_file_name)
                    file2_df = pd.read_csv(reference_file_name)

                    missing_columns = False
                    if not "Audio File Name" in file2_df.columns:
                        missing_columns = True
                        logging.warning(f"'Audio File Name' column missing in reference transcriptions file {reference_file_name}; will not merge.")

                    if not "Reference" in file2_df.columns:
                        missing_columns = True
                        logging.warning(f"'Reference' column missing in reference transcriptions file {reference_file_name}; will not merge.")

                    if not missing_columns:
                        file2_df = file2_df[["Audio File Name", "Reference"]]

                        # Perform outer join merge
                        comparison_result = pd.merge(file1_df,file2_df, on='Audio File Name', how='outer')
                        #print(comparison_result)

                        comparison_result.to_csv(report_file_name, index=False)
                        logging.info(f"Updated {report_file_name} with reference transcriptions")
            except (FileNotFoundError, pd.errors.EmptyDataError) as e:
                logging.warning(f"Failed to read reference transcriptions file: {e}")
            except Exception as e:
                logging.warning(f"Failed to merge reference transcriptions into {report_file_name}: {str(e)}")
                
def run(config_file:str, logging_level:str=DEFAULT_LOGLEVEL):
    config      = Config(config_file)
    transcriber = Transcriber(config)

    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.debug(f"Using config file:{config_file}")

    audio_file_dir = config.getValue("Transcriptions","audio_file_folder") or ""
    max_threads = int(config.getValue("SpeechToText","max_threads", 1) or 1)

    summary_file = config.getValue("ErrorRateOutput", "summary_file") or ""
    output_dir = os.path.dirname(summary_file) if summary_file else ""
    if output_dir and len(output_dir) > 0:
        os.makedirs(output_dir, exist_ok=True)

    files = []
    skipped = []
    for f in os.listdir(audio_file_dir):
        if f.endswith(FILE_EXTENSIONS):
            files.append(os.path.join(audio_file_dir, f))
        else:
            skipped.append(os.path.join(audio_file_dir, f))

    if len(files) < len(os.listdir(audio_file_dir)):
        logging.warning("Skipping files in the audio file directory due to invalid file extensions: " + str(skipped))

    total_files=len(files)

    if total_files>0:
        complete_files=0
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            #executor.map(transcriber.transcribe,files)
            futures = [executor.submit(transcriber.transcribe, file) for file in files]
            for future in concurrent.futures.as_completed(futures):
                complete_files+=1
                if complete_files%100==0:
                    logging.info(f"Completed transcribing {complete_files} files out of {total_files}")
    
        if complete_files != total_files:
            logging.error(f"Only {complete_files} out of {total_files} were transcribed.")
        else:
            logging.info(f"Completed transcribing {complete_files} files out of {total_files}")
    else:
        logging.error("There were no valid audio files found. Exiting.")
        sys.exit(1)

    transcriber.report()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-c', '--config_file', type=str, default=DEFAULT_CONFIG_INI, help='the config file to use')
    parser.add_argument(
        '-ll', '--log_level', type=str, default=DEFAULT_LOGLEVEL, help='the log level to use')

    args = parser.parse_args()

    run(args.config_file, args.log_level)
