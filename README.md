# STT-WER-Python
Utilities for
* [Transcribing](#transcription) a set of audio files with Speech to Text (STT)
* [Analyzing](#analysis) the error rate of the STT transcription against a known-good transcription

## More documentation
This readme describes the tools in depth.  For more information on use cases and methodology, please see the following articles:
* [New Python Scripts to Measure Word Error Rate on Watson Speech to Text](https://medium.com/@marconoel/new-python-scripts-to-measure-word-error-rate-on-watson-speech-to-text-77ecaa513f60): How to use these tools, including a YouTube video demonstration
* [New Speech Testing Utilities for Conversational AI Projects](https://medium.com/ibm-watson-speech-services/new-speech-testing-utilities-for-conversational-ai-projects-bf73debe19be): Describes recipe for using Text to Speech to "bootstrap" testing data
* [Data Collection and Training for Speech Projects](https://medium.com/ibm-data-ai/data-collection-and-training-for-speech-projects-22004c3e84fb): How to collect test data from human voices.
* [How to Train your Speech to Text Dragon](https://medium.com/ibm-watson/watson-speech-to-text-how-to-train-your-own-speech-dragon-part-1-data-collection-and-fdd8cea4f4b8)

You may also find useful:
* [TTS-Python](https://github.com/IBM/watson-tts-python) - companion tooling for IBM Text to Speech

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
* max_threads - Maximum number of threads to use with `transcribe.py` to improve performance.
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
python models.py -o create -t custom_model -n "model1" -d "my first model"
```

Add a corpus file for a custom model (the custom model's customization_id is stored in `config.ini.model1`)(`corpus1.txt` contains the corpus contents):
```
python models.py -c config.ini.model1 -o create -n "corpus1" -f "corpus1.txt" -t corpus
```

Create corpora for all corpus files in a directory (the filename will be used for the corpora name)
```
python models.py -c config.ini.model1 -o create -t corpus -dir corpus-dir
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

# Sample setup for organizing multiple experiments
Instructions for creating a directory structure for organizing input and output files for experiments for multiple models. Creating a new directory structure is recommend for each new model being experimented/tested. A sample `MemberID` model is shown.
1. Start from root of WER tool directory, `cd WATSON-STT-WER-PYTHON`
1. Create project directory, `mkdir -p <project name>`
    1. e.g. `mkdir -p ClientName-data`
1. Create audio directory, `mkdir -p <project name>/audios/<audio type>`
    1. e.g. `mkdir -p ClientName-data/audios/audio.memberID`
    1. copy/upload audio files to directory
        1. e.g. `cp /temp/audio/*.wav ClientName-data/audios/audio.memberID`
1. Create referemce transcriptions directory, `mkdir -p <project name>/reference_transcriptions`
    1. e.g. `mkdir -p ClientName-data/reference_transcriptions`
    1. copy/upload transcription file to directory
        1. e.g. `cp/temp/transcriptions/reference_transcription_memberID.csv ClientName-data/reference_transcriptions`
1. Create experiments directory, `mkdir -p <project name>/experiments/<model description base>/<model detail>`
    1. e.g. `mkdir -p ClientName-data/experiments/telephony_base/MemberID/`
1. Copy sample config file over to directory
    1. e.g. `cp config.ini.sample ClientName-data/experiments/telephony_base/MemberID/config.ini`
    1. Edit the config file to match your new directory structure
        ```
        base_model_name=en-US_Telephony
        .
        .
        .
        [Transcriptions]
        reference_transcriptions_file=./ClientName-data/reference_transcriptions/reference_transcription_memberID.csv
        stt_transcriptions_file=./ClientName-data/experiments/telephony_base/MemberID/stt_transcription.csv
        audio_file_folder=./ClientName-data/audios/audio.memberID

        [ErrorRateOutput]
        details_file=./ClientName-data/experiments/telephony_base/MemberID/wer_detailsMemberID.csv
        summary_file=./ClientName-data/experiments/telephony_base/MemberID/wer_summaryMemberID.json
        word_accuracy_file=./ClientName-data/experiments/telephony_base/MemberID/wer_word_accuracyMemberID.csv
        stt_transcriptions_file=./ClientName-data/experiments/telephony_base/MemberID/stt_transcription.csv
        ```
1. transcribe using the new config file, `python transcribe.py ClientName-data/experiments/telephony_base/MemberID/config.ini`
1. analyze using the new config file, `python analyze.py ClientName-data/experiments/telephony_base/MemberID/config.ini`
1. repeat previous steps for each new experiment

# (Optional): Using the `Whisper` model to create a reference file
Whisper is a general-purpose speech recognition model. It is trained on a large dataset of 680,000 hours containing diverse audio and is also a multi-task model that can perform multilingual speech recognition as well as speech translation and language identification. - see here for more information https://openai.com/blog/whisper/

Some customers may have a lot of audio files to build their training and test sets, but they do not have time to transcribe them to have a reference. You can always bootstrap your human transcription by using Watson STT but there is always a risk of introducing bias from it. This new Python module will allow users to build a pretty accurate reference using the "whisper" model.

NOTE: These "whisper" models are significantly larger than the Watson STT and much slower to process audio files, depending on the model size you select - Be patient.

## Install Whisper models
- Pull the repository locally: https://github.com/openai/whisper
- Follow the steps to complete the installation: https://github.com/openai/whisper#setup
- Note the name of your "whisper" root folder

## Setup
- Copy the audio files you wish to get transcribed into the "whisper" root folder
- From the sub-folder `whisper-script`, copy the new python script `reference-transcripts.py` into the "whisper" root folder above

## Setup the whisper model language for the audio files
There are 2 ways to select the whisper model language to be used to transcribe your audio files.
- language detection
- default language

You need to update the python script `reference-transcripts.py`, and update the "auto_detect" variable

- auto_detect = True # Set to True if you do not know the language of the audio
- default_lang = 'en' # If auto_detect is False, this value will be used for all audio files

TIP: You can use the same first 2 letters of the Watson STT model you wish to evaluate (eg. en-GB_Telephony ==> "en" / pt-BR_Telephony ==> "pt")

NOTE: The "whisper" language detection may not be accurate. In the CSV file, a column called "Language - CAN BE DELETED" is created as an informational indicator of the "whisper" language used (detected or by default).

## Run the python script `reference-transcripts.py`
- Go to the "whisper" folder
- Simply run `python reference-transcripts.py`

When completed, you should be getting a CSV file named `reference_transcriptions_whisper.csv`.

NOTE: Please review and adjust transcription where applicable as this is still speech recognition and may not be accurate. Don't forget to delete the column "Language - CAN BE DELETED" before saving.

You are now ready to use this CSV file as your reference file when evaluating Watson STT.
