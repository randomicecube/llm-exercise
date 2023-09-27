################################################################################
# C to Rust translation - inputs are every IntroClass student submission, for every benchmark 

import os
import subprocess
from langchain import HuggingFaceHub, LLMChain
from langchain.prompts import PromptTemplate
from random import randint

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
API_TOKEN = get_api_token()

################################################################################

def create_model(seed):
  return HuggingFaceHub(
    repo_id=MODEL,
    huggingfacehub_api_token=API_TOKEN,
    task = "text-generation",
    model_kwargs = {
      "max_new_tokens": 512,
      "repetition_penalty": 1.05,
      "temperature": 0.15,
      "top_p": 0.975,
      "return_full_text": True,
      "seed": seed,
    }
)

prompt = PromptTemplate(
  input_variables=[ "code" ],
  template="Translate the following C code to Rust:\n{code}"
)
prompt_with_previous_compilation_error = PromptTemplate(
  input_variables=[ "code", "previous_compilation_error" ],
  template="Translate the following C code to Rust (don't forget to fix the error):\n{code}\nError: {previous_compilation_error}"
)

prompt_with_previous_test_failure = PromptTemplate(
  input_variables=[ "code", "expected_output", "actual_output" ],
  template="Translate the following C code to Rust (don't forget to fix the test output-errors):\n{code}\nExpected output: {expected_output}\nActual output: {actual_output}"
)

def perform_query(code, model, previous_compilation_error = None, previous_test_failure = None):
  if previous_compilation_error:
    print_debug(f"Previous compilation error: {previous_compilation_error}")
    chain = LLMChain(
      prompt=prompt_with_previous_compilation_error,
      llm=model
    )
    reply = chain.run({"code": code, "previous_compilation_error": previous_compilation_error})
  elif previous_test_failure:
    expected_output, actual_output = previous_test_failure
    print_debug(f"Previous test failure: {previous_test_failure}")
    chain = LLMChain(
      prompt=prompt_with_previous_test_failure,
      llm=model
    )
    reply = chain.run({
      "code": code,
      "expected_output": expected_output,
      "actual_output": actual_output
    })
  else:
    print_debug("No previous error")
    chain = LLMChain(prompt=prompt, llm=model)
    reply = chain.run(code)
  reply = reply.partition("```rust")[2] # get everything after the code starts being written
  reply = reply.partition("```")[0] # we can discard everything after the code ends
  # there's also some cases where the final ``` doesn't seem to be put (?)
  reply = reply.partition("<|end|>")[0]
  # this assumes that no-one used ``` along the code itself, which is a bit of a hack
  return reply

################################################################################

SRC_DIR = os.getcwd()
BENCHMARK_LOCATION = SRC_DIR + "/../data/IntroClass/"
RUST_CODE_LOCATION = SRC_DIR + "/../data/c-to-rust/"
BENCHMARKS = map(
 lambda b: BENCHMARK_LOCATION + b,
 [ "checksum/", "digits/", "grade/", "median/", "smallest/", "syllables/" ]
)
TO_AVOID = [ "tests" ]
TEST_TYPES = [ "blackbox", "whitebox" ]

# I want objects which have both _what happened_ and also, if there was an error, its error code
# This is useful to re-ask the model to fix the code, considering the error code
# Moreover, for test failures, we can also give back the expected output and the actual output
class QueryResult:
  def __init__(self, result, error = None, outputs = None):
    # Note that result is a string, which may be "COMPILER_FAILURE", "TEST_FAILURE" or "TEST_SUCCESS"
    self.result = result
    self.error = error
    self.outputs = outputs # a tuple with two strings, the expected output and the actual output


def cargo_init(rust_dir):
  pwd = os.getcwd()
  os.chdir(rust_dir)
  subprocess.run(["cargo", "init"])
  os.chdir(pwd)

# With more time, using rust's test feature (w/ `cargo test`) could be fun
# It seemed a bit too complicated to me for this exercise, though
def create_tests(rust_dir, benchmark):
  # we want to copy the tests/ folder from the benchmark to rust_dir
  pwd = os.getcwd()
  os.chdir(benchmark)
  subprocess.run(["cp", "-r", "tests/", rust_dir])
  os.chdir(pwd)

def test_code(rust_dir):
  pwd = os.getcwd()
  os.chdir(rust_dir)
  compilation_result = subprocess.run(["rustc", "src/main.rs"], capture_output=True, text=True)
  os.chdir(pwd)

  # Rust's compiler, on compilation errors, returns "For more information about this error, try `rustc --explain <error code>`".
  # With more time, it'd be interesting to parse the error code, give it back to the LLM
  # and ask it to fix the code, considering the given error code.
  if compilation_result.returncode != 0:
    return QueryResult("COMPILER_FAILURE", compilation_result.stderr)
  return run_tests(rust_dir)

