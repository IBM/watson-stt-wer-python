import whisper
import os

model = whisper.load_model("medium")

#list audio files in current folder

files=os.listdir('.')

#Process each audio files in whisper, wirting in reference_transcriptions_whisper.csv
with open('./reference_transcriptions_whisper.csv','w', encoding='utf-8') as csvfile:
    #Writing CSV column headers
    csvfile.write('Language - CAN BE DELETED,Audio File Name,Reference')
    csvfile.write('\n')

    for f in files:
        if f.endswith(".wav"): #Transcribing WAV files only
            # load audio and pad/trim it to fit 30 seconds
            audio = whisper.load_audio(f)
            audio = whisper.pad_or_trim(audio)

            # make log-Mel spectrogram and move to the same device as the model
            mel = whisper.log_mel_spectrogram(audio).to(model.device)

            # detect the spoken language
            _, probs = model.detect_language(mel)
            audio_lang = max(probs, key=probs.get)

            #transcribing audio with whisper model
            print(f"Processing audio file {f} using language {audio_lang}")
            result = model.transcribe(f,fp16=False, language=audio_lang)

            #writing into CSV file
            csvfile.write(str(audio_lang)+','+'./'+str(f)+','+result["text"])
            csvfile.write('\n')
