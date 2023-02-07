import argparse
import os
import sys
import re
import csv
import json
import logging
from shutil import copyfile
from config import Config
import subprocess
import os.path
from os import path
import glob

import pandas as pd

import transcribe
import analyze
import optional_analyze_with_sclite

DEFAULT_CONFIG_INI='config.ini'
DEFAULT_LOGLEVEL='INFO'

class Experiments:
    def __init__(self, config, output_dir):
        self.config = config
        self.output_dir = output_dir

    def run_all_experiments(self, bias_range, weight_range, sds_range, bas_range, max_threads, logging_level):

        # load the metadata config parameters
        metadata_config = Config(self.config.config_file)
        metadata_file=str(metadata_config.getValue("Experiments", "metadata_file"))
        metadata_column=str(metadata_config.getValue("Experiments", "metadata_column"))
        metadata_list=metadata_config.getValue("Experiments", "metadata_list")
        metadata_list=metadata_list.split(",")
        metadata_values = list(metadata_list)

        # metadata file

        if 'xlsx' in metadata_file:
            metadata_df = pd.read_excel(metadata_file)
        else:
            metadata_df = pd.read_csv(metadata_file)

        print("metadata file length: ", len(metadata_df.index))
        print(metadata_df.head(10))            

        weight_values = list(weight_range)
        sds_values = list(sds_range)
        bas_values = list(bas_range)

        for bias in bias_range:
            for weight in weight_values:
                for sds in sds_values:
                    for bas in bas_values:

                        bias = round(bias, 2)
                        weight = round(weight, 2)
                        sds = round(sds, 2)
                        bas = round(bas,2)

                        logging.info(f"Running Experiment -- Character Insertion Bias: {bias}, Customization Weight: {weight}, Speech Detector Sensitivity: {sds}, Background Audio Suppression: {bas}")

                        # need to update the directory name with an if statement for metadata
                        experiment_output_dir = self.output_dir + "/bias_" + str(bias) + "_weight_" + str(weight) + "_sds_" + str(sds) + "_bas_" + str(bas)
                        os.makedirs(experiment_output_dir, exist_ok=True)

                        exp_config_path = experiment_output_dir + "/" + self.config.config_file
                        copyfile(self.config.config_file, exp_config_path)
                        # need to update the reference file with an if statement for metadata

                        #Update config settings for the experiment
                        exp_config = Config(exp_config_path)

                        

                        file_info = os.path.split(exp_config.getValue('Transcriptions', 'stt_transcriptions_file'))
                        stt_transcriptions_file = os.path.join(experiment_output_dir, file_info[1])
                        exp_config.setValue('Transcriptions', 'stt_transcriptions_file', stt_transcriptions_file)

                        file_info = os.path.split(exp_config.getValue('ErrorRateOutput', 'stt_transcriptions_file'))
                        stt_transcriptions_file = os.path.join(experiment_output_dir, file_info[1])
                        exp_config.setValue('ErrorRateOutput', 'stt_transcriptions_file', stt_transcriptions_file)
                                                
                        exp_config.setValue('SpeechToText', "max_threads", str(max_threads))

                        exp_config.setValue('SpeechToText', "speech_detector_sensitivity", str(sds))
                        exp_config.setValue('SpeechToText', "background_audio_suppression", str(bas))
                        exp_config.setValue('SpeechToText', "character_insertion_bias", str(bias))
                        exp_config.setValue('SpeechToText', "customization_weight", str(weight))

                        exp_config.writeFile(exp_config_path)

                        #Get Transcriptions 
                        transcribe.run(exp_config_path, logging_level)

                        # break transcript up depending on metadata
                        transcript_df = pd.read_csv(stt_transcriptions_file)

                        print("transcript length: ", len(transcript_df.index))
                        print(transcript_df.head(10))

                        # remove the directory from the file name so its the same in both dfs
                        transcript_df['Audio File Name'] = transcript_df['Audio File Name'].apply(lambda S:S.rsplit('/',1)[-1])

                        # rename the audio column so its the same in both dfs
                        metadata_df.rename(columns = {'FileName':'Audio File Name'}, inplace=True)

                        # create a new merged df that has the 'Comment' column 
                        transcript_df_new = pd.merge(transcript_df, metadata_df[['Audio File Name', metadata_column]], on="Audio File Name")
                            
                        # loop through metadata values

                        for value in metadata_values:

                            # create new dfs based on desired value
                            value_df = transcript_df_new[transcript_df_new[metadata_column] == value]

                            # remove 'Comment' column
                            del value_df[metadata_column]

                            print("comment: ", value, len(value_df.index))

                            # create new directory with the metadata value
                            experiment_output_dir = self.output_dir + "/bias_" + str(bias) + "_weight_" + str(weight) + "_sds_" + str(sds) + "_bas_" + str(bas)
                            os.makedirs(experiment_output_dir, exist_ok=True)

                            new_output_dir = self.output_dir + f"/{value}" + "/bias_" + str(bias) + "_weight_" + str(weight) + "_sds_" + str(sds) + "_bas_" + str(bas)


                            # new_output_dir = os.path.join(experiment_output_dir, value)
                            os.makedirs(new_output_dir, exist_ok=True)
                            print("new output dir: ", new_output_dir)

                            new_config_path = new_output_dir + "/" + self.config.config_file
                            copyfile(self.config.config_file, new_config_path)

                            #Update config settings for the experiment
                            new_config = Config(new_config_path)

                            # create the new csv files
                            # os.makedirs(f"{self.output_dir}/{value}", exist_ok=True)
                            transcript_info = os.path.split(new_config.getValue("Transcriptions", "stt_transcriptions_file"))
                            new_transcript_file = os.path.join(new_output_dir, transcript_info[1])

                            print("new transcript file: ", new_transcript_file)
                            print("length new transcripts file: ", len(new_transcript_file))

                            value_df.to_csv(new_transcript_file, index=False)

                            # set new file paths with the metadata value for analysis config files 
                            new_config.setValue('ErrorRateOutput', 'stt_transcriptions_file', new_transcript_file)
                            new_config.setValue('Transcriptions', 'stt_transcriptions_file', new_transcript_file)
                            new_config.setValue('Transcriptions', 'reference_transcriptions_file', new_transcript_file)

                            file_info = os.path.split(new_config.getValue('ErrorRateOutput', 'details_file'))
                            details_file = os.path.join(new_output_dir, file_info[1])
                            new_config.setValue('ErrorRateOutput', 'details_file', details_file)

                            file_info = os.path.split(new_config.getValue('ErrorRateOutput', 'summary_file'))
                            summary_file = os.path.join(new_output_dir, file_info[1])
                            new_config.setValue('ErrorRateOutput', 'summary_file', summary_file)

                            file_info = os.path.split(new_config.getValue('ErrorRateOutput', 'word_accuracy_file'))
                            word_accuracy_file = os.path.join(new_output_dir, file_info[1])
                            new_config.setValue('ErrorRateOutput', 'word_accuracy_file', word_accuracy_file)

                            new_config.writeFile(new_config_path)

                            print("new config path: ", new_config_path)

                            # Delete the old experiment directory
                            clear_folder(experiment_output_dir)
                            
                            #Get Analysis
                            if new_config.getValue('ErrorRateOutput', 'sclite_directory') is None:
                                analyze.run(new_config_path, logging_level)
                            else:
                                optional_analyze_with_sclite.run(new_config_path, logging_level)

                            logging.info(f"Experiment Complete \n")

        return metadata_list

    def run_report(self, output_dir, config, metadata_list):
        logging.debug(f"Generating summary report in {output_dir}")

        # Extract all summaries
        if config.getValue('ErrorRateOutput', 'sclite_directory') is None:
            lines = True 
            wer_summary_filename = os.path.split(config.getValue("ErrorRateOutput", "summary_file"))[1]
        else:
            lines = False
            wer_summary_filename = 'sclite_wer_summary.json'
            
        for value in metadata_list:
            summary_files = glob.glob(f"{output_dir}/{value}/**/*{wer_summary_filename}")

            # output_filename = os.path.join(output_dir,value + "_all_summaries.csv")
            output_filename = output_dir + f"/{value}_all_summaries.csv"

            f = open(summary_files[0])
            data = json.load(f)
            df_all = pd.read_json(json.dumps(data), orient='records', lines=lines)

            for file in summary_files[1:]:
                f = open(file)
                data = json.load(f)
                df = pd.read_json(json.dumps(data), orient='records', lines=lines)
                df_all = pd.concat([df_all, df], ignore_index=True)
            
            logging.info("\n"+df_all.to_markdown())
            df_all.to_csv(output_filename, index=False)
            logging.info(f"Generated summary report {output_filename}")

