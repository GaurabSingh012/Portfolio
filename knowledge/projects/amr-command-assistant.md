# AMR Command Assistant

## Overview

The AMR Command Assistant is an NLP project that interprets
natural-language commands intended for an Autonomous Mobile Robot
(AMR) and converts them into structured JSON output.

The goal is to identify the intended action and destination so
that a downstream robotics system can consume the structured
command.

## Problem Statement

Natural-language instructions can contain variations in wording,
destination names, and negation.

A robotics system needs a structured representation of a command
rather than unrestricted natural-language text.

## Project Objectives

- Extract actions and destinations from natural-language commands.
- Convert commands into a consistent JSON format.
- Identify commands that explicitly prohibit an action.
- Evaluate the model on different command formulations.

## Model and Dataset

### Language Model

- Base model: Qwen3-1.7B-Base
- Fine-tuning approach: Parameter-Efficient Fine-Tuning (PEFT)
- Adaptation method: Low-Rank Adaptation (LoRA)

### Dataset

- Dataset file: AMR_800_FineTuning_Dataset_clean.csv
- Dataset size: 800 command examples
- Fields include category, instruction, input, output, and notes.

The dataset contains examples for training the model to map
natural-language instructions to structured command output.

## Output Format

The model produces JSON with two fields:

{
  "action": "navigate",
  "destination": "robotics lab"
}

For commands that should not initiate navigation, the intended
output may be:

{
  "action": "none",
  "destination": "none"
}

The actual output depends on the command and the learned behavior
of the fine-tuned model.

## Implementation Workflow

1. Prepare and clean the command dataset.
2. Load the Qwen3-1.7B base model.
3. Configure LoRA for parameter-efficient fine-tuning.
4. Train the model using the command examples.
5. Load the trained adapter for inference.
6. Test commands and inspect the generated JSON.

## Example Tests

Input:
"Go to the robotics lab."

Expected output:
{
  "action": "navigate",
  "destination": "robotics lab"
}

Input:
"Move to the charging station."

Expected output:
{
  "action": "navigate",
  "destination": "charging station"
}

Input:
"Do not go to the robotics lab."

Expected output:
{
  "action": "none",
  "destination": "none"
}

These examples demonstrate selected test cases, not a guarantee
that every command will be handled correctly.

## Evaluation and Limitations

The model has been tested on selected navigation commands
and negative instructions.

Testing has also revealed cases where negation or exclusion
was interpreted incorrectly. For example, some commands that
should reject a destination produced an incorrect destination.

Further work is needed to evaluate generalization to unseen
commands, improve handling of negation, and measure performance
on a held-out test set.

Do not assume that the model directly controls the robot.
The structured output is intended for use by a downstream
robotics component.

## Technical Stack

- Python
- Hugging Face Transformers
- PEFT
- LoRA
- Qwen3-1.7B-Base
- CSV-based command dataset

## Source

Dataset: AMR_800_FineTuning_Dataset_clean.csv

Add the actual source repository and training-code paths here.