# Code, methods and data attribution

The MIT license applies to the project code. Third-party papers, abstracts,
PDFs, source datasets and model weights keep their original terms and are not
relicensed by this repository.

The triangle constraint follows Wolfe, Spekkens and Fritz, *The Inflation
Technique for Causal Inference with Latent Variables*,
https://arxiv.org/abs/1609.00672. The local implementation is a special-case
reference calculation, not a new inflation theorem or a bundled copy of the
Inflation package.

The optional OCR tools use a separately obtained PaddlePaddle/Unlimited-OCR-2
model. Its source and weights are not included. Literature TXT and JSON records
are kept in the local dataset directory and ignored by Git. Patient-level MIMIC
data is not included and remains subject to PhysioNet access conditions.