def drange(start, stop, step):
    r = start
    while r < stop:
        yield r
        r += step

def clear_folder(dir):
    logging.debug(f"Deleting directory {dir}")
    if os.path.exists(dir):
        for the_file in os.listdir(dir):
            file_path = os.path.join(dir, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                else:
                    clear_folder(file_path)
                    os.rmdir(file_path)
            except Exception as e:
                logging.exception(f"Could not delete directory {dir}: ", exc_info=e)
                exit() 
        os.rmdir(dir)

def run(config_file:str, logging_level:str=DEFAULT_LOGLEVEL):

    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.debug(f"Using config file:{config_file}")

    config = Config(config_file)

    output_dir = os.path.dirname(config.getValue("ErrorRateOutput", "summary_file"))
    if output_dir is None or len(output_dir) == 0:
        output_dir = "."

    # build generators
    experiments = Experiments(config, output_dir)
    max_threads = int(config.getValue("SpeechToText","max_threads", 1))
    sds_min  = float(config.getValue("Experiments", "sds_min"))
    sds_max  = float(config.getValue("Experiments", "sds_max"))
    sds_step  = float(config.getValue("Experiments", "sds_step"))
    bias_min  = float(config.getValue("Experiments", "bias_min"))
    bias_max  = float(config.getValue("Experiments", "bias_max"))
    bias_step  = float(config.getValue("Experiments", "bias_step"))
    cust_weight_min  = float(config.getValue("Experiments", "cust_weight_min"))
    cust_weight_max  = float(config.getValue("Experiments", "cust_weight_max"))
    cust_weight_step  = float(config.getValue("Experiments", "cust_weight_step"))
    bas_min = float(config.getValue("Experiments", "bas_min"))
    bas_max = float(config.getValue("Experiments", "bas_max"))
    bas_step = float(config.getValue("Experiments", "bas_step"))

    custom_model = str(config.getValue("SpeechToText", "language_model_id"))
    
    bias_range = drange(bias_min, bias_max+bias_step, bias_step)
    weight_range = drange(cust_weight_min, cust_weight_max+cust_weight_step, cust_weight_step) if custom_model!="None" else drange(0.0, 0.1, 0.1)    
    sds_range = drange(sds_min, sds_max+sds_step, sds_step) 
    bas_range = drange(bas_min, bas_max+bas_step, bas_step)
    
    metadata_list = experiments.run_all_experiments(bias_range, weight_range, sds_range, bas_range, max_threads, logging_level)

    experiments.run_report(output_dir, config, metadata_list)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-c', '--config_file', type=str, default=DEFAULT_CONFIG_INI, help='the config file to use')
    parser.add_argument(
        '-ll', '--log_level', type=str, default=DEFAULT_LOGLEVEL, help='the log level to use')

    args = parser.parse_args()

    run(args.config_file, args.log_level)
