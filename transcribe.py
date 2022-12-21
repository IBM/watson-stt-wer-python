from datetime import datetime
import argparse
import json
import os
import sys
import re
import csv
import concurrent.futures
import threading
from config import Config
import logging

from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import IAMTokenManager
from ibm_cloud_sdk_core.authenticators import BearerTokenAuthenticator
from ibm_watson.websocket import RecognizeCallback, AudioSource

import os.path
from os import path

import pandas as pd

from uuid import uuid4

DEFAULT_CONFIG_INI='config.ini'
DEFAULT_LOGLEVEL='DEBUG'

class Transcriptions:
    data = {}

    def add(self, transcriptionKey:str, transcriptionValue:str):
        self.data[transcriptionKey] = transcriptionValue

    def getData(self):
        return self.data

class MyRecognizeCallback(RecognizeCallback):
    audio_file_name = None
    transcriptions = None

    def __init__(self, audio_file_name:str, transcriptions:Transcriptions):
        RecognizeCallback.__init__(self)
        self.audio_file_name = audio_file_name
        self.transcriptions = transcriptions

    def on_data(self, data):
        #print(json.dumps(data, indent=2))
        try:
            transcription = ""
            for result in data['results']:
                transcription += result["alternatives"][0]["transcript"]
            #print(transcription)
            self.transcriptions.add(self.audio_file_name, transcription)
        except:
            logging.exception(f"{self.audio_file_name} - No transcription found")

    def on_error(self, error):
        logging.error(f'{self.audio_file_name} - Recognize Error received: {error}')

    def on_inactivity_timeout(self, error):
        logging.error(f'{self.audio_file_name} - Inactivity timeout: {error}')

class Transcriber:

    def __init__(self, config):
        self.config = config
        self.STT = self.createSTT()
        self.transcriptions = Transcriptions()
        self.audio_types = {}
        self.audio_types["wav"]  = "audio/wav"
        self.audio_types["mp3"]  = "audio/mp3"
        self.audio_types["mpeg"] = "audio/mpeg"
        self.audio_types["ogg"]  = "audio/ogg"
        self.audio_types["webm"]  = "audio/webm"
        self.audio_types["opus"]  = "audio/webm"

    def createSTT(self):
        apikey            = self.config.getValue("SpeechToText", "apikey")
        url               = self.config.getValue("SpeechToText", "service_url")
        use_bearer_token  = self.config.getBoolean("SpeechToText", "use_bearer_token")

        if use_bearer_token != True:
            authenticator = IAMAuthenticator(apikey)
        else:
            iam_token_manager = IAMTokenManager(apikey=apikey)
            bearerToken       = iam_token_manager.get_token()
            authenticator     = BearerTokenAuthenticator(bearerToken)

        speech_to_text = SpeechToTextV1(authenticator=authenticator)

        speech_to_text.set_service_url(url)
        speech_to_text.set_default_headers({'x-watson-learning-opt-out': "true"})
        return speech_to_text

    def getAudioType(self, file:str):
        try:
            filetype = file.lower().split(".")[-1]
            return self.audio_types.get(filetype, None)
        except:
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
            transaction_id=str("{}".format(datetime.now().strftime('%Y%m-%d%H-%M%S-') + str(uuid4())))
            new_headers=self.STT.default_headers
            new_headers['X-Global-Transaction-Id']=transaction_id
            self.STT.set_default_headers(new_headers)
            logging.deubg("--> Transaction ID:", self.STT.default_headers['X-Global-Transaction-Id'])

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
                logging.exception(f"Error transcribing {filename}:",exc_info=e)

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
            except Exception as e:
                logging.warning(f"Failed to merge reference transcriptions into {report_file_name}:", exc_info=e)
                
def run(config_file:str, logging_level:str=DEFAULT_LOGLEVEL):
    config      = Config(config_file)
    transcriber = Transcriber(config)

    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.debug(f"Using config file:{config_file}")

    audio_file_dir    = config.getValue("Transcriptions","audio_file_folder")
    max_threads   = int(config.getValue("SpeechToText","max_threads", 1))

    output_dir = os.path.dirname(config.getValue("ErrorRateOutput", "summary_file"))
    if output_dir is not None and len(output_dir) > 0:
        os.makedirs(output_dir, exist_ok=True)

    files = [audio_file_dir + "/" + f for f in os.listdir(audio_file_dir)]
    total_files=len(files)
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

    transcriber.report()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-c', '--config_file', type=str, default=DEFAULT_CONFIG_INI, help='the config file to use')
    parser.add_argument(
        '-ll', '--log_level', type=str, default=DEFAULT_LOGLEVEL, help='the log level to use')

    args = parser.parse_args()

    run(args.config_file, args.log_level)
