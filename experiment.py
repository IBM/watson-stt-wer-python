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

DEFAULT_CONFIG_INI='config.ini'
DEFAULT_LOGLEVEL='INFO'

class Experiments:
    def __init__(self, config, output_dir):
        self.config = config
        self.output_dir = output_dir

    def run_all_experiments(self, bias_range, weight_range, sds_range, bas_range, max_threads, logging_level):
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

                        experiment_output_dir = self.output_dir + "/" + str(bias) + "_" + str(weight) + "_" + str(sds) + "_" + str(bas)
                        os.makedirs(experiment_output_dir, exist_ok=True)

                        exp_config_path = experiment_output_dir + "/" + self.config.config_file
                        copyfile(self.config.config_file, exp_config_path)

                        #Update config settings for the experiment
                        exp_config = Config(exp_config_path)

                        file_info = os.path.split(exp_config.getValue('ErrorRateOutput', 'details_file'))
                        details_file = os.path.join(experiment_output_dir, file_info[1])
                        exp_config.setValue('ErrorRateOutput', 'details_file', details_file)

                        file_info = os.path.split(exp_config.getValue('ErrorRateOutput', 'summary_file'))
                        summary_file = os.path.join(experiment_output_dir, file_info[1])
                        exp_config.setValue('ErrorRateOutput', 'summary_file', summary_file)

                        file_info = os.path.split(exp_config.getValue('ErrorRateOutput', 'word_accuracy_file'))
                        word_accuracy_file = os.path.join(experiment_output_dir, file_info[1])
                        exp_config.setValue('ErrorRateOutput', 'word_accuracy_file', word_accuracy_file)

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

                        #Get Analysis
                        analyze.run(exp_config_path, logging_level)

                        logging.info(f"Experiment Complete \n")




    def run_report(self, output_dir, config):
        logging.debug(f"Generating summary report in {output_dir}")

        # Extract all summaries
        wer_summary_filename = os.path.split(config.getValue("ErrorRateOutput", "summary_file"))[1]
        summary_tuples = []
        summary_files = glob.glob(f"{output_dir}/**/*{wer_summary_filename}")
        for file in summary_files:
            with open(file) as json_file:
                summary_tuples.append(json.load(json_file))

        # Open summary file for writing
        output_filename = output_dir + '/all_summaries.csv'
        with open(output_filename, 'w') as data_file:
            dict_writer = csv.DictWriter(data_file, fieldnames=summary_tuples[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(summary_tuples)
            logging.info(f"Wrote consolidated summary to {output_filename}")

def drange(start, stop, step):
    r = start
    while r < stop:
        yield r
        r += step

def run(config_file:str, logging_level:str=DEFAULT_LOGLEVEL):

    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.debug(f"Using config file:{config_file}")

    config = Config(config_file)

    output_dir = os.path.dirname(config.getValue("ErrorRateOutput", "summary_file"))
    if output_dir is None or len(output_dir) == 0:
        output_dir = "."
    #print(output_dir)

    #run_all_experiments(config_file, output_dir)

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
    weight_range = drange(cust_weight_min, cust_weight_max+cust_weight_step, cust_weight_step) if custom_model==None else drange(0.0, 0.1, 0.1)
    sds_range = drange(sds_min, sds_max+sds_step, sds_step) 
    bas_range = drange(bas_min, bas_max+bas_step, bas_step)
    
    experiments.run_all_experiments(bias_range, weight_range, sds_range, bas_range, max_threads, logging_level)

    experiments.run_report(output_dir, config)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-c', '--config_file', type=str, default=DEFAULT_CONFIG_INI, help='the config file to use')
    parser.add_argument(
        '-ll', '--log_level', type=str, default=DEFAULT_LOGLEVEL, help='the log level to use')

    args = parser.parse_args()

    run(args.config_file, args.log_level)
