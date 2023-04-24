# Fine Tuning Your Configuration

In its default state, Watson STT provides very accurate transcriptions across a wide range of words, accents, and audio interferances. However, should you want to get under the hood and fine tune things, Watson STT has you covered. With settings for speech sensitivity, background audio suppression, and customization model bias, to name a few, Watson STT gives you the ability to optimize your solution to fit your business and customer needs.

## Sounds great, how do I optimize the fine tuning, though?
Getting that perfect balance can be tricky. Manually cycling through parameter values, or taking guesses at optimal settings, takes time and will often not produce the best results for your solution. To know for sure which settings provide the best transcriptions, you'll want to perform a grid search on the settings you care about. When complete, you'll be able to make a confident decision on what to set each parameter, knowing that those decisions will verifiably lead to better transcriptions within your usecase. 

## What is grid search?
Grid search is a fancy term for cycling through all combinations of various parameter values to find the most optimal ones. In the case of a STT grid search, the optimal values are the ones that produce the most accurate transcriptions for a given test set. During grid search, a given iteration will set the parameters to specific values, run a test set of audio files through STT, and analyze the results for accuracy. It then increments one of the parameters and starts a new iteration. After all possible combinations of values have been attempted and analyzed, results are provided showing the accuracy of each iteration and the values used during that iteration.

## This can be automated, right?
Of course! In fact it already has! Within the https://github.com/IBM/watson-stt-wer-python repo there is a script called `experiment.py` to facilitate grid search against Watson STT. Here's how it works:

Clone down the repo to your local machine

```git clone git@github.com:IBM/watson-stt-wer-python.git```

Follow the installation instructions in the repository's README - https://github.com/IBM/watson-stt-wer-python#installation

Create a reference file containing audio filenames and their associated, correct, transcritption. There is a sample reference file in the repo to model your's after.

Select audio files to use as a test set. Note that the more files you include both the more representative the results will be, and the longer grid search will take. Store this test set into a unique directory.

Update the `config.ini` file with:
1. The `apikey`, `service_url`, and `base_model_name` of the service to optimize. 
1. If using a custom model, include the `language_model_id` and/or `acoustic_model_id`. 
1. The `reference_transcriptions_file` you created 
1. The `audio_file_folder` containing your test set of audio files. 
1. The `stt_transcriptions_file` you wish to have transcripts stored into as a filename.
1. The parameters you wish to optimize. If you would like to omit parameters from the grid search, set their `_min` and `_max` values to the same value, which will be used in each iteration. 
    1. `sds_*` controls the `speech_detector_sensitivity` parameter
    1. `bias_*` controls the `character_insertion_bias` parameter
    1. `cust_weight_*` controls the `customization_weight` parameter
    1. `bas_*` controls the `background_audio_suppression` parameter

Run the grid search
```python experiment.py --config_file config.ini --log_level INFO```

View the results in the file `all_summaries.csv` to see a concise view of all iterations, or, view the details of each iteration by looking at the set of directories created in the format `bias_<bias-value>_weight_<customization-weight-value>_sds_<sds-value>_bas_<bas-value>`

