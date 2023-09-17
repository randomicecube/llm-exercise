import os
import subprocess
from langchain import HuggingFaceHub, LLMChain
from langchain.prompts import PromptTemplate

# Pass False as an argument if you don't use agenix (slash if you aren't me)
def get_api_token(agenix = True):
  if agenix:
    pwd = os.getcwd()
    os.chdir(os.environ.get("HOME") + "/gaspafiles/secrets")
    key = subprocess.check_output(["agenix", "-d", "hugging-face.age"]).decode("utf-8").replace("\n", "")
    os.chdir(pwd)
    return key
  # Otherwise just have a .env file and have your API key there, read it and so on
  return "<insert your key here>"

model_id = "HuggingFaceH4/starchat-beta"
api_token = get_api_token()

llm = HuggingFaceHub(
    repo_id=model_id,
    huggingfacehub_api_token=api_token,
    task = "text-generation",
    model_kwargs = {
      "min_length": 30,
      "max_new_tokens": 256,
      "do_sample": True,
      "temperature": 0.2,
      "top_k": 50,
      "top_p": 0.95,
      "eos_token_id": 49155,
    }
)

prompt = PromptTemplate(
  input_variables=[ "code" ],
  template="Translate the following C code to Rust:\n{code}"
)

with open("test.c", "r") as file:
  code = file.read()
  chain = LLMChain(prompt=prompt, llm=llm)
  reply = chain.run(code)
  reply = reply.partition("```rust")[2] # get everything after the code starts being written
  reply = reply.partition("```")[0] # we can discard everything after the code ends
  # this assumes that no-one used ``` along the code itself, which is a bit of a hack
  print(reply)

