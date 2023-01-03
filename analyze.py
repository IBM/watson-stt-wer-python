# Repo: https://pypi.org/project/jiwer/
# Simple python package to approximate the Word Error Rate (WER), Match Error Rate (MER), Word Information Lost (WIL) and Word Information Preserved (WIP) of a transcript.
# - WER (word error rate), commonly used in ASR assessment, measures the cost of restoring the output word sequence to the original input sequence.
# - MER (match error rate) is the proportion of I/O word matches which are errors.
# - WIL (word information lost) is a simple approximation to the proportion of word information lost which overcomes the problems associated with the RIL (relative information lost)
#   measure that was proposed half a century ago.
# It computes the minimum-edit distance between the ground-truth sentence and the hypothesis sentence of a speech-to-text API.
# The minimum-edit distance is calculated using the python C module python-Levenshtein.

import argparse
import os
import jiwer
import json
import sys
import csv
import logging
from shutil import copyfile
from os.path import join, dirname
from config import Config
import nltk
from nltk.stem.porter import PorterStemmer

DEFAULT_CONFIG_INI='config.ini'
DEFAULT_LOGLEVEL='DEBUG'

class AnalysisResult:
    def __init__(self, audio_file_name, reference, hypothesis, cleaned_reference, cleaned_hypothesis, measures, differences):
        self.audio_file_name = audio_file_name
        self.measures        = measures
        self.differences     = differences

        self.data = {}
        self.data["Audio File Name"]       = audio_file_name
        self.data["Reference"]             = reference
        self.data["Transcription"]         = hypothesis
        self.data["Reference (clean)"]     = cleaned_reference
        self.data["Transcription (clean)"] = cleaned_hypothesis
        self.data["WER"]                   = measures['wer'] * 100
        self.data["MER"]                   = measures['mer'] * 100
        self.data["WIL"]                   = measures['wil'] * 100
        self.data["Hits"]                  = measures['hits']
        self.data["Substitutions"]         = measures['substitutions']
        self.data["Deletions"]             = measures['deletions']
        self.data["Insertions"]            = measures['insertions']
        self.data["Differences"]           = str(differences).replace(';', ' ') #Replace commas for naive CSV readers

