# https://people.csail.mit.edu/joe/sctk-1.2/doc/sclite.htm#sclite_name_0
# sclite is an open source tool for analyzing STT results that uses a reference file to calculate substitutions,
# deletions, insertions, Word Error Rate (WER), and Sentence Error Rate (SER) in a file (.sys). It also outputs a detailed
# report (.dtl) and a string alignment file (.prf)

import argparse
import copy
import os
import subprocess
import json
import sys
import logging
from shutil import copyfile
from os.path import join, dirname
from config import Config

import pandas as pd

DEFAULT_CONFIG_INI='config.ini'
DEFAULT_LOGLEVEL='DEBUG'

class Analyzer:
    def __init__(self, config):
        self.config = config

    def create_ctm(self, transcriptions_filename):
        ctm_file = os.path.splitext(transcriptions_filename)[0]+".ctm"
        ctm_entries=[]
        #data = self.transcriptions.getData()
        if transcriptions_filename is not None:
            try:
                if os.path.exists(transcriptions_filename):
                    logging.debug(f"Attempting to create ctm file from transcriptions file - {transcriptions_filename}")
                    transcriptions_df = pd.read_csv(transcriptions_filename)
                    transcriptions_df.sort_values(by="Audio File Name", inplace=True)

                    for audio_file in json.loads(transcriptions_df.to_json(orient='records')):
                        words = str(audio_file["Transcription"]).split()
                        for word in words:
                            ctm_entries.append(audio_file["Audio File Name"].replace(" ", "_") + " 1 0 -1 " + word)
                    
                    self.write_to_file(ctm_entries,ctm_file)
                    logging.info(f"Created ctm file - {ctm_file}")
            except Exception as e:
                logging.exception(f"Failed to create ctm file {ctm_file}:",e)

    def create_stm(self, transcriptions_filename, reference_file_name):
        stm_file = os.path.splitext(transcriptions_filename)[0]+".stm"
        if reference_file_name is not None:
            try:
                if os.path.exists(reference_file_name):
                    logging.debug(f"Found reference transcriptions file - {reference_file_name} - attempting to create stm file")
                    ref_df = pd.read_csv(reference_file_name, usecols = ['Audio File Name','Reference'])
                    ref_df = ref_df.sort_values(by = 'Audio File Name')
                    ref_df.insert(1,"num1",pd.Series([1 for x in range(len(ref_df.index))]))
                    ref_df.insert(2,"num2",pd.Series([0 for x in range(len(ref_df.index))]))
                    ref_df.insert(3,"num3",pd.Series([0 for x in range(len(ref_df.index))]))
                    ref_df.insert(4,"num4",pd.Series([1000 for x in range(len(ref_df.index))]))
                    #write out to file
                    ref_df = ref_df.to_string(header=False,index=False)
                    lines = ref_df.split("\n")
                    new_lines = []
                    for line in lines:
                        new_lines.append(line.lstrip())
                    self.write_to_file(new_lines, stm_file)
                    logging.info(f"Created stm file - {stm_file}")
            except Exception as e:
                logging.exception(f"Failed to create stm file {stm_file}:",e)

    def write_to_file(self, entries, filename):
        with open(filename, "wt", encoding="utf-8") as f:
            for entry in entries:
                f.write(entry + "\n")
    
    def analyze(self, transcriptions_filename, sclite_path):
        results = {'task':[], 'sub':[], 'del':[], 'ins':[], 'wer':[], 'ser':[], 'words':[], 'sentences':[]}

        stm_file = os.path.splitext(os.path.abspath(transcriptions_filename))[0]+".stm"
        ctm_file = os.path.splitext(os.path.abspath(transcriptions_filename))[0]+".ctm"

        result = subprocess.run([sclite_path+'/sclite', '-h', ctm_file, 'ctm', '-r', stm_file, 'stm', '-o', 'prf', 'dtl', 'sum'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sclite_summary_file = ctm_file + '.sys'

        logging.debug(result.stdout.decode('ascii'))

        try:
            with open(sclite_summary_file,'rt') as f:
                        lines = f.readlines()
                        for line in lines:
                            if line.find("Sum") != -1:
                                align = self.get_wer(line)
                                results['task'].append(os.path.basename(os.path.dirname(ctm_file)))                          
                                for cat in ('sub', 'del', 'ins', 'wer', 'words', 'ser', 'sentences'):
                                    results[cat].append(float(align[cat]))   
        except Exception as e:
            logging.exception(f"Could not open {sclite_summary_file}: ", exc_info=e)
            exit() 
        
        columns = {'sub':'Substitutions', 'del':'Deletions', 'ins':'Insertions', 'wer':'Word Error Rate', 'words':'Total Words', 'ser':'Sentence Error Rate', 'sentences':'Total Sentences'}
        df = pd.DataFrame.from_dict(results).rename(columns=columns)

        wer_summary_file=str(os.path.dirname(stm_file)+"/sclite_wer_summary.json")
        df.to_json(wer_summary_file, orient="records")
        logging.info(f"Created summary file - {wer_summary_file}")

        logging.debug("\n"+df.to_markdown(index=False)) 

    def get_wer(self, sclite_str):
        #  "| Sum/Avg|  187    764 | 84.9   11.0    4.1    8.4   23.4   49.2 |"
        elements = sclite_str.replace('|', ' ').split()
        if len(elements) != 9:
            sys.exit("unable to parse: ", sclite_str)
        return {'sentences':elements[1], 'words':elements[2], 'accuracy':elements[3], 'sub':elements[4],
                'del':elements[5], 'ins':elements[6], 'wer':elements[7], 'ser':elements[8]}   

def run(config_file:str, logging_level:str=DEFAULT_LOGLEVEL):
    config      = Config(config_file)
    analyzer    = Analyzer(config)

    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.debug(f"Using config file:{config_file}")

    output_dir = os.path.dirname(config.getValue("ErrorRateOutput", "summary_file"))
    transcriptions_filename = config.getValue("Transcriptions", "stt_transcriptions_file")
    reference_file_name = config.getValue("Transcriptions", "reference_transcriptions_file")
    sclite_directory = config.getValue("ErrorRateOutput", "sclite_directory")

    if output_dir is not None and len(output_dir) > 0:
        os.makedirs(output_dir, exist_ok=True)

    analyzer.create_ctm(transcriptions_filename)
    analyzer.create_stm(transcriptions_filename, reference_file_name)
    analyzer.analyze(transcriptions_filename, sclite_directory)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-c', '--config_file', type=str, default=DEFAULT_CONFIG_INI, help='the config file to use')
    parser.add_argument(
        '-ll', '--log_level', type=str, default=DEFAULT_LOGLEVEL, help='the log level to use')

    args = parser.parse_args()

    run(args.config_file, args.log_level)
