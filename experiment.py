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

def run_experiment(config_file, output_dir, stt_param_name, stt_config_val):

        if type(stt_config_val) == float:
            exp_setting = float("{:.1f}".format(stt_config_val))
        else:
            exp_setting = stt_config_val

        # Set path variables
        experiment_dir = stt_param_name + "_" + str(exp_setting)
        path = output_dir + "/" + stt_param_name + "_" + str(exp_setting)

        #Create Experiment output directory if it doesn't exist
        os.makedirs(path, exist_ok=True)

        #Copy config.ini to experiment folder
        exp_config_path = path + "/" + "config.ini"
        copyfile(config_file, exp_config_path)

        #Update config settings for the experiment
        exp_config = Config(exp_config_path)

        exp_config.setValue('SpeechToText', stt_param_name, str(exp_setting))

        details_file=experiment_dir + "/" + exp_config.getValue('ErrorRateOutput', 'details_file')
        exp_config.setValue('ErrorRateOutput', 'details_file', details_file)

        summary_file=experiment_dir + "/" + exp_config.getValue('ErrorRateOutput', 'summary_file')
        exp_config.setValue('ErrorRateOutput', 'summary_file', summary_file)

        word_accuracy_file=experiment_dir + "/" + exp_config.getValue('ErrorRateOutput', 'word_accuracy_file')
        exp_config.setValue('ErrorRateOutput', 'word_accuracy_file', word_accuracy_file)

        reference_transcriptions_file=path + "/" + exp_config.getValue('Transcriptions', 'reference_transcriptions_file')
        copyfile(exp_config.getValue('Transcriptions', 'reference_transcriptions_file'), reference_transcriptions_file)
        reference_transcriptions_file=experiment_dir + "/" + exp_config.getValue('Transcriptions', 'reference_transcriptions_file')
        exp_config.setValue('Transcriptions', 'reference_transcriptions_file', reference_transcriptions_file)

        stt_transcriptions_file=experiment_dir + "/" + exp_config.getValue('Transcriptions', 'stt_transcriptions_file')
        exp_config.setValue('Transcriptions', 'stt_transcriptions_file', stt_transcriptions_file)

        exp_config.writeFile(exp_config_path)

        #Get Transcriptions
        subprocess.call(["python", "transcribe.py", exp_config_path])

        #Get Analysis
        subprocess.call(["python", "analyze.py", exp_config_path])

def run_all_experiments(config_file, output_dir):

    #Customize this function to process the configuration settings
    #that need to be tested

    #Set variable for stt configuration to iterate through
    sensitivity = 0.3

    #Iterate through possible values of the setting.
    while sensitivity < 0.5:

        #Run the experiment for the specific configuration value
        #You must include the exact name of the stt parameter being tested
        run_experiment(config_file, output_dir, "speech_detector_sensitivity", sensitivity)

        #Move to the next value to be tested
        sensitivity = sensitivity + 0.1


def run_report(output_dir, config):
    print(f"Reporting from {output_dir}")

    # Extract all summaries
    wer_summary_filename = config.getValue("ErrorRateOutput", "summary_file")
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

    output_dir = config.getValue("ErrorRateOutput", "output_directory")

    run_all_experiments(config_file, output_dir)

    run_report(output_dir, config)

if __name__ == '__main__':
    main()
