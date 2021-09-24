# STT-WER-Python
Utilities for
* [Transcribing](#transcription) a set of audio files with Speech to Text (STT)
* [Analyzing](#analysis) the error rate of the STT transcription against a known-good transcription

## Medium article
Check out this Medium article to learn more how to use it, including a YouTube video demonstration https://medium.com/@marconoel/new-python-scripts-to-measure-word-error-rate-on-watson-speech-to-text-77ecaa513f60

## Installation
Requires Python 3.x installation.

All of the watson-stt-wer-python dependencies are installed at once with `pip`:

```
pip install -r requirements.txt
```

## Setup
Create a copy of `config.ini.sample`. You'll modify this file in subsequent steps.
```
cp config.ini.sample config.ini
```

Each sub-sections will describe what configuration parameters are needed.

# Transcription
Uses IBM Watson Speech to Text service to transcribe a folder full of audio files.  Creates a CSV with transcriptions.



## Setup
Update the parameters in your `config.ini` file.

Required configuration parameters:
* apikey - API key for your Speech to Text instance
* service_url - Reference URL for your Speech to Text instance
* base_model_name - Base model for Speech to Text transcription

Optional configuration parameters:
* language_model_id - Language model customization ID (comment out to use base model)
* acoustic_model_id - Acoustic model customization ID (comment out to use base model)
* grammar_name - Grammar name (comment out to use base model)
* stt_transcriptions_file - Output file for Speech to Text transcriptions
* audio_file_folder - Input directory containing your audio files
* reference_transcriptions_file - Reference file for manually transcribed audio files ("labeled data" or "ground truth").  If present, will be merged into `stt_transcriptions_file` as "Reference" column

## Execution
Assuming your configuration is in `config.ini`, transcribe all the audio files in `audio_file_folder` parameter via the following command:

```
python transcribe.py config.ini
```

## Output
Transcription will be stored in a CSV file based on `stt_transcriptions_file` parameter with a format like below:

Audio File|Transcription
-----|-----
file1.wav|The quick brown fox
file2.wav|jumped over the lazy dog

A third column, "Reference", will be included with the reference transcription, if a `reference_transcriptions_file` is found as source.

# Analysis
Simple python package to approximate the Word Error Rate (WER), Match Error Rate (MER), Word Information Lost (WIL) and Word Information Preserved (WIP) of one or more transcripts.

## Setup
Your config file must have references for the `reference_transcriptions_file` and `stt_transcriptions_file` properties.

* **Reference file** (`reference_transcriptions_file`) is a CSV file with at least columns called `Audio File Name` and `Reference`.  The `Reference` is the actual transcription of the audio file (also known as the "ground truth" or "labeled data"). NOTE: In your audio file name, make sure you put the full path (eg. ./audio1.wav)
* **Hypothesis file** (`stt_transcriptions_file`) is a CSV file with at least columns called `Audio File Name` and `Hypothesis`.  The `Hypothesis` is the transcription of the audio file by the Speech to Text engine.  The `transcribe.py` script can create this file.

## Execution

```
python analyze.py config.ini
```

## Results
The script creates two output files, in the file names specified by the `details_file` and `summary_file` properties.
* **Details** (`details_file`) is a CSV file with rows for each audio sample, including reference and hypothesis transcription and specific transcription errors
* **Summary** (`summary_file`) is a JSON file with metrics for total transcriptions and overall word and sentence error rates.

## Metrics (Definitions)
- WER (word error rate), commonly used in ASR assessment, measures the cost of restoring the output word sequence to the original input sequence.
- MER (match error rate) is the proportion of I/O word matches which are errors.
- WIL (word information lost) is a simple approximation to the proportion of word information lost which overcomes the problems associated with the RIL (relative information lost) measure that was proposed half a century ago.

## Background on supporting library
Repo of the Python module JIWER: https://pypi.org/project/jiwer/

It computes the minimum-edit distance between the ground-truth sentence and the hypothesis sentence of a speech-to-text API.
The minimum-edit distance is calculated using the python C module python-Levenshtein.
