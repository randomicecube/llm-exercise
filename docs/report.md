- [Automatic Translation from C to Rust using LLMs](#automatic-translation-from-c-to-rust-using-llms)
  - [Introduction](#introduction)
    - [Transpilers](#transpilers)
    - [LLM-based translation](#llm-based-translation)
  - [Setup](#setup)
  - [Methodology](#methodology)
    - [Prompt Design](#prompt-design)
    - [Model Parameters](#model-parameters)
  - [Problems found](#problems-found)
  - [General results](#general-results)
  - [Side-experiment - C-to-Python](#side-experiment---c-to-python)
  - [Some ideas that could still be explored in the future](#some-ideas-that-could-still-be-explored-in-the-future)
  - [Articles/papers (a very succinct 'related work' section)](#articlespapers-a-very-succinct-related-work-section)

# Automatic Translation from C to Rust using LLMs

## Introduction

The concept of programming language translation is certainly not new: developers have migrated codebases from
one language to another for decades. It's generally considered a tedious process, considering as with many
languages such translations aren't particularly trivial, due to core differences between them; moreover, as
with any kind of migration, translation errors will naturally occur, leading to errors/faults.

### Transpilers

Transpilers, or source-to-source compilers, try to take this burden out of the developers' hands, with C2Rust being
perhaps the most relevant one for this report. The diagram below, taken from C2Rust's [GitHub page](https://github.com/immunant/c2rust), displays
their translation pipeline:

![C2Rust transpilation pipeline](https://github.com/immunant/c2rust/raw/master/docs/c2rust-overview.png)

Note how the transpiler creates [unsafe Rust](https://doc.rust-lang.org/nomicon/meet-safe-and-unsafe.html). Moreover,
transpilers generate code that isn't particularly idiomatic. As such, developers would still need
to manually rewrite/refactor code, in order to be more idiomatic (and, ideally,
to make it safe). Regarding the former, C2Rust's team does say they're working
on tools to improve it - until then, examples [like this one](https://www.reddit.com/r/rustjerk/comments/dpskmo/c2rust_produces_extremely_idiomatic_and/)
will certainly be common, and require manual rewriting.

### LLM-based translation

With the recent "rise to stardom" of machine learning, and large language models (LLMs)
in particular, it's natural to investigate whether these models can actually produce
good, faithful, and idiomatic language translations. With these models being trained
on large amounts of data, it's possible that they can learn the intricacies of a language, through context cues and
other features, thus producing more idiomatic source-to-source migrations.

## Setup

I'll be using the [IntroClass](https://github.com/ProgramRepair/IntroClass) benchmark
for this report, in order to both gather the examples to translate, as well as to
have a concrete way to evaluate the amount of errors/faults in the translated code.
I'll be trying to perform a mix of testing both the given correct solution per benchmark
(at `<benchmark>/tests/<benchmark>.c`), as well as the (possibly incorrect) solutions
submitted by students.

Moreover, I'll be using the [StarChatBeta](https://huggingface.co/HuggingFaceH4/starchat-beta) model,
an assistant-like extension to StarCoderBase, a model by HuggingFace trained on
80+ languages (including both C and Rust). To connect with it, I'll be using HuggingFace's [inference API](https://huggingface.co/inference-api).

## Methodology

My initial idea was to write a script that would, for each of the provided benchmarks,
provide a direct translation from C to Rust (without indicating to the model whether
safety was required). Afterwards, all (both black and whitebox) tests would be run
on the translated code - for the provided correct solution, all tests should pass,
while for the student solutions, I would have to manually check whether the tests
that were not passing were due to the translation, or due to the student's code (and this
was done manually - in an ideal scenario I would have done this automatically too,
but alas).

In proper research, each error/bug encountered would have certainly be documented in
a rather granular manner, considering both its type (e.g., compilation vs runtime error),
as well as its cause (e.g., API mismatches between languages, type mismatches, etc.).
For this small report, I found it would be useful to still categorize errors, of course,
but I did it in a more high-level manner, considering only three possible scenarios:
`COMPILATION_FAILURE`, when `rustc` is not able to compile the translated code;
`TEST_FAILURE`, when the translated code compiles, but fails some of the tests (be it
wrong input or general runtime errors); and `TEST_SUCCESS`, when the translated code compiles, runs, and passes all of the provided tests.

The script itself tries to perform the translation a maximum of six times: three to
fix possible compilation errors, and three to fix possible test failures. If, during
the test-failure phase, the code goes back to a compilation error, the script stops
trying to translate the code (just so it doesn't get stuck in going back and forth
between these two phases). Note, of course, that proper research methods would be to
have many more phases, with the possibility of going back and forth between them
and so on, I opted for this for simplicity's sake.

### Prompt Design

Prompts are an integral part of code-assistant-like models, and as such, it's important
to design them in a way that allows the model to best understand what we want it to do,
performing the task in the most faithful way possible. After some experimentation,
starting with very bare-bones prompts, and then adding more and more information
and quirks/hacks, I ended up with the following prompts (which vary between each
of the scenarios we may want to consider; note that the exact prompts are in the script,
this is just a general explanation of each one):

- **Initial prompt**: Here, basic instructions are given to the model. While I initially
  tried to ask it just to translate the C code to Rust, I then realized that it helped
  to ask it not to add nor change logic within it; moreover, adding a comment regarding
  the output having to be exactly the same as the input also helped (although certainly
  far from always - more on this later).
- **Compilation error prompt**: Here, the prompt is provided with the exact error
  (so, the one taken from `stderr`) displayed by `rustc`. I thought of parsing just the
  error codes, but it didn't seem to help at all, as the additional context provided
  by the error message itself seemed to be more useful to the model. I also tried
  to ask the model, first, to explain what was wrong in the code, considering the
  error message(s), and in a second message to fix the code according to that, but
  it didn't seem to help particularly - perhaps some more prompt engineering is required
  on this end for it to work properly?
- **Test failure prompt**: Here, the prompt is provided with the exact expected output
  for the failed test, as well as the output of the translated code. I tried to give it
  _all_ the tests failed by the code, but the model seemed to get overwhelmed by the
  amount of differences, with the next translation ranging from completely equal, to a bit
  better, to complete gibberish. As such, I opted to just give it one test at a time,
  which seemed to work better. I also tried to ask the model to explain what was wrong,
  just like I did for the compilation error prompt, but it didn't seem to help particularly
  either.

### Model Parameters

I'm using the `starchat-beta` model, which, although previously trained, allows for (as the vast
majority of API-accessible LLMs seem to do) the possibility of passing [parameters](https://huggingface.co/docs/api-inference/detailed_parameters#text-generation-task),
in order to aid/specialize the model on whatever task we want to do. The ones I found
to be most relevant are the following:

TODO: mention the parameters that ended up being used in the end

## Problems found

Besides the ones mentioned in the previous sections, one of the most recurrent problems
was definitely the model's borderline refusal to utilize `use` statements whenever
needed, even if the prompt explicitly says for it to do so.

TODO: add rest

<!-- Imports, `use` thingies -->

## General results

TODO: add

## Side-experiment - C-to-Python

During my C-to-Rust experiments, the idea that "perhaps the model just hasn't seen
enough Rust examples for it to provide good enough translations" came to my mind often:
as such, and with Python being undoubtedly one of the most ubiquitous languages out there,
I decided to try to translate the same C code benchmark to Python, and see how
well the model would perform in comparison with the previous experiments (considering,
of course, the same prompts, model parameters, and so on, and no compilation-failure query stage). The results, curiously,
were that the code still does not seem to pass most of the tests presented; however,
while in Rust the code would often not even compile, in Python the errors did not
seem to be as severe on that end, with syntax errors being way less prevalent
(it's interesting to wonder about why this is happening - is it because Python is
dynamically typed? Rather, is it due to Python's syntax being, in general, less strict
than Rust's?). The errors here, though, seem to be related with the model's seeming
inability to discover small errors between the expected and actual output - as an
example, the `digits` benchmark tended to face the following issue:

```
[DEBUG] Expected output:
Enter an integer >
2
6
6
8
6
5
5
0
0
1
That's all, have a nice day!

[DEBUG] Actual output: Enter an integer: 100556886
```

During all three test-failure iterations, the model never seems to understand the
need to print newlines after each digit, nor that the prompt separator for user input
is a `>`, not a `:`, and finally, that the final "That's all, have a nice day!" message
should be printed after the digits. I tried tinkering around the model's parameters,
but never seemed to make this quite work - in future experiments, it would be interesting
to test whether other, perhaps more advanced/well trained/specifically code-trained
models would be able to perform better on this regard.

## Some ideas that could still be explored in the future

I only thought of this a bit too late to include it here (well, rather, a friend of mine did and I thought it'd be a nice experiment), but it'd probably be interesting
to research on a different translation pipeline: starting off with a transpilation of
C code to unsafe and unidiomatic Rust, proceed with `c2rust`'s `c2rust refactor` tool
(although not sure on how well this currently works), and afterwards, use the LLM to
translate the code to idiomatic Rust; one could even use the LLM to perform just
these two last steps, and see how well it performs. By my intuition, this should
probably produce better results than just direct translations, considering many
of the problems pointed out above would not be relevant anymore, with the bulk
of the translation work having already been done.

I also thought (and also too late) of the idea of having manually translated
C to Rust code, have that same C code translated to Rust via an LLM, and survey a pool
of Computer Science students/workers on which one they thought was written by a human vs AI, and
why they thought so - this would probably be a good way to measure the current progress
on idiomatic programming language translations, with the reasoning given by the people
surveyed being of great use (perhaps even more so if they are not particularly
indulged into ML) for finding spots where models could be improved.

## Articles/papers (a very succinct 'related work' section)

While investigating this topic, I invariably ended up finding some articles/papers
which both allowed me to understand the current research on it a bit better, while
also providing me insights on why some of the errors I found were happening, and
how academia is currently trying to solve them. Some of them are the following (I read
a couple of more, whose links I'm not currently able to find):

- [Understanding the Effectiveness of Large
  Language Models in Code Translation - Rangeet Pan et. al](https://arxiv.org/pdf/2308.03109.pdf)
- [Attention, Compilation, and Solver-based Symbolic
  Analysis are All You Need - Prithwish Jana et. al](https://arxiv.org/pdf/2306.06755.pdf)
- [IBM India's overview and publications on Code Translation](https://research.ibm.com/projects/code-translation)
