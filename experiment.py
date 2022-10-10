import os
import sys
import re
import csv
import json
from shutil import copyfile
from config import Config
import subprocess
import os.path
from os import path
import glob

import pandas as pd

import transcribe
import analyze

def run_experiment(config_file, output_dir, stt_param_name, stt_config_val):

        if type(stt_config_val) == float:
            exp_setting = float("{:.2f}".format(stt_config_val))
        else:
            exp_setting = stt_config_val

        # Set path variables & create output directory
        experiment_dir = stt_param_name + "_" + str(exp_setting)

        path = output_dir + "/" + stt_param_name + "_" + str(exp_setting)
        os.makedirs(path, exist_ok=True)

        exp_config_path = path + "/" + "config.ini"
        copyfile(config_file, exp_config_path)

        #Update config settings for the experiment
        exp_config = Config(exp_config_path)

        exp_config.setValue('SpeechToText', stt_param_name, str(exp_setting))

        file_info = os.path.split(exp_config.getValue('ErrorRateOutput', 'details_file'))
        details_file = os.path.join(file_info[0], experiment_dir, file_info[1])
        exp_config.setValue('ErrorRateOutput', 'details_file', details_file)

        file_info = os.path.split(exp_config.getValue('ErrorRateOutput', 'summary_file'))
        details_file = os.path.join(file_info[0], experiment_dir, file_info[1])
        exp_config.setValue('ErrorRateOutput', 'summary_file', details_file)

        file_info = os.path.split(exp_config.getValue('ErrorRateOutput', 'word_accuracy_file'))
        details_file = os.path.join(file_info[0], experiment_dir, file_info[1])
        exp_config.setValue('ErrorRateOutput', 'word_accuracy_file', details_file)

        file_info = os.path.split(exp_config.getValue('Transcriptions', 'stt_transcriptions_file'))
        details_file = os.path.join(file_info[0], experiment_dir, file_info[1])
        exp_config.setValue('Transcriptions', 'stt_transcriptions_file', details_file)

        exp_config.writeFile(exp_config_path)

        #Get Transcriptions 
        transcribe.run(exp_config_path)

        #Get Analysis
        analyze.run(exp_config_path)

def run_all_experiments(config_file, output_dir):

    #Customize this function to process the configuration settings
    #that need to be tested

    #Set variable for stt configuration to iterate through
#    customization_weight = 0.1
    character_insertion_bias = 0.0
#    background_audio_suppression = 0.0
#    speech_detector_sensitivity = 0.0

    #Iterate through possible values of the setting.
#    while customization_weight < 1.0:
    while character_insertion_bias < 1.0:
#    while background_audio_suppression < 1.0:
#    while speech_detector_sensitivity < 1.0:

        #Run the experiment for the specific configuration value
        #You must include the exact name of the stt parameter being tested
#        run_experiment(config_file, output_dir, "customization_weight", customization_weight)
        run_experiment(config_file, output_dir, "character_insertion_bias", character_insertion_bias)
#        run_experiment(config_file, output_dir, "background_audio_suppression", background_audio_suppression)
#        run_experiment(config_file, output_dir, "speech_detector_sensitivity", speech_detector_sensitivity)

        #Move to the next value to be tested
#        customization_weight = customization_weight + 0.1
        character_insertion_bias = character_insertion_bias + 0.05
#        background_audio_suppression = background_audio_suppression + 0.05
#        speech_detector_sensitivity = speech_detector_sensitivity + 0.05


def run_report(output_dir, config):
    print(f"Reporting from {output_dir}")

    # Extract all summaries
    wer_summary_filename = os.path.split(config.getValue("ErrorRateOutput", "summary_file"))[1]
    summary_tuples = []
    summary_files = glob.glob(f"{output_dir}/**/*{wer_summary_filename}")
    for file in summary_files:
        with open(file) as json_file:
            summary_tuples.append(json.load(json_file))

    # Open summary file for writing
    output_filename = output_dir + '/experiment_summary.csv'
    with open(output_filename, 'w') as data_file:
        dict_writer = csv.DictWriter(data_file, fieldnames=summary_tuples[0].keys())
        dict_writer.writeheader()
        dict_writer.writerows(summary_tuples)
        print(f"Wrote experiment summary to {output_filename}")

def main():

    # Create config file for experiment
    config_file = "config.ini"
    if len(sys.argv) > 1:
       config_file = sys.argv[1]
    else:
       print("Using default config filename: config.ini.")

    config = Config(config_file)

    output_dir = os.path.dirname(config.getValue("ErrorRateOutput", "summary_file"))
    if output_dir is None or len(output_dir) == 0:
        output_dir = "."
    #print(output_dir)

    run_all_experiments(config_file, output_dir)

    run_report(output_dir, config)

if __name__ == '__main__':
    main()