def run_tests(rust_dir):
  # Once again, we won't be using `cargo test`, but rather just running the program itself with specific inputs (and checking the outputs)
  # The tests are just simple .in files, with the expected output being in the corresponding .out file
  pwd = os.getcwd()
  os.chdir(rust_dir)
  for test_type in TEST_TYPES:
    for test in os.listdir(f"tests/{test_type}"):
      if not test.endswith(".in"):
        continue
      test_name = test[:-3]
      with open(f"tests/{test_type}/{test}", "r") as test_file:
        input_data = test_file.read()
        result = subprocess.run(["./main"], input=input_data.encode("utf-8"), capture_output=True, timeout=5)
        with open(f"tests/{test_type}/{test_name}.out", "r") as expected_output:
          expected_output = expected_output.read()
          # Ideally we'd keep checking more and more tests, but for simplicity's
          # sake we'll just stop at the first failure
          if result.stdout != expected_output:
            os.chdir(pwd)
            return QueryResult("TEST_FAILURE", outputs = (expected_output, result.stdout))
  os.chdir(pwd)
  return QueryResult("TEST_SUCCESS")

def process_submission(
  submission_path, benchmark_name,
  no_compilation_errors = True, previous_error = None,
  no_test_errors = True, previous_test_failure = None
):
  global compilation_failures, test_failures, test_successes
  try:
    print_debug(f"Processing {submission_path + benchmark_name + '.c'}")
    with open(submission_path + benchmark_name + ".c", "r") as s:
      code = s.read()
      llm = create_model(seed=randint(0, 1000000))
      reply = perform_query(code, llm, previous_error, previous_test_failure)
      if not os.path.isdir(rust_dir + "/src"):
        os.mkdir(rust_dir + "/src")
      with open(rust_dir + "/src/main.rs", "w") as rust_file:
        rust_file.write(reply)
      query_result = test_code(rust_dir)
      
      match query_result.result:
        case "COMPILER_FAILURE":
          if no_compilation_errors:
            process_submission(submission_path, benchmark_name, False, query_result.error, no_test_errors)
          else:
            print_error(f"Compiler failure for {submission_path + benchmark_name + '.c'}")
            compilation_failures += 1
        case "TEST_FAILURE":
          if no_test_errors:
            # I'm forcing False for no_compilation_errors, just so there's no possibility of back-and-forth between the two
            process_submission(submission_path, benchmark_name, False, None, False, query_result.outputs)
          else:
            print_info(f"Test failure for {submission_path + benchmark_name + '.c'}")
            test_failures += 1
        case "TEST_SUCCESS":
          print_info(f"Test success for {submission_path + benchmark + '.c'}")
          test_successes += 1

  except FileNotFoundError:
    print(f"The submission {submission_path + benchmark_name + '.c'} was not found.")
  except Exception as e:
    print(f"An error occurred: {str(e)}")

################################################################################

compilation_failures = 0
test_failures = 0
test_successes = 0

if __name__ == "__main__":
  for benchmark in BENCHMARKS:
    # create directory in c-to-rust if it hasn't been already done
    benchmark_name = benchmark.split("/")[-2]
    if not os.path.isdir(RUST_CODE_LOCATION + benchmark_name):
      os.mkdir(RUST_CODE_LOCATION + benchmark_name)
    
    for student_directory_name in os.listdir(benchmark):
      student_directory_path = benchmark + student_directory_name + "/"
      if not os.path.isdir(student_directory_path) and student_directory_name not in TO_AVOID:
        continue

      # create directory in c-to-rust/benchmark if it hasn't been already done
      if not os.path.isdir(RUST_CODE_LOCATION + benchmark_name + "/" + student_directory_name):
        os.mkdir(RUST_CODE_LOCATION + benchmark_name + "/" + student_directory_name)

      # we're within a student's submissions folder
      for submission_name in os.listdir(student_directory_path):
        submission_path = student_directory_path + submission_name + "/"
        if not os.path.isdir(submission_path):
          continue
        
        rust_dir = RUST_CODE_LOCATION + benchmark_name + "/" + student_directory_name + "/" + submission_name
        # create directory in c-to-rust/benchmark/student if it hasn't been already done
        if not os.path.isdir(rust_dir):
          os.mkdir(rust_dir)
          # we want this to be a rust project, thus we need to run cargo init
          cargo_init(rust_dir)

        # we also need to create the tests
        create_tests(rust_dir, benchmark)

        process_submission(submission_path, benchmark_name)

  print_info(f"Compilation failures: {compilation_failures}, Test failures: {test_failures}, Test successes: {test_successes}")
