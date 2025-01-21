import os
from urllib.request import urlretrieve
import numpy as np
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.llms import HuggingFacePipeline
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.llms import HuggingFaceHub
from langchain_community.llms.huggingface_pipeline import HuggingFacePipeline
from huggingface_hub import login
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer

modelName = "HuggingFaceTB/SmolLM-135M-Instruct"

tokenizer = AutoTokenizer.from_pretrained(modelName)
model = AutoModelForCausalLM.from_pretrained(modelName)


with open("pdf_raw_text.txt", encoding="utf-8") as f:
    paper_text = f.read()

paper_text = paper_text.replace("\n", " ").strip()
print(len(paper_text))

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 1200,
    chunk_overlap  = 50,
)
docs_after_split = text_splitter.split_text(paper_text)

print(len(docs_after_split))

print(len(docs_after_split)*len(docs_after_split[0]))

huggingface_embeddings = HuggingFaceBgeEmbeddings(
    model_name="sentence-transformers/all-MiniLM-l6-v2",  # alternatively use  for a light and faster experience.
    model_kwargs={'device':'cpu'}, 
    encode_kwargs={'normalize_embeddings': True}
)
print(docs_after_split.dtype)
vectorstore = FAISS.from_texts(docs_after_split, huggingface_embeddings)


retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})

# hf = HuggingFacePipeline.from_model_id(
#     model_id="mistralai/Mistral-7B-v0.1",
#     task="text-generation",
#     pipeline_kwargs={"temperature": 0, "max_new_tokens": 300}
# )

hf = HuggingFacePipeline.from_model_id(
    model_id="gpt2",
    task="text-generation",
    pipeline_kwargs={"temperature": 1, "max_new_tokens": 150}
)

# query = "what is this paper about?"
llm = hf 
# print(llm.invoke(query))
priorUserQueries = ""
priorAnswers = ""
index = 0

print("Chatbot is ready! Type your questions below:")
while True:
    user_query = input("\nYou: ")
    if user_query.lower() in ["exit", "quit"]:
        print("Goodbye!")
        break

    # Retrieve relevant chunks from FAISS
    retrieved_docs = retriever.invoke(user_query)

    # Combine retrieved chunks into a single prompt
    context = "\n\n".join([doc.page_content for doc in retrieved_docs])

    max_context_length = 800
    truncated_context = context[:max_context_length]

    priorAnswersTrunc = priorAnswers[:150]
    priorUserQueriesTrunc = priorUserQueries[:150]


    prompt = f"Context: {context} Provide a concise answer with no more than 50 words. If you don't know something don't make it up and just say you dont know it. Prior Questions:{priorUserQueriesTrunc}. Prior Answers: {priorAnswersTrunc} \n\nQuestion: {user_query}\nAnswer:"

    # Use the LLM to process the prompt
    response = llm.invoke(prompt)

    print(f"Bot: {response}")
    priorUserQueries+=f"user_query at instance {index} = {user_query}"
    priorAnswers+=f"response at instance {index} = {response}"


"""
# Retrieve relevant chunks from FAISS
query = "what is this paper about?"
retrieved_docs = retriever.invoke(query)

# Combine retrieved chunks into a single prompt
context = "\n\n".join([doc.page_content for doc in retrieved_docs])
prompt = f"Context: {context}\n\nQuestion: {query}\nAnswer:"

# Use the LLM to process the prompt
response = llm.invoke(prompt)

print(response)

print("\n\n\n")

print(context)

"""