class AnalysisResults:
    def __init__(self, config):
        self.results = []
        self.headers = []
        self.total_words  = 0
        self.total_word_errors = 0
        self.total_sent_errors = 0
        self.config = config
        self.word_map = {}

    def add(self, result:AnalysisResult):
        #Track `details_file` data
        self.results.append(result)
        self.headers = result.data.keys()

        #Track `summary_file` data
        word_errors = 0
        word_errors += result.data["Substitutions"]
        word_errors += result.data["Deletions"]
        word_errors += result.data["Insertions"]

        self.total_words  += len(result.data["Reference"].split(" "))
        self.total_word_errors += word_errors
        if(word_errors > 0):
            self.total_sent_errors += 1

        #Track `word_accuracy_file` data
        for word in result.data["Reference (clean)"].split(" "):
            tuple = self.get_tuple(word)
            tuple['count'] = tuple['count']+1
            tuple['error_rate'] = tuple['errors'] / tuple['count']

        for word in result.differences:
            tuple = self.get_tuple(word)
            tuple['errors']     = tuple['errors']+1
            tuple['error_rate'] = tuple['errors'] / tuple['count']

    def get_tuple(self, word):
        if word not in self.word_map:
            tuple = {'word':word, 'count':0, 'errors':0, 'error_rate':0.0}
            self.word_map[word] = tuple
        else:
            tuple = self.word_map[word]
        return tuple

    def get_summary(self):
        results = {}
        results["Number of Samples"]      = len(self.results)
        results["Total Words"]            = self.total_words
        results["Total Word Errors"]      = self.total_word_errors
        results["Word Error Rate"]        = round(self.total_word_errors / self.total_words, 4)
        results["Total Sentence Errors"]  = self.total_sent_errors
        results["Sentence Error Rate"]    = round(self.total_sent_errors / len(self.results), 4)

        #Store transcription configuration in the summary, for ease of comparing different summary files
        #Don't store/compare sensitive values
        config_keys = self.config.getKeys("SpeechToText")
        ignore_keys = ["apikey","service_url","use_bearer_token"]
        for key in config_keys:
            if key not in ignore_keys:
                results[key] = self.config.getValue("SpeechToText", key)

        return results

    def write_details(self, filename):
        csv_columns = self.headers

        with open(filename, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(csv_columns)
            for result in self.results:
                writer.writerow(result.data.values())
        
        logging.info(f"Wrote detailed results to {filename}")

    def write_summary(self, filename):

        with open(filename, 'w') as jsonfile:
            json.dump(self.get_summary(), jsonfile, indent=2)
        
        logging.info(f"Wrote summary results to {filename}")

    def write_word_accuracy(self, filename):
        csv_columns = ['word','count','errors','error_rate']

        with open(filename, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            for word in self.word_map:
                writer.writerow(self.word_map[word])

        logging.info(f"Wrote word accuracy results to {filename}")

class Analyzer:
    def __init__(self, config):
        self.config = config
        self.transformation = self.get_pipeline()

    def load_csv(self, filename:str, headers:list):
        result = {}
        # https://stackoverflow.com/questions/57152985/what-is-the-difference-between-utf-8-and-utf-8-sig
        # utf-8-sig so we can ignore the BOM (Byte Order Marker)
        with open(filename, encoding='utf-8-sig') as file:
            csvreader = csv.DictReader(file)
            for row in csvreader:
                key = row[headers[0]]
                value = row[headers[1]]
                result[key] = value
        return result

    def get_pipeline(self):
        pipeline = []
        if self.config.getBoolean("Transformations", "lower_case"):
            pipeline.append(jiwer.ToLowerCase())

        if self.config.getBoolean("Transformations", "remove_white_space"):
            pipeline.append(jiwer.RemoveWhiteSpace(replace_by_space=True))

        if self.config.getBoolean("Transformations", "remove_multiple_spaces"):
            pipeline.append(jiwer.RemoveMultipleSpaces())

        #JIWER 2.2 defines SentencesToListOfWords
        if self.config.getBoolean("Transformations", "sentences_to_words") and getattr(jiwer, "SentencesToListOfWords", None) is not None:
            pipeline.append(jiwer.SentencesToListOfWords(word_delimiter=" "))

        word_list = self.config.getValue("Transformations", "remove_word_list")
        if word_list is not None and len(word_list) > 0:
            pipeline.append(jiwer.RemoveSpecificWords(word_list.split(",")))

        if self.config.getBoolean("Transformations", "remove_punctuation"):
            pipeline.append(jiwer.RemovePunctuation())

        if self.config.getBoolean("Transformations", "strip"):
            pipeline.append(jiwer.Strip())

        if self.config.getBoolean("Transformations", "remove_empty_strings"):
            pipeline.append(jiwer.RemoveEmptyStrings())

        #JIWER 2.3+ defines ReduceToListOfListOfWords, breaking API change from SentencesToListOfWords
        if self.config.getBoolean("Transformations", "sentences_to_words") and getattr(jiwer, "ReduceToListOfListOfWords", None) is not None:
            pipeline.append(jiwer.ReduceToSingleSentence())
            pipeline.append(jiwer.ReduceToListOfListOfWords(word_delimiter=" "))

        return jiwer.Compose(pipeline)


    def analyze(self):
        reference_file   = self.config.getValue("Transcriptions","reference_transcriptions_file")
        hypothesis_file  = self.config.getValue("Transcriptions","stt_transcriptions_file")
        reference_dict   = self.load_csv(reference_file, ["Audio File Name", "Reference"])
        hypothesis_dict  = self.load_csv(hypothesis_file,["Audio File Name", "Transcription"])

        results = AnalysisResults(self.config)
        p_stemmer = PorterStemmer()

        for audio_file_name in reference_dict.keys():
            reference = reference_dict.get(audio_file_name)
            hypothesis   = hypothesis_dict.get(audio_file_name, None)

            if hypothesis is None:
                logging.warn(f"{audio_file_name} - No hypothesis transcription found", sys.stderr)
                continue

            # Common pre-processing on ground truth and hypothesis
            cleaned_ref = self.transformation(reference)
            cleaned_hyp = self.transformation(hypothesis)

            if self.config.getBoolean("Transformations", "stemming"):
                cleaned_ref = [p_stemmer.stem(word) for word in cleaned_ref]
                cleaned_hyp = [p_stemmer.stem(word) for word in cleaned_hyp]

            # gather all metrics at once with `compute_measures`
            measures = jiwer.compute_measures(cleaned_ref, cleaned_hyp)
            differences = self.compute_differences(cleaned_ref, cleaned_hyp)

            result = AnalysisResult(audio_file_name, reference, hypothesis, " ".join(cleaned_ref), " ".join(cleaned_hyp), measures, differences)
            results.add(result)

        return results

    def compute_differences(self, ref_list, hyp_list):
        #Simple set arithmetic does not work if the same word appears multiple times in the reference transcription
        #differences = list(set(cleaned_ref) - set(cleaned_hyp))

        differences = list()
        for word in set(ref_list):
            ref_count = ref_list.count(word)
            hyp_count = hyp_list.count(word)
            diff = ref_count - hyp_count
            if diff > 0:
                for _ in range(diff):
                    differences.append(word)
        return differences

def run(config_file:str, logging_level:str=DEFAULT_LOGLEVEL):
    config      = Config(config_file)
    analyzer    = Analyzer(config)

    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.debug(f"Using config file:{config_file}")

    output_dir = os.path.dirname(config.getValue("ErrorRateOutput", "summary_file"))
    if output_dir is not None and len(output_dir) > 0:
        os.makedirs(output_dir, exist_ok=True)

    results = analyzer.analyze()
    results.write_details(config.getValue("ErrorRateOutput","details_file"))
    results.write_summary(config.getValue("ErrorRateOutput","summary_file"))
    results.write_word_accuracy(config.getValue("ErrorRateOutput","word_accuracy_file"))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-c', '--config_file', type=str, default=DEFAULT_CONFIG_INI, help='the config file to use')
    parser.add_argument(
        '-ll', '--log_level', type=str, default=DEFAULT_LOGLEVEL, help='the log level to use')

    args = parser.parse_args()

    run(args.config_file, args.log_level)
