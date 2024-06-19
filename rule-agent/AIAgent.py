#
#    Copyright 2024 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.messages.ai import AIMessage
import prompts

class AIAgent:

    def __init__(self, llm):
        self.llm = llm
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=100)
        self.prompt = PromptTemplate.from_template(
            prompts.INSTRUCTIONS_WITH_CONTEXT
        )       
        self.vector_store = None
        self.retriever = None
        self.chain = None
    
    def ingestDocument(self, pdf_file_path: str):
        docs = PyPDFLoader(file_path=pdf_file_path).load()
        chunks = self.text_splitter.split_documents(docs)
        chunks = filter_complex_metadata(chunks)

        vector_store = Chroma.from_documents(documents=chunks, embedding=FastEmbedEmbeddings())
        self.retriever = vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 3,
                "score_threshold": 0.1,
            },
        )
        
        self.chain = ({"context": self.retriever, "input": RunnablePassthrough()}
                      | self.prompt
                      | self.llm
                      ##| StrOutputParser()
        )

    def processMessage(self, userInput) -> str:
        if not self.chain:
            return "Please, add a PDF document first."
        response = self.chain.invoke({'input': userInput})
        textResponse = ""    

        if (isinstance(response, AIMessage)):
            textResponse = response.content
        else:
            textResponse = response    

        translation_table = str.maketrans({'"': r'\"','\n': r' ', '\t': r' ', '\r': r' ' })
        return '{ "input": "' + userInput.translate(translation_table) + '", "output": "' + textResponse.translate(translation_table) + '"}'

    def clear(self):
        self.vector_store = None
        self.retriever = None
        self.chain = None