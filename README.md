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

**Note:**  If receiving an SSL Certificate error (CERTIFICATE_VERIFY_FAILED) when running the python scripts, try the following commands to tell python to use the system certificate store.

**_Windows_**
```
pip install --trusted-host pypi.org --trustedhost files.python.org python-certifi-win32
```

**_MacOS_**

Open a terminal and change to the location of your python installation to execute `Install Certificates.command`, for example:
```
cd /Applications/Python 3.6
./Install Certificates.command
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
* stemming - If True, pre-processing stems words with Porter stemmer. Stemming will treat singular/plural of a word as equivalent, rather than a word error.



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

# Experiment
Use the experiment.py script to execute a series of Transcription/Analyze experiments where configuration settings may change for each experiment.  This option will require customization to set up for the specific configuration to be tested.  Changes should be made in the run_all_experiments function.

```
python experiment.py config.ini
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

# Model training
The `models.py` script has wrappers for many model-related tasks including creating models, updating training contents, getting model details, and training models.

## Setup
Update the parameters in your `config.ini` file.

Required configuration parameters:
* apikey - API key for your Speech to Text instance
* service_url - Reference URL for your Speech to Text instance
* base_model_name - Base model for Speech to Text transcription

## Execution
For general help, execute:
```
python models.py
```

The script requires a type (one of base_model,custom_model,corpus,word,grammar) and an operation (one of list,get,create,update,delete)
The script optionally takes a config file as an argument with `-c config_file_name_goes_here`, otherwise using a default file of `config.ini` which contains the connection details for your speech to text instance.
Depending on the specified operation, the script also accepts a name, description, and file for an associated resource.  For instance, new custom models should have a name and description, and a corpus should have a name and associated file.

## Examples

List all base models:
```
python models.py -o list -t base_model
```

List all custom models:
```
python models.py -o list -t custom_model
```

Create a custom model:
```
python models.py -o add -t custom_model -n "model1" -d "my first model"
```

Add a corpus file for a custom model (the custom model's customization_id is stored in `config.ini.model1`)(`corpus1.txt` contains the corpus contents):
```
python models.py -c config.ini.model1 -o add -n "corpus1" -f "corpus1.txt"
```

List all corpora for a custom model (the custom model's customization_id is stored in `config.ini.model1`):
```
python models.py -c config.ini.model1 -o list -t corpus
```

Train a custom model (the custom model's customization_id is stored in `config.ini.model1`):
```
python models.py -c config.ini.model1 -o update -t custom_model
```

Note some parameter combinations are not possible.  The operations supported all wrap the SDK methods documented at https://cloud.ibm.com/apidocs/speech-to-text.