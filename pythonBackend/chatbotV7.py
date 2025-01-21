import os
import re
from urllib.request import urlretrieve
import numpy as np
import transformers
import torch
from langchain_community import document_loaders
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from transformers import GPT2TokenizerFast
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.embeddings import HuggingFaceBgeEmbeddings

modelName = "HuggingFaceTB/SmolLM-1.7B"

tokenizer = AutoTokenizer.from_pretrained(modelName)
model = AutoModelForCausalLM.from_pretrained(modelName)

with open("pdf_raw_text.txt", encoding="utf-8") as f:
    paper_text = f.read()

paper_text = paper_text.replace("\n", " ").strip()
paper_text = re.sub(r'[^\w\s.,]', '', paper_text)

tokenizedText = tokenizer.tokenize(paper_text)

len(tokenizedText)

tokenizedText[801]

#retriever = SentenceTransformer('paraphrase-MiniLM-L6-v2')

#document_embeddings = retriever.encode(chunks, convert_to_tensor=True)

document_embedder = HuggingFaceBgeEmbeddings(
    model_name="BAAI/bge-small-en",  # alternativen bedenken für schnellere ausführung
    model_kwargs={'device':'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300)

texts = text_splitter.create_documents([paper_text])

#texts[0]

db = FAISS.from_documents(texts, document_embedder)

retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 3})

str(retriever.invoke("What is this paper about?")[0])

def generate_response(retrieved_info, query):
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token  

    input_text = f"Context: {retrieved_info} your job is to answer questions about the scientific paper \"Learning to Play the Chess Variant Crazyhouse Above World Champion Level With Deep Neural Networks and Human Data\". Provide a concise answer with no more than 130 words. If you don't know something don't make it up and just say you dont know it.\n\nQuestion: {query}\nAnswer: "

    inputs = tokenizer(
        input_text,
        return_tensors="pt",
        padding=True,
        truncation=True,
    )

    response = model.generate(
        inputs["input_ids"],
        attention_mask=inputs["attention_mask"],
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
        max_new_tokens=160,
        pad_token_id=tokenizer.pad_token_id  
    )

    return tokenizer.decode(response[0], skip_special_tokens=True)

while True:
    user_query = input("\nYou: ")
    if user_query.lower() in ["exit", "quit"]:
        print("Goodbye!")
        break
    retrieved_info = retriever.invoke(user_query)

    retrieved_info_concat = str(retrieved_info[0]) + str(retrieved_info[1]) + str(retrieved_info[2])
    response = generate_response(retrieved_info_concat, user_query)

    print("Query:", user_query, '<- our prompt')
    print("Retrieved Information:", retrieved_info[0], '<- retrieved response')
    print("Response:", response, '<- smollms response')