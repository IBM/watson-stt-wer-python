import json
import os
from pickle import TRUE
import sys
import re
import csv
import time
from config import Config

from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import IAMTokenManager
from ibm_cloud_sdk_core.authenticators import BearerTokenAuthenticator
from ibm_watson.speech_to_text_v1 import CustomWord

from argparse import ArgumentParser

import os.path
from os import path

#For information to user.  stdout is preserved for command status (could be redirected to file and parsed), stderr tracks ongoing progress
def eprint(msg:str):
    print(msg, file=sys.stderr)

class ModelTool:

    def __init__(self, config, ARGS):
        self.config = config
        self.STT = self.createSTT()
        self.ARGS = ARGS

    def createSTT(self):
        apikey            = self.config.getValue("SpeechToText", "apikey")
        url               = self.config.getValue("SpeechToText", "service_url")
        use_bearer_token  = self.config.getBoolean("SpeechToText", "use_bearer_token")

        if use_bearer_token != True:
            authenticator = IAMAuthenticator(apikey)
        else:
            iam_token_manager = IAMTokenManager(apikey=apikey)
            bearerToken       = iam_token_manager.get_token()
            authenticator     = BearerTokenAuthenticator(bearerToken)

        speech_to_text = SpeechToTextV1(authenticator=authenticator)

        speech_to_text.set_service_url(url)
        speech_to_text.set_default_headers({'x-watson-learning-opt-out': "true"})
        return speech_to_text

    def execute(self):
        # eprint(f"operation: {self.ARGS.operation}\n"
        #       +f"type: {self.ARGS.type}\n"
        #       +f"name: {self.ARGS.name}\n"
        #       +f"description: {self.ARGS.description}\n"
        #       +f"file: {self.ARGS.file}\n"
        # )

        # Registration of all the methods we support.
        # First key is type, second key is type
        # By genericizing the invocation, we can use common response handling below.
        type_handlers = {}
        type_handlers['base_model'  ] = self.get_type_base_model_handlers
        type_handlers['custom_model'] = self.get_type_custom_model_handlers
        type_handlers['corpus'      ] = self.get_type_corpus_handlers
        type_handlers['word'        ] = self.get_type_word_handlers
        type_handlers['grammar'     ] = self.get_type_grammar_handlers

        if self.ARGS.type in type_handlers:
            type_handler = type_handlers[self.ARGS.type]()
            if self.ARGS.operation in type_handler:
                eprint(f"Executing operation: {self.ARGS.operation} on type: {self.ARGS.type}")
                response = type_handler[self.ARGS.operation]()
                if response is not None:
                    #Could do global handling of HTTP status code, etc
                    #eprint(response.get_status_code())
                    print(json.dumps(response.get_result(), indent=2))
                else:
                    eprint(f"Error executing operation: {self.ARGS.operation} on type: {self.ARGS.type}")    
            else:
                eprint(f"Unsupported operation: {self.ARGS.operation} on type: {self.ARGS.type}")
        else:
            eprint(f"Unsupported type: {self.ARGS.type}")

    # Most methods rely on the customization ID, we can abstract the config file from those methods
    def get_customization_id(self):
        return self.config.getValue("SpeechToText", "language_model_id")

    def wait_until(self, status):
        """Wait until the model is in the given state, such as 'ready' or 'available'
        (it might still need to finalize an operation such adding a corpus file or training)
        """
        while True:
            resp = self.STT.get_language_model(self.get_customization_id())
            # respjson = json.dumps(resp)
            print("resp result status: ", resp.result['status'])
            if resp.status_code != 200:
                return False            
            if resp.result['status'] == status:
                break
            elif resp.result['status'] == 'failed':
                break
            else:
                print("model in '" + resp.result['status'] + "' status, waiting until '" + status + "'...")
                time.sleep(5.0)

    '''
    Base model functions
    '''
    def get_type_base_model_handlers(self):
        handlers = {}
        handlers['list'] = self.STT.list_models
        handlers['get']  = self.get_base_model

        return handlers
    
    def get_base_model(self):
        name = self.config.getValue("SpeechToText", "base_model_name")
        if ARGS.name is not None:
            name = ARGS.name

        return self.STT.get_model(name)

    '''
    Custom model functions
    '''

    def get_type_custom_model_handlers(self):
        handlers = {}
        handlers['list'  ] = self.STT.list_language_models
        handlers['create'] = self.create_custom_model
        handlers['get'   ] = self.get_custom_model
        handlers['delete'] = self.delete_custom_model
        # Update intentionally mapped to STT 'train' to reduce operation count.  
        # Thus the SDK's 'add' is our 'create' and SDK's 'train' is our update.  This matches my mental model of speech customization.
        handlers['update'] = self.train_custom_model

        return handlers

    def get_custom_model(self):
        return self.STT.get_language_model(self.get_customization_id())

    def create_custom_model(self):
        base_model_name = self.config.getValue("SpeechToText", "base_model_name")
        model_name = self.ARGS.name
        if self.ARGS.name is None:
            eprint("ERROR: Must pass a 'name' for the model")
            return None

        #Parameter 'dialect' is not included in this tool
        response = self.STT.create_language_model(model_name, base_model_name, description=self.ARGS.description)

        if response is not None and 'customization_id' in response.get_result():
            #Fetch new customization id, to store it back into a new config file
            customization_id = response.get_result()['customization_id']
            self.config.setValue("SpeechToText", "language_model_id", customization_id)
            
            #Sanitization could be improved a bit more, see https://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename
            sanitized_model_name = re.sub('[ /.]','_', model_name)
            new_config_file_name = f"config.ini.{sanitized_model_name}"
            eprint(f"Writing new configuration to {new_config_file_name} which contains customization id {customization_id}")
            self.config.writeFile(new_config_file_name)

        return response

    def delete_custom_model(self):
        return self.STT.delete_language_model(self.get_customization_id())

    def train_custom_model(self):
        return self.STT.train_language_model(self.get_customization_id())

    def reset_custom_model(self):
        return self.STT.reset_language_model(self.get_customization_id())

    def upgrade_custom_model(self):
        return self.STT.upgrade_language_model(self.get_customization_id())

    '''
    Corpus functions
    '''

    def get_type_corpus_handlers(self):
        handlers = {}
        handlers['list'  ] = self.list_corpora
        handlers['get'   ] = self.get_corpus
        handlers['create'] = self.add_corpus
        handlers['update'] = self.update_corpus
        handlers['delete'] = self.delete_corpus

        return handlers

    def list_corpora(self):
        return self.STT.list_corpora(self.get_customization_id())

    def add_corpus(self):
        return self.do_write_corpus(update=False)

    def update_corpus(self):
        return self.do_write_corpus(update=True)

    def do_write_corpus(self, update:bool):
        if self.ARGS.file is None and self.ARGS.directory is None:
            eprint("ERROR: Must pass a 'file' or 'directory' for the corpus")
            return None

        if self.ARGS.directory is not None:
            dir = os.path.dirname(os.path.join(self.ARGS.directory, ''))
            for file in os.listdir(dir):
                filename = os.path.basename(file).split('.')[0]
                with open(os.path.join(dir, file), 'rb') as corpus_contents:
                    resp = self.STT.add_corpus(self.get_customization_id(), filename, corpus_contents, allow_overwrite="true")
                    self.wait_until('ready')
                    print("Corpora ", filename, " created")
            return resp
        if self.ARGS.file is not None:
            name = self.ARGS.name
            if self.ARGS.name is None:
                name = os.path.basename(self.ARGS.file)
                eprint(f"WARNING: A corpus 'name' is required. Using default name '{name}'")

            with open(self.ARGS.file, 'rb') as corpus_contents:
                return self.STT.add_corpus(self.get_customization_id(), name, corpus_contents, allow_overwrite="true")

    def get_corpus(self):
        if self.ARGS.name is None:
            eprint(f"ERROR: A corpus 'name' is required.")
            return None

        return self.STT.get_corpus(self.get_customization_id(), self.ARGS.name)

    def delete_corpus(self):
        if self.ARGS.name is None:
            eprint(f"ERROR: A corpus 'name' is required.")
            return None

        return self.STT.delete_corpus(self.get_customization_id(), self.ARGS.name)

    '''
    Custom word functions
    '''

    def get_type_word_handlers(self):
        handlers = {}
        handlers['list'  ] = self.list_words
        handlers['get'   ] = self.get_word
        handlers['create'] = self.add_words
        handlers['update'] = self.add_words
        handlers['delete'] = self.delete_word

        return handlers
    
    def list_words(self):
        return self.STT.list_words(self.get_customization_id())

    def get_word(self):
        if self.ARGS.name is None:
            eprint(f"ERROR: A word 'name' is required.")
            return None

        return self.STT.get_word(self.get_customization_id(), self.ARGS.name)

    def add_words(self):
        if self.ARGS.file is None:
            eprint(f"ERROR: A word 'file' is required.\nThe file format is documented in https://cloud.ibm.com/docs/speech-to-text?topic=speech-to-text-languageCreate#addWords")
            return None

        with open(self.ARGS.file, 'rb') as word_contents_str:
            #SDK does not allow a file stream, you need to create CustomWord objects instead
            words_json = json.load(word_contents_str)
            words = []
            for word_json in words_json['words']:
                words.append(CustomWord(word        = word_json.get('word'),
                                        sounds_like = word_json.get('sounds_like'),
                                        display_as  = word_json.get('display_as')
                                        ))
            resp = self.STT.add_words(self.get_customization_id(), words)
            self.wait_until('ready')
            return resp

    def delete_word(self):
        if self.ARGS.name is None:
            eprint(f"ERROR: A word 'name' is required.")
            return None

        return self.STT.delete_word(self.get_customization_id(), self.ARGS.name)

    '''
    Grammar functions
    '''

    def get_type_grammar_handlers(self):
        handlers = {}
        handlers['list'  ] = self.list_grammars
        handlers['get'   ] = self.get_grammar
        handlers['create'] = self.add_grammar
        handlers['update'] = self.update_grammar
        handlers['delete'] = self.delete_grammar

        return handlers

    def list_grammars(self):
        return self.STT.list_grammars(self.get_customization_id())

    def add_grammar(self):
        return self.do_write_grammar(update=False)

    def update_grammar(self):
        return self.do_write_grammar(update=True)

    def do_write_grammar(self, update:bool):
        if self.ARGS.file is None:
            eprint("ERROR: Must pass a 'file' for the grammar")
            return None

        name = self.ARGS.name
        if self.ARGS.name is None:
            name = os.path.basename(self.ARGS.file)
            eprint(f"WARNING: A grammar 'name' is required. Using default name '{name}'")

        if self.ARGS.file.endswith('.abnf'):
            content_type = "application/srgs"
        elif self.ARGS.file.endswith('.xml'):
            content_type = "application/srgs+xml"
        else:
            eprint(f"ERROR: Expected .abnf or .xml file type for grammar.")
            return None

        with open(self.ARGS.file, 'rb') as grammar_contents:
            return self.STT.add_grammar(self.get_customization_id(), name, grammar_contents, content_type=content_type, allow_overwrite=update)

    def get_grammar(self):
        if self.ARGS.name is None:
            eprint(f"ERROR: A grammar 'name' is required.")
            return None

        return self.STT.get_grammar(self.get_customization_id(), self.ARGS.name)

    def delete_grammar(self):
        if self.ARGS.name is None:
            eprint(f"ERROR: A grammar 'name' is required.")
            return None

        return self.STT.delete_grammar(self.get_customization_id(), self.ARGS.name)

def create_parser():
    parser = ArgumentParser(description='Run IBM Speech To Text model-related commands')
    parser.add_argument('-c', '--config_file', type=str, required=False, default="config.ini", help='Configuration file including connection details')
    parser.add_argument('-o', '--operation', type=str, required=True, choices=["list","get","create","update","delete"], help="operation to perform")
    parser.add_argument('-t', '--type', type=str, required=True, choices=["base_model","custom_model","corpus","word","grammar"], help="type the operation works on")
    parser.add_argument('-n', '--name', type=str, required=False, help="name the operation works on, for instance 'MyModel' or 'corpus1'.")
    parser.add_argument('-d', '--description', type=str, required=False, help="description of the object being created; used only in create")
    parser.add_argument('-f', '--file', type=str, required=False, help="path to a file supporting the operation, for instance a corpus file or grammar file")
    parser.add_argument('-dir', '--directory', type=str, required=False, help="directory containing corpus files")
    return parser

def main(ARGS):
    config     = Config(ARGS.config_file)
    model_tool = ModelTool(config, ARGS)
    
    model_tool.execute()

if __name__ == '__main__':
    ARGS = create_parser().parse_args()
    main(ARGS)