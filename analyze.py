# Repo: https://pypi.org/project/jiwer/
# Simple python package to approximate the Word Error Rate (WER), Match Error Rate (MER), Word Information Lost (WIL) and Word Information Preserved (WIP) of a transcript.
# - WER (word error rate), commonly used in ASR assessment, measures the cost of restoring the output word sequence to the original input sequence.
# - MER (match error rate) is the proportion of I/O word matches which are errors.
# - WIL (word information lost) is a simple approximation to the proportion of word information lost which overcomes the problems associated with the RIL (relative information lost)
#   measure that was proposed half a century ago.
# It computes the minimum-edit distance between the ground-truth sentence and the hypothesis sentence of a speech-to-text API.
# The minimum-edit distance is calculated using the python C module python-Levenshtein.

import jiwer
import json
import sys
import csv
from os.path import join, dirname
from config import Config


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
    def __init__(self):
        self.results = []
        self.headers = []
        self.total_words  = 0
        self.total_word_errors = 0
        self.total_sent_errors = 0

    def add(self, result:AnalysisResult):
        #print("Add",result.data)
        self.results.append(result)
        self.headers = result.data.keys()

        word_errors = 0
        word_errors += result.data["Substitutions"]
        word_errors += result.data["Deletions"]
        word_errors += result.data["Insertions"]

        self.total_words  += len(result.data["Reference"].split(" "))
        self.total_word_errors += word_errors
        if(word_errors > 0):
            self.total_sent_errors += 1

    def get_summary(self):
        results = {}
        results["Number of Samples"]      = len(self.results)
        results["Total Words"]            = self.total_words
        results["Total Word Errors"]      = self.total_word_errors
        results["Word Error Rate"]        = round(self.total_word_errors / self.total_words, 4)
        results["Total Sentence Errors"]  = self.total_sent_errors
        results["Sentence Error Rate"]    = round(self.total_sent_errors / len(self.results), 4)

        return results

    def write_details(self, filename):
        print(f"Writing detailed results to {filename}")
        csv_columns = self.headers

        with open(filename, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(csv_columns)
            for result in self.results:
                writer.writerow(result.data.values())

    def write_summary(self, filename):
        print(f"Writing summary results to {filename}")

        with open(filename, 'w') as jsonfile:
            json.dump(self.get_summary(), jsonfile)

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

        if self.config.getBoolean("Transformations", "remove_multiple_spaces"):
            pipeline.append(jiwer.RemoveMultipleSpaces())

        if self.config.getBoolean("Transformations", "remove_white_space"):
            pipeline.append(jiwer.RemoveWhiteSpace(replace_by_space=True))

        if self.config.getBoolean("Transformations", "sentences_to_words"):
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

        return jiwer.Compose(pipeline)


    def analyze(self):
        reference_file   = self.config.getValue("Transcriptions","reference_transcriptions_file")
        hypothesis_file  = self.config.getValue("Transcriptions","stt_transcriptions_file")
        reference_dict   = self.load_csv(reference_file, ["Audio File Name", "Reference"])
        hypothesis_dict  = self.load_csv(hypothesis_file,["Audio File Name", "Transcription"])

        results = AnalysisResults()

        for audio_file_name in reference_dict.keys():
            reference = reference_dict.get(audio_file_name)
            hypothesis   = hypothesis_dict.get(audio_file_name, None)

            if hypothesis is None:
                print(f"{audio_file_name} - No hypothesis transcription found", sys.stderr)
                continue

            # Common pre-processing on ground truth and hypothesis
            cleaned_ref = self.transformation(reference)
            cleaned_hyp = self.transformation(hypothesis)

            # gather all metrics at once with `compute_measures`
            measures = jiwer.compute_measures(cleaned_ref, cleaned_hyp)
            differences = list(set(cleaned_ref) - set(cleaned_hyp))

            result = AnalysisResult(audio_file_name, reference, hypothesis, " ".join(cleaned_ref), " ".join(cleaned_hyp), measures, differences)
            results.add(result)

        return results

def main():
    config_file = "config.ini"
    if len(sys.argv) > 1:
       config_file = sys.argv[1]
    else:
       print("Using default config filename: config.ini.")

    config      = Config(config_file)
    analyzer    = Analyzer(config)

    results = analyzer.analyze()
    results.write_details(config.getValue("ErrorRateOutput","details_file"))
    results.write_summary(config.getValue("ErrorRateOutput","summary_file"))

if __name__ == '__main__':
    main()
