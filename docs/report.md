- [Automatic Translation from C to Rust using LLMs](#automatic-translation-from-c-to-rust-using-llms)
  - [Introduction](#introduction)
    - [Transpilers](#transpilers)
    - [LLM-based translation](#llm-based-translation)
  - [Setup](#setup)
  - [Methodology](#methodology)
    - [Prompt Design](#prompt-design)
    - [Model Parameters](#model-parameters)
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

- `seed` was used to introduce variability between each translation made (among each iteration,
  for the same benchmark); it did not seem to yield _that_ much difference, compared
  to not having it at all, but from an intuition standpoint, it seemed like it'd make sense to utilize it.
- neither `max_length` nor `min_length` seemed like good choices for me - the code itself
  did not seem to benefit from setting boundaries on the length of the output, and
  the code itself never seemed to deviate from "what was expected" regardless of
  such flags being set, hence why I opted to not use them.
- I tried tinkering around with the `repetition_penalty` parameter, but it did not
  seem to change anything in the quality of the output - in fact, regardless of its usage,
  the code did not seem to repeat itself that much (this would probably be more relevant
  in other, perhaps more broad text-generation tasks).
- Regarding decoding (so, "the process a model uses to choose the tokens in the generated output"):
  - `temperature` is related with choosing the next token - higher values will make the model
    more "creative", while lower values will make it more "conservative" (that is,
    with higher temperature values, we'll choose tokens that are less likely to be chosen).
    After experimenting with both, lower values (so, less creative ones) seemed to
    produce better results -- perhaps in more creative tasks, such as answering abstract
    questions, higher values would be more useful -- thus why I opted to use a low value, `0.15`.
  - `top_k` is related with the number of tokens to consider for each step of the decoding
    process. I tried tinkering around with it, but it did not seem to change much
    in the results (albeit perhaps I could have tried with lower values to funnel the answers),
    thus my final attempt did not include it.
  - `top_p` sampling, or _nucleus sampling_, makes the model choose a token from
    the smallest pool of tokens that have a cumulative probability of `top_p`.
    Here, higher values did seem to yield better results with relation to fixing
    compilation errors (albeit most turned into test failures), but nevertheless
    a high value (`0.975`) ended up being used.

## General results

Besides the errors/issues mentioned in the previous sections, one of the most recurrent problems
was definitely the model's borderline refusal to utilize `use` statements (e.g., `use std::io`)
whenever needed, even if the error message itself clearly says it should do so.
Moreover, the model sometimes assumes certain APIs, where methods such as `trim()`
were assumed to exist for `f64`'s - they do not. Besides, sometimes the model
tried to perform literal translations of char-int operations, and they do not work
in the same way in both C and Rust. Finally, even when the syntax was well translated,
the model struggled with fixing simple output formatting errors, which lead to tests
usually failing, as the absence of characters such as newlines being enough to
make the output not match the expected one.

As such, **the vast majority** of the translations failed, with most of the errors
being compilation errors. Although I was aware that non-GPT/CodeLlama/CodeWizard models
would probably not perform particularly well, I was still surprised at the low
amount of tests that actually fully passed. Between API and type mismatches, missing
`use` statements, and output formatting errors, the model seemed to struggle with
translations in a general fashion, and I'm left confused on whether this is due to
the model's inability to perform well in these kinds of tasks, or if I could have done
something vastly different to achieve better results - more iterations did not seem to
change much, and varying parameters, albeit changing the code, did not seem to change
the results themselves that much overall.

One thing that would have been interesting, which I unfortunately forgot until the very end,
is to have tracked the results of the model's translations between different ranges
of iterations, and different values for the model's parameters; this very well could
have lead to me to, using proper visualizations for the acquired data, understand
patterns on the results, and find out the ideal parameters to be used.

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
to test whether other, perhaps more advanced/well trained/specifically "top_k": 50,

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

- [Understanding the Effectiveness of Large Language Models in Code Translation - Rangeet Pan et. al](https://arxiv.org/pdf/2308.03109.pdf)
- [Attention, Compilation, and Solver-based Symbolic Analysis are All You Need - Prithwish Jana et. al](https://arxiv.org/pdf/2306.06755.pdf)
- [IBM India's overview and publications on Code Translation](https://research.ibm.com/projects/code-translation)
- [IBM's article on model parameters](https://www.ibm.com/docs/en/watsonx-as-a-service?topic=models-parameters)
