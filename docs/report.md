- [Automatic Translation from C to Rust using LLMs](#automatic-translation-from-c-to-rust-using-llms)
  - [Introduction](#introduction)

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
