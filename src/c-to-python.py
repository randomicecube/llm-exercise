import os
import subprocess
from langchain import HuggingFaceHub, LLMChain
from langchain.prompts import PromptTemplate

print_debug = lambda arg: print("[DEBUG] " + str(arg))
print_info = lambda arg: print("[INFO] " + str(arg))
print_error = lambda arg: print("[ERROR] " + str(arg))

################################################################################

# Pass False as an argument if you don't use agenix (slash if you aren't me)
def get_api_token(agenix = True):
  if agenix:
    pwd = os.getcwd()
    os.chdir(os.environ.get("HOME") + "/gaspafiles/secrets")
    key = subprocess.check_output(
      ["agenix", "-d", "hugging-face.age"]
    ).decode("utf-8").replace("\n", "")
    os.chdir(pwd)
    return key
  # Otherwise just have a .env file and have your API key there, read it and so on
  return os.environ.get("HUGGING_FACE_API_KEY")

MODEL = "HuggingFaceH4/starchat-beta"
API_TOKEN = get_api_token(False)

################################################################################

llm = HuggingFaceHub(
    repo_id=MODEL,
    huggingfacehub_api_token=API_TOKEN,
    task = "text-generation",
    model_kwargs = {
      "min_length": 100,
      "max_new_tokens": 400,
      "do_sample": True,
      "repetition_penalty": 1.2,
      "temperature": 0.2,
      "top_k": 50,
      "top_p": 0.95,
      "eos_token_id": 123721,
    }
)

prompt = PromptTemplate(
  input_variables=[ "code" ],
  template="Translate the following C code to Python:\n{code}"
)

def perform_query(code):
  chain = LLMChain(prompt=prompt, llm=llm)
  reply = chain.run(code)
  reply = reply.partition("```python")[2] # get everything after the code starts being written
  reply = reply.partition("```")[0] # we can discard everything after the code ends
  # there's also some cases where the final ``` doesn't seem to be put (?)
  reply = reply.partition("<|end|>")[0]
  # this assumes that no-one used ``` along the code itself, which is a bit of a hack
  return reply

################################################################################

SRC_DIR = os.getcwd()
BENCHMARK_LOCATION = SRC_DIR + "/../data/IntroClass/"
PYTHON_CODE_LOCATION = SRC_DIR + "/../data/c-to-python/"
#BENCHMARKS = map(
#  lambda b: BENCHMARK_LOCATION + b,
#  [ "checksum/", "digits/", "grade/", "median/", "smallest/", "syllables/" ]
#)
BENCHMARKS = map(
  lambda b: BENCHMARK_LOCATION + b,
  [ "checksum/" ]
)
TO_AVOID = [ "tests" ]
#TEST_TYPES = [ "blackbox", "whitebox" ]
TEST_TYPES = [ "whitebox" ]

compilation_failures = 0
test_failures = 0
test_successes = 0


def create_tests(python_dir, benchmark):
  # we want to copy the tests/ folder from the benchmark to python_dir
  pwd = os.getcwd()
  os.chdir(benchmark)
  subprocess.run(["cp", "-r", "tests/", python_dir])
  os.chdir(pwd)

def run_tests(python_dir):
  # The tests are just simple .in files, with the expected output being in the corresponding .out file
  pwd = os.getcwd()
  os.chdir(python_dir)
  for test_type in TEST_TYPES:
    for test in os.listdir(f"tests/{test_type}"):
      if not test.endswith(".in"):
        continue
      test_name = test[:-3]
      with open(f"tests/{test_type}/{test}", "r") as test_file:
        input_data = test_file.read()
        result = subprocess.run(["python", "main.py"], input=input_data.encode("utf-8"), capture_output=True, timeout=5)
        with open(f"tests/{test_type}/{test_name}.out", "r") as expected_output:
          expected_output = expected_output.read()
          # Ideally we'd keep checking more and more tests, but for simplicity's
          # sake we'll just stop at the first failure
          if result.stdout.decode("utf-8") != expected_output:
            print_debug(f"Expected: {expected_output}")
            print_debug(f"Got: {result.stdout.decode('utf-8')}")
            return "TEST_FAILURE"
  os.chdir(pwd)
  return "TEST_SUCCESS"



for benchmark in BENCHMARKS:
  # create directory in c-to-python if it hasn't been already done
  benchmark_name = benchmark.split("/")[-2]
  if not os.path.isdir(PYTHON_CODE_LOCATION + benchmark_name):
    os.mkdir(PYTHON_CODE_LOCATION + benchmark_name)
  
  for student_directory_name in os.listdir(benchmark):
    student_directory_path = benchmark + student_directory_name + "/"
    if not os.path.isdir(student_directory_path) and student_directory_name not in TO_AVOID:
      continue

    # create directory in c-to-python/benchmark if it hasn't been already done
    if not os.path.isdir(PYTHON_CODE_LOCATION + benchmark_name + "/" + student_directory_name):
      os.mkdir(PYTHON_CODE_LOCATION + benchmark_name + "/" + student_directory_name)

    # we're within a student's submissions folder
    for submission_name in os.listdir(student_directory_path):
      submission_path = student_directory_path + submission_name + "/"
      if not os.path.isdir(submission_path):
        continue
      
      python_dir = PYTHON_CODE_LOCATION + benchmark_name + "/" + student_directory_name + "/" + submission_name
      # create directory in c-to-python/benchmark/student if it hasn't been already done
      if not os.path.isdir(python_dir):
        os.mkdir(python_dir)
      # we also need to create the tests
      create_tests(python_dir, benchmark)

      # we're within a specific submission
      try:
        print_debug(f"Processing {submission_path + benchmark_name + '.c'}")
        with open(submission_path + benchmark_name + ".c", "r") as s:
          code = s.read()
          reply = perform_query(code)
          if not os.path.isdir(python_dir + "/src"):
            os.mkdir(python_dir + "/src")
          with open(python_dir + "/src/main.py", "w") as python_file:
            python_file.write(reply)
          result = run_tests(python_dir)
          
          match result:
            case "TEST_FAILURE":
              print_info(f"Test failure for {submission_path + benchmark_name + '.c'}")
              test_failures += 1
            case "TEST_SUCCESS":
              print_info(f"Test success for {submission_path + benchmark + '.c'}")
              test_successes += 1

      except FileNotFoundError:
        print(f"The submission {submission_path + benchmark_name + '.c'} was not found.")
      except Exception as e:
        print(f"An error occurred: {str(e)}")

print_info(f"Test failures: {test_failures}, Test successes: {test_successes}")

