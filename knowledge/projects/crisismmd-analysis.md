# CrisisMMD Multimodal Analysis

## Overview

CrisisMMD Multimodal Analysis is an AI/ML project focused on
analyzing crisis-related social media content using both text
and images.

The project explores multimodal classification to support
the analysis and triage of information shared during
humanitarian crises.

## Problem Statement

Crisis-related social media posts may contain useful information
in both their written text and accompanying images.

Analyzing only one modality may omit information available
in the other. A multimodal model can combine text and image
representations to support classification.

## Dataset

- Dataset: CrisisMMD v2.0
- Input modalities: Text and images
- Application area: Crisis-related and humanitarian social
  media analysis

Document the exact classification task, dataset split, and
label categories used in this implementation from the source
code and dataset configuration.

## Model Architecture

The implementation uses separate encoders for text and images.

### Text Encoder

DistilBERT is used to encode the textual content of a post
into a contextual representation.

### Image Encoder

ResNet is used to extract visual features from the accompanying
image.

Image transformations and normalization are applied as part
of image preprocessing.

### Multimodal Fusion

The text and image representations are combined through
feature concatenation.

The fused representation is passed to a classification
layer that produces predictions for the selected task.

## Processing Workflow

1. Load the text and image data.
2. Tokenize text using DistilBERT's tokenizer.
3. Preprocess images using the image transformation pipeline.
4. Extract text representations using DistilBERT.
5. Extract image features using ResNet.
6. Concatenate the two feature representations.
7. Pass the fused features to the classifier.
8. Evaluate predictions against the actual labels.

## Technical Stack

- Python
- PyTorch
- Hugging Face Transformers
- DistilBERT
- torchvision
- ResNet
- CrisisMMD v2.0

## Results and Evaluation

Add the actual evaluation results from the completed experiments.

Useful metrics may include accuracy, precision, recall, F1-score,
and a confusion matrix, depending on the classification task.

Include the test-set results, selected model configuration,
and any comparison between text-only, image-only, and
multimodal models only if those experiments were performed.

No quantitative performance results are asserted in this draft.

## Limitations

Document limitations based on actual experiments, including
modality-specific errors, class imbalance, data quality,
or generalization issues if observed.

## Source

Dataset: CrisisMMD v2.0

Add the actual project repository and relevant training-script
paths here.