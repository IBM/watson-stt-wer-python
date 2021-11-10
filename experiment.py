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

import pandas as pd

def run_experiment(config_file, report_dir):

    sensitivity = 0.5

    while sensitivity < 0.8:

        sens = float("{:.1f}".format(sensitivity))

        # Parent Directory path
        experiment_dir = report_dir + "/sens" + str(sens)

        # Path
        path = experiment_dir

        try:
            os.makedirs(path)
            #print("Directory '%s' created successfully" %directory)
        except OSError as error:
            pass
            #print("Directory '%s' can not be created")

        #Copy config.ini to experiment folder
        exp_config_path = path + "/" + "config.ini"
        copyfile(config_file, exp_config_path)

        #Update config settings for the experiment
        exp_config = Config(exp_config_path)
        exp_config.setValue('SpeechToText', 'speech_detector_sensitivity', str(sens))

        details_file=path + "/" + exp_config.getValue('ErrorRateOutput', 'details_file')
        exp_config.setValue('ErrorRateOutput', 'details_file', details_file)

        summary_file=path + "/" + exp_config.getValue('ErrorRateOutput', 'summary_file')
        exp_config.setValue('ErrorRateOutput', 'summary_file', summary_file)

        reference_transcriptions_file=path + "/" + exp_config.getValue('Transcriptions', 'reference_transcriptions_file')
        copyfile(exp_config.getValue('Transcriptions', 'reference_transcriptions_file'), reference_transcriptions_file)
        exp_config.setValue('Transcriptions', 'reference_transcriptions_file', reference_transcriptions_file)

        stt_transcriptions_file=path + "/" + exp_config.getValue('Transcriptions', 'stt_transcriptions_file')
        exp_config.setValue('Transcriptions', 'stt_transcriptions_file', stt_transcriptions_file)

        exp_config.writeFile(exp_config_path)

        #Get Transcriptions
        subprocess.call(["python", "transcribe.py", exp_config_path])

        #Get Analysis
        subprocess.call(["python", "analyze.py", exp_config_path])

        sensitivity = sensitivity + 0.1


def run_report(report_dir):

    # Open summary file for writing
    data_file = open(report_dir + '/experiment_summary.csv', 'w')

    count = 0
    for subdir, dirs, files in os.walk(report_dir):
        for file in files:
            if file == "wer_summary.json":
                #print(os.path.join(subdir, file))

                # Opening JSON file and loading the data
                # into the variable data
                with open(os.path.join(subdir, file)) as json_file:
                    data = json.load(json_file)

                # create the csv writer object
                csv_writer = csv.writer(data_file)

                #for result in data:
                if count == 0:

                    # Writing headers of CSV file
                    print(data)
                    header = data.keys()
                    csv_writer.writerow(header)
                    count += 1

                    # Writing data of CSV file
                csv_writer.writerow(data.values())

    data_file.close()

def main():

    # Create config file for experiment
    config_file = "config.ini"
    if len(sys.argv) > 1:
       config_file = sys.argv[1]
    else:
       print("Using default config filename: config.ini.")

    config = Config(config_file)

    report_dir = os.path.relpath(os.path.dirname(os.path.abspath(__file__)), ".") \
                + "/" + config.getValue("ErrorRateOutput", "report_directory")

    run_experiment(config_file, report_dir)

    run_report(report_dir)

if __name__ == '__main__':
    main()